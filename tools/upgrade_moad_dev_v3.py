"""Add FINESS catalog, current-direction details and new DEV widget URLs.

Input is the v2 DEV document. Plan is produced by finess-core-v1-dev.js from
the two official public feeds. Existing contacts, answers and tables survive.
"""
import sys,json,pathlib
from offline_grist import load,act,records,export
from migrate_moad_dev import col,table,bulk,update,acl,owner_only

def upgrade(source,destination,planfile):
    e=load(source);plan=json.loads(pathlib.Path(planfile).read_text())
    if any(t['tableId']=='FINESS_CATALOGUE' for t in records(e,'_grist_Tables')):raise ValueError('Ce document possède déjà le modèle FINESS V3 ; aucune modification effectuée.')
    contact_ref=next(t['id'] for t in records(e,'_grist_Tables') if t['tableId']=='CONTACTS')
    if not any(c['parentId']==contact_ref and c['colId']=='TELEPHONE' for c in records(e,'_grist_Tables_column')):col(e,'CONTACTS','TELEPHONE','Text')
    col(e,'SITES','DIRECTION_CONTACTS_JSON','Text','''import json
return json.dumps([{"nom": c.NOM_PRENOM_contact.strip(), "email": c.EMAIL or "", "telephone": c.TELEPHONE or "", "fonction": c.FONCTION.LIBELLE or ""} for c in CONTACTS.all if c.FONCTION.id in [20,21,23] and (c.SITE_PRINCIPAL.id == $id or $id in [s.id for s in c.SITES_RESP_AIRMES])], ensure_ascii=False)''')
    for r in records(e,'_grist_ACLResources'):
        if r['tableId']=='SITES' and 'DIRECTION_NOMS' in r['colIds']:update(e,'_grist_ACLResources',r['id'],colIds=r['colIds']+',DIRECTION_CONTACTS_JSON')
    col(e,'ESMS','FINESS_NORMALISE','Text','''import re
s = re.sub(r"[\\s.\\-]", "", str($FINESS or "").upper())
if re.fullmatch(r"[0-9]{8}", s): s = "0" + s
return s if re.fullmatch(r"[0-9][0-9A-Z][0-9]{7}", s) and s != "000000000" else ""''')
    physical=[('FINESS','Text'),('FINESS_JURIDIQUE','Text'),('UGECAM','Ref:UGECAM'),('RAISON_SOCIALE','Text'),('RAISON_SOCIALE_LONGUE','Text'),('CATEGORIE_CODE','Text'),('CATEGORIE','Text'),('ADRESSE','Text'),('TELEPHONE','Text'),('SIRET','Text'),('DATE_CREATION','Text'),('DATE_OUVERTURE','Text'),('DATE_AUTORISATION','Text'),('DATE_MAJ_SOURCE','Text'),('MILLESIME_ETAB','Text'),('MILLESIME_EQUIPEMENTS','Text'),('DATE_ARRETE_DONNEES','Text'),('IMPORT_LE','Text'),('SOURCE_ETAB_URL','Text'),('SOURCE_EQUIPEMENTS_URL','Text'),('PRESENT_SOURCE','Bool'),('DONNEES_COMPLEMENTAIRES','Text'),('DONNEES_SOURCE_JSON','Text')]
    site_formula='''ss = sorted(set(r.SITE.id for r in ESMS.lookupRecords(FINESS_NORMALISE=$FINESS) if r.SITE))
return SITES.lookupOne(id=ss[0]) if len(ss) == 1 else SITES.lookupOne(id=0)'''
    table(e,'FINESS_CATALOGUE',[(k,t,'') for k,t in physical]+[('SITES_LIES','RefList:SITES','sorted(set(r.SITE.id for r in ESMS.lookupRecords(FINESS_NORMALISE=$FINESS) if r.SITE))'),('CONTACTS_PERIMETRE','RefList:CONTACTS','''ss = set(s.id for s in $SITES_LIES)
return [c.id for c in CONTACTS.all if c.SITE_PRINCIPAL.id in ss or any(s.id in ss for s in c.SITES_RESP_AIRMES)]'''),('SITE','Ref:SITES',site_formula),('RATTACHEMENT','Text','''ss = set(r.SITE.id for r in ESMS.lookupRecords(FINESS_NORMALISE=$FINESS) if r.SITE)
return "Rattaché à un site" if len(ss) == 1 else "Sites multiples — à arbitrer" if len(ss) > 1 else "À rattacher"''')])
    eqfields=[('CLE_SOURCE','Text'),('FINESS','Text'),('DISCIPLINE','Text'),('LIB_DISCIPLINE','Text'),('ACTIVITE','Text'),('LIB_ACTIVITE','Text'),('CLIENTELE','Text'),('LIB_CLIENTELE','Text'),('CAPACITE_AUTORISEE','Numeric'),('CAPACITE_INSTALLEE','Numeric'),('IND_SUP_AUT','Text'),('IND_SUP_INST','Text'),('DATE_AUTORISATION','Text'),('DATE_PREMIERE_AUTORISATION','Text'),('DATE_DERNIERE_INSTALLATION','Text'),('DATE_MAJ_AUTORISATION','Text'),('DATE_MAJ_INSTALLATION','Text'),('MILLESIME','Text'),('PRESENT_SOURCE','Bool'),('ANOMALIE','Text'),('DONNEES_SOURCE_JSON','Text')]
    table(e,'FINESS_EQUIPEMENTS',[(k,t,'') for k,t in eqfields]+[('ETABLISSEMENT','Ref:FINESS_CATALOGUE','FINESS_CATALOGUE.lookupOne(FINESS=$FINESS)')])
    for name,capacity,flag in [('NB_PLACES_AUTORISEES','CAPACITE_AUTORISEE','IND_SUP_AUT'),('NB_PLACES_INSTALLEES','CAPACITE_INSTALLEE','IND_SUP_INST')]:
        col(e,'FINESS_CATALOGUE',name,'Numeric',f'''rr = [r for r in FINESS_EQUIPEMENTS.lookupRecords(FINESS=$FINESS) if r.PRESENT_SOURCE]
if not $PRESENT_SOURCE or any(r.ANOMALIE for r in rr): return None
vv = [r.{capacity} for r in rr if r.{flag} == "N" and r.{capacity} is not None]
return sum(vv) if vv else None''')
    col(e,'FINESS_CATALOGUE','STATUT_CAPACITES','Text','''rr = [r for r in FINESS_EQUIPEMENTS.lookupRecords(FINESS=$FINESS) if r.PRESENT_SOURCE]
return "Absent du dernier import établissements" if not $PRESENT_SOURCE else "À vérifier : lignes ambiguës ou indicateurs incomplets" if any(r.ANOMALIE for r in rr) else "Non couvert par les équipements sociaux importés" if not rr else "Totaux des capacités actives ; lignes supprimées exclues"''')
    col(e,'ESMS','FINESS_REF','Ref:FINESS_CATALOGUE','FINESS_CATALOGUE.lookupOne(FINESS=$FINESS_NORMALISE)')
    table(e,'FINESS_IMPORTS',[(k,'Text','') for k in ['DATE_IMPORT','FICHIER_ETAB','FICHIER_EQUIPEMENTS','SHA256_ETAB','SHA256_EQUIPEMENTS','SOURCE_ETAB_URL','SOURCE_EQUIPEMENTS_URL','BILAN_JSON','AVERTISSEMENTS_JSON']])
    owner_only(e,'FINESS_IMPORTS')
    table(e,'FINESS_ACCES_PAGE',[('LIBELLE','Text','')]);bulk(e,'FINESS_ACCES_PAGE',[{'id':1,'LIBELLE':'Liste des FINESS du Groupe UGECAM'}])
    gate="user.demande_acces.STATUT == 'Validé' and user.droits_supp.ACCES_LISTE_ESMS is True"
    acl(e,'FINESS_ACCES_PAGE',[('user.Access == OWNER','+CRUD'),(gate,'+R-CUD'),('','-CRUD')])
    def scope(site,ug,contacts):
        return f"(user.droits_supp.DNGU is True or (user.droits_supp.SIEGE is True and user.droits_supp.UGECAM == {ug}) or (user.droits_supp.SIEGE != True and user.droits_supp.DNGU != True and user.droits_supp.id in {contacts}))"
    acl(e,'FINESS_CATALOGUE',[('user.Access == OWNER','+CRUD'),(gate+' and '+scope('rec.SITE','rec.UGECAM','rec.CONTACTS_PERIMETRE'),'+R-CUD'),('','-CRUD')])
    acl(e,'FINESS_EQUIPEMENTS',[('user.Access == OWNER','+CRUD'),(gate+' and '+scope('rec.ETABLISSEMENT.SITE','rec.ETABLISSEMENT.UGECAM','rec.ETABLISSEMENT.CONTACTS_PERIMETRE'),'+R-CUD'),('','-CRUD')])
    acl(e,'FINESS_CATALOGUE',[('user.Access == OWNER','+CRUD'),('','-CRUD')],'CONTACTS_PERIMETRE')
    bulk(e,'FINESS_CATALOGUE',plan['catalogue']);bulk(e,'FINESS_EQUIPEMENTS',plan['equipments'])
    audit=plan.get('audit',{})
    bulk(e,'FINESS_IMPORTS',[dict(DATE_IMPORT=plan['catalogue'][0]['IMPORT_LE'],FICHIER_ETAB=audit.get('fichier_etab','etablissements.csv'),FICHIER_EQUIPEMENTS=audit.get('fichier_eq','equipements.csv'),SHA256_ETAB=audit.get('sha256_etab',''),SHA256_EQUIPEMENTS=audit.get('sha256_eq',''),SOURCE_ETAB_URL=plan['catalogue'][0]['SOURCE_ETAB_URL'],SOURCE_EQUIPEMENTS_URL=plan['catalogue'][0]['SOURCE_EQUIPEMENTS_URL'],BILAN_JSON=json.dumps(plan['summary']),AVERTISSEMENTS_JSON=json.dumps(plan['warnings'],ensure_ascii=False))])
    ref=next(t['id'] for t in records(e,'_grist_Tables') if t['tableId']=='FINESS_ACCES_PAGE')
    result=act(e,['CreateViewSection',ref,0,'custom',None,None]).retValues[0]
    update(e,'_grist_Views',result['viewRef'],name='Liste des FINESS du Groupe UGECAM',layoutSpec=json.dumps({'leaf':result['sectionRef']}))
    options={'customView':json.dumps({'mode':'url','url':'https://mahmboud.github.io/grist-fiche-esms/dev/moad-airmes-20261028/target/liste-finess-v1-dev.html','access':'full','renderAfterReady':False,'columnsMapping':None})}
    update(e,'_grist_Views_section',result['sectionRef'],title='Liste des FINESS du Groupe UGECAM',options=json.dumps(options))
    # Keep the list beside the ESMS page, and preserve all existing page IDs.
    page=next(p for p in records(e,'_grist_Pages') if p['viewRef']==result['viewRef']);update(e,'_grist_Pages',page['id'],pagePos=4.5)
    paths={'v6-dev2.html':'v6-dev3.html','airmes-arborescence-v2-dev.html':'airmes-arborescence-v3-dev.html','admin-nouveau-referent-v2-dev.html':'admin-nouveau-referent-v3-dev.html','acces-moad-v2-dev.html':'acces-moad-v3-dev.html'}
    for r in records(e,'_grist_Views_section'):
        options=r.get('options') or ''
        for old,new in paths.items():options=options.replace('/target/'+old,'/target/'+new)
        if options!=r.get('options'):update(e,'_grist_Views_section',r['id'],options=options)
    # Display native references as labels rather than numerical record IDs.
    refs={r['tableId']:r['id'] for r in records(e,'_grist_Tables')};cols=records(e,'_grist_Tables_column')
    for t,c,target,visible in [('FINESS_CATALOGUE','UGECAM','UGECAM','UGECAM'),('FINESS_CATALOGUE','SITE','SITES','NOM'),('ESMS','FINESS_REF','FINESS_CATALOGUE','FINESS')]:
        cr=next(r['id'] for r in cols if r['parentId']==refs[t] and r['colId']==c);vc=next(r['id'] for r in cols if r['parentId']==refs[target] and r['colId']==visible)
        update(e,'_grist_Tables_column',cr,visibleCol=vc);act(e,['SetDisplayFormula',t,None,cr,'$'+c+'.'+visible])
    export(e,source,destination)
    print(json.dumps({'finess':len(plan['catalogue']),'equipements':len(plan['equipments']),'page':result,'source_preserved':source,'output':destination},ensure_ascii=False))
if __name__=='__main__':upgrade(*sys.argv[1:])
