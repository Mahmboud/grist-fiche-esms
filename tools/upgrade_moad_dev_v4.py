"""Recover every historical FINESS without guessing Airmes service identities.

The original Airmes tree is exposed through scoped, non-personal projections.
The input document and all original rows/values remain unchanged.
"""
import sys,json,re,unicodedata,collections,pathlib
from offline_grist import load,act,records,export,objtypes
from migrate_moad_dev import col,table,bulk,update,acl,owner_only

def norm(v):
    s=re.sub(r'[\s.\-]','',str(v or '').upper())
    if re.fullmatch(r'\d{8}',s):s='0'+s
    return s if re.fullmatch(r'[0-9][0-9A-Z][0-9]{7}',s) and s!='000000000' else ''
def keys(v):
    s=str(v or '').upper()
    if norm(s):return [norm(s)]
    return sorted(set(filter(None,(norm(x) for x in re.findall(r'(?<![0-9A-Z])[0-9](?:[\s.-]*[0-9A-Z])(?:[\s.-]*[0-9]){7}(?![0-9A-Z])',s)))))
def name(v):return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFD',str(v or '')).encode('ascii','ignore').decode().lower())

def upgrade(source,destination,report):
    e=load(source)
    if any(t['tableId']=='REPRISE_FINESS_HISTORIQUE' for t in records(e,'_grist_Tables')):raise ValueError('Ce document est déjà en V4 ; aucune modification effectuée.')
    if any(t['tableId']=='REPRISE_FINESS_HISTORIQUE' for t in records(e,'_grist_Tables')):raise ValueError('La reprise V4 existe déjà ; aucune modification effectuée.')
    ug={r['id']:r for r in records(e,'UGECAM')};sites={r['id']:r for r in records(e,'SITES')};legacy={r['id']:r for r in records(e,'ESMS_Liste_UGECAM_')};existing=records(e,'ESMS');mapping={r['ANCIEN_SITE']:r['SITE'] for r in records(e,'MIGRATION_SITES')};catalogue={r['FINESS']:r for r in records(e,'FINESS_CATALOGUE')}
    legal_added={}
    for uid,u in ug.items():
        historical={k for r in legacy.values() if r['UGECAM']==uid and name(r['ESMS_raison_sociale']).startswith(('siege','dngu')) for k in keys(r['FINESS'])}
        missing=sorted(historical-set(keys(u['FINESS_Juridique'])))
        if missing:
            update(e,'UGECAM',uid,FINESS_Juridique=str(u['FINESS_Juridique'] or '')+'\n'+'\n'.join(missing))
            legal_added[str(uid)]=missing
    col(e,'UGECAM','FINESS_JURIDIQUES','ChoiceList','''import re
s = str($FINESS_Juridique or "").upper()
def clean(v):
  v = re.sub(r"[\\s.\\-]", "", v)
  if re.fullmatch(r"[0-9]{8}", v): v = "0" + v
  return v if re.fullmatch(r"[0-9][0-9A-Z][0-9]{7}", v) and v != "000000000" else ""
single = clean(s)
return [single] if single else sorted(set(filter(None, [clean(x) for x in re.findall(r"(?<![0-9A-Z])[0-9](?:[\\s.-]*[0-9A-Z])(?:[\\s.-]*[0-9]){7}(?![0-9A-Z])", s)])))''')
    for k,t,f in [('APPELLATIONS_HISTORIQUES','ChoiceList',''),('FINESS_HISTORIQUES','ChoiceList',''),('FINESS_SOURCE_BRUT','Text',''),('ORIGINE_DONNEES','Text',''),('STATUT_REPRISE_FINESS','Text',''),('UGECAM_SOURCE','Ref:UGECAM','')]:col(e,'ESMS',k,t,f)
    act(e,['ModifyColumn','ESMS','UGECAM',{'formula':'$SITE.UGECAM if $SITE else $UGECAM_SOURCE','isFormula':True}])
    col(e,'ESMS','FINESS_CODES','ChoiceList','sorted(set(list($FINESS_HISTORIQUES or []) + ([$FINESS_NORMALISE] if $FINESS_NORMALISE else [])))')
    col(e,'ESMS','FINESS_JURIDIQUES_UGECAM','ChoiceList','list($UGECAM.FINESS_JURIDIQUES or [])')
    col(e,'ESMS','FINESS_JURIDIQUE','Text','($FINESS_REF.FINESS_JURIDIQUE if $FINESS_REF else ($UGECAM.FINESS_JURIDIQUES[0] if len($UGECAM.FINESS_JURIDIQUES or []) == 1 else ""))')
    kind={};geo=collections.defaultdict(list)
    for lid,r in legacy.items():
        kk=keys(r['FINESS']);head=name(r['ESMS_raison_sociale']).startswith(('siege','dngu'))
        if head:kind[lid]=('FINESS juridique de siège',kk)
        elif kk:kind[lid]=('FINESS géographique historique',kk);[geo[k].append(r) for k in kk]
        else:kind[lid]=('Texte non FINESS' if str(r['FINESS'] or '').strip() else 'Non renseigné',[])
    for r in existing:
        ids=r['ESMS_LEGACY_IDS'] or [];codes=sorted(set(k for i in ids if i in kind and kind[i][0]=='FINESS géographique historique' for k in kind[i][1]));old=norm(r['FINESS'])
        rec={'FINESS_HISTORIQUES':['L',*codes],'FINESS_SOURCE_BRUT':' | '.join(str(legacy[i]['FINESS']) for i in ids if i in legacy),'ORIGINE_DONNEES':'Airmes','STATUT_REPRISE_FINESS':'Repris par lien historique explicite' if codes else 'Aucun FINESS historique directement associé'}
        if len(codes)==1 and (not str(r['FINESS'] or '').strip() or old==codes[0]):rec['FINESS']=codes[0]
        elif old and codes and old not in codes:rec['STATUT_REPRISE_FINESS']='FINESS actuel conservé ; historique également disponible'
        update(e,'ESMS',r['id'],**rec)
    represented={k for r in records(e,'ESMS') for k in r['FINESS_CODES'] or []};new=[];nextid=max(r['id'] for r in existing)+1
    for code,rr in sorted(geo.items()):
        if code in represented:continue
        ss={mapping[r['SITES_nomenclature_UGECAM']] for r in rr if r['SITES_nomenclature_UGECAM'] in mapping};uu={r['UGECAM'] for r in rr if r['UGECAM']};sid=next(iter(ss)) if len(ss)==1 else 0;uid=sites[sid]['UGECAM'] if sid else next(iter(uu)) if len(uu)==1 else 0;public=catalogue.get(code,{})
        addresses={str(r['ADRESSE']).strip() for r in rr if str(r['ADRESSE'] or '').strip()};coords={(r.get('Latitude'),r.get('Longitude')) for r in rr if isinstance(r.get('Latitude'),(int,float)) and isinstance(r.get('Longitude'),(int,float)) and (r['Latitude'] or r['Longitude'])};lat,lon=next(iter(coords)) if len(coords)==1 else (None,None)
        new.append({'id':nextid,'RAISON_SOCIALE':public.get('RAISON_SOCIALE') or str(rr[0]['ESMS_raison_sociale']).strip(),'SITE':sid,'UGECAM_SOURCE':uid,'TYPOLOGIE':public.get('CATEGORIE') or rr[0]['Typologie_ESMS'],'FINESS':code,'FINESS_HISTORIQUES':['L',code],'FINESS_SOURCE_BRUT':' | '.join(str(r['FINESS']) for r in rr),'ORIGINE_DONNEES':'Reprise FINESS historique','STATUT_REPRISE_FINESS':'Établissement historique — à rapprocher des services Airmes' if sid else 'Établissement historique — site à rapprocher','ESMS_LEGACY_IDS':['L',*[r['id'] for r in rr]],'ADRESSE':public.get('ADRESSE') or next(iter(addresses)) if len(addresses)==1 or public.get('ADRESSE') else '', 'Latitude':lat,'Longitude':lon,'AIRMES_ID':'','SOURCE_LIGNE':0});nextid+=1
    bulk(e,'ESMS',new)
    for item in records(e,'ESMS'):
        aliases=sorted(set(str(legacy[i]['ESMS_raison_sociale']).strip() for i in (item['ESMS_LEGACY_IDS'] or []) if i in legacy and str(legacy[i]['ESMS_raison_sociale']).strip()))
        if aliases:update(e,'ESMS',item['id'],APPELLATIONS_HISTORIQUES=['L',*aliases])
    # FINESS is not necessarily unique across services: update the exact-code
    # projection, without replacing any manually assigned FINESS value.
    act(e,['ModifyColumn','FINESS_CATALOGUE','SITES_LIES',{'isFormula':True,'formula':'sorted(set(r.SITE.id for r in ESMS.all if r.SITE and $FINESS in (r.FINESS_CODES or [])))'}])
    act(e,['ModifyColumn','FINESS_CATALOGUE','SITE',{'isFormula':True,'formula':'$SITES_LIES[0] if len($SITES_LIES) == 1 else SITES.lookupOne(id=0)'}])
    act(e,['ModifyColumn','FINESS_CATALOGUE','RATTACHEMENT',{'isFormula':True,'formula':'"Rattaché à un site" if len($SITES_LIES) == 1 else "Sites multiples — à arbitrer" if len($SITES_LIES) > 1 else "À rattacher"'}])
    table(e,'REPRISE_FINESS_HISTORIQUE',[('LIGNE_SOURCE','Ref:ESMS_Liste_UGECAM_',''),('RAISON_SOCIALE_SOURCE','Text',''),('FINESS_BRUT','Text',''),('TYPE','Text',''),('CODES_NORMALISES','ChoiceList',''),('ESMS_CIBLES','RefList:ESMS','')]);owner_only(e,'REPRISE_FINESS_HISTORIQUE')
    allnew=records(e,'ESMS');audit=[]
    for lid,r in legacy.items():
        typ,kk=kind[lid];targets=[x['id'] for x in allnew if set(x['FINESS_CODES'] or [])&set(kk)] if typ=='FINESS géographique historique' else []
        audit.append({'id':lid,'LIGNE_SOURCE':lid,'RAISON_SOCIALE_SOURCE':r['ESMS_raison_sociale'],'FINESS_BRUT':r['FINESS'],'TYPE':typ,'CODES_NORMALISES':['L',*kk],'ESMS_CIBLES':['L',*targets]})
    bulk(e,'REPRISE_FINESS_HISTORIQUE',audit)
    # Read-only projections for the original tree. Legacy directions/personal
    # columns are not exposed by restoring this widget.
    table(e,'ARBO_ESMS_REFERENCES',[('ESMS_raison_sociale','Text',''),('FINESS','Text',''),('UGECAM','Ref:UGECAM',''),('SITE_SCOPE','Ref:SITES','')]);bulk(e,'ARBO_ESMS_REFERENCES',[{'id':r['id'],'ESMS_raison_sociale':r['ESMS_raison_sociale'],'FINESS':r['FINESS'],'UGECAM':r['UGECAM'],'SITE_SCOPE':mapping.get(r['SITES_nomenclature_UGECAM'],0)} for r in legacy.values()])
    columns=[('NIVEAU'+str(i),'Text','') for i in range(10)]+[(k,t,'') for k,t in [('ARBORESCENCE','Text'),('IS_ENTITE','Bool'),('type_prestation_name','Text'),('ID_service','Text'),('parent_id','Text'),('LEVEL','Text'),('Rattachement_ESMS_liste_UGECAM','RefList:ARBO_ESMS_REFERENCES'),('UGECAM_LIBELLE','Text'),('UGECAM_SCOPE','Ref:UGECAM'),('SITE_SCOPE','Ref:SITES'),('NIVEAU_NUM','Int')]]
    table(e,'ARBORESCENCE_AIRMES_DEV',columns)
    alias={name(r['UGECAM']):r['id'] for r in ug.values()};alias.update({'ugecamidf':10,'ugecamnordest':8,'ugecamrhonealpes':7,'ugecamhautsdefrance':4})
    sitekeys={(s['UGECAM'],name(s['NOM'])):s['id'] for s in sites.values()};tree=[]
    for r in records(e,'Import_entite_AIRMES'):
        raw=r['NIVEAU1'];uid=raw if isinstance(raw,int) and raw in ug else alias.get(name(raw),0);sid=sitekeys.get((uid,name(r['NIVEAU2'])),0);level=int(r['LEVEL']) if isinstance(r['LEVEL'],(int,float)) else -1
        rec={k:str(r.get(k) or '') for k in ['NIVEAU'+str(i) for i in range(10)]+['ARBORESCENCE','type_prestation_name','ID_service','parent_id','LEVEL']};rec.update(id=r['id'],IS_ENTITE=r['IS_ENTITE'] is True,Rattachement_ESMS_liste_UGECAM=['L',*(r['Rattachement_ESMS_liste_UGECAM'] or [])],UGECAM_LIBELLE=ug.get(uid,{}).get('UGECAM',''),UGECAM_SCOPE=uid,SITE_SCOPE=sid,NIVEAU_NUM=level);tree.append(rec)
    bulk(e,'ARBORESCENCE_AIRMES_DEV',tree)
    gate="user.demande_acces.STATUT == 'Validé' and user.droits_supp.ACCES_ARBORESCENCE is True"
    scoped="(user.droits_supp.DNGU is True or (user.droits_supp.SIEGE is True and user.droits_supp.UGECAM == {ug}) or (user.droits_supp.SIEGE != True and user.droits_supp.DNGU != True and {site} != 0 and ((user.droits_supp.SITE_PRINCIPAL != 0 and user.droits_supp.SITE_PRINCIPAL == {site}) or {site} in user.droits_supp.SITES_RESP_AIRMES)))"
    acl(e,'ARBO_ESMS_REFERENCES',[('user.Access == OWNER','+CRUD'),(gate+' and '+scoped.format(ug='rec.UGECAM',site='rec.SITE_SCOPE'),'+R-CUD'),('','-CRUD')])
    context="(rec.NIVEAU_NUM == 0 or (rec.NIVEAU_NUM == 1 and rec.UGECAM_SCOPE == user.droits_supp.UGECAM))"
    acl(e,'ARBORESCENCE_AIRMES_DEV',[('user.Access == OWNER','+CRUD'),(gate+' and ('+scoped.format(ug='rec.UGECAM_SCOPE',site='rec.SITE_SCOPE')+' or '+context+')','+R-CUD'),('','-CRUD')])
    refs={t['tableId']:t['id'] for t in records(e,'_grist_Tables')}
    for r in records(e,'_grist_Views_section'):
        options=r.get('options') or '';options=options.replace('/target/v6-dev3.html','/target/v6-dev4.html').replace('/target/airmes-arborescence-v3-dev.html','/target/airmes-arborescence-v4-dev.html')
        values={'options':options}
        if r['id']==37:values.update(tableRef=refs['ARBORESCENCE_AIRMES_DEV'],title='Arborescence AIRMES')
        if options!=r.get('options') or r['id']==37:update(e,'_grist_Views_section',r['id'],**values)
    # Its custom-widget fields must belong to the restored source projection.
    gone=[r['id'] for r in records(e,'_grist_Views_section_field') if r['parentId']==37]
    if gone:act(e,['BulkRemoveRecord','_grist_Views_section_field',gone])
    cols=[r for r in records(e,'_grist_Tables_column') if r['parentId']==refs['ARBORESCENCE_AIRMES_DEV'] and r['colId']!='manualSort']
    for pos,r in enumerate(cols,1):act(e,['AddRecord','_grist_Views_section_field',None,{'parentId':37,'colRef':r['id'],'parentPos':pos}])
    after=records(e,'ESMS');available={k for r in after for k in r['FINESS_CODES'] or []};result={'juridiques_ajoutes_depuis_les_sieges':legal_added,'lignes_historiques':len(legacy),'lignes_finess_geographiques':sum(kind[i][0]=='FINESS géographique historique' for i in legacy),'finess_geographiques_distincts':len(geo),'finess_reportes':len(set(geo)&available),'nouveaux_etablissements_historiques':len(new),'esms_total':len(after),'lignes_arborescence':len(tree),'references_arborescence':len(legacy),'finess_juridiques':sum(len(r['FINESS_JURIDIQUES'] or []) for r in records(e,'UGECAM')),'repartition_sources':dict(collections.Counter(k[0] for k in kind.values()))}
    assert set(geo)<=available,'Un FINESS historique manque dans la source des fiches'
    export(e,source,destination);pathlib.Path(report).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':upgrade(*sys.argv[1:])
