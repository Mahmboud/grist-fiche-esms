"""Add public-source projections and one-click sync to the supplied V4 copy.

All existing business columns, IDs, answers and records are preserved. Source
data use separate tables and formula columns; no public file contains Grist data.
"""
import sys,json,pathlib,subprocess,tempfile
from offline_grist import load,act,records,export,objtypes
from migrate_moad_dev import col,table,bulk,update,acl,owner_only

def main(source,destination,packfile,reportfile):
 e=load(source);before_tables={r['tableId'] for r in records(e,'_grist_Tables')}
 if 'DONNEES_PUBLIQUES' in before_tables:raise ValueError('Document déjà migré ; source laissée intacte.')
 refs={r['tableId']:r['id'] for r in records(e,'_grist_Tables')};cols=records(e,'_grist_Tables_column')
 before={t:[{k:v for k,v in r.items() if k=='id' or k in {c['colId'] for c in cols if c['parentId']==refs[t] and not c['isFormula']}} for r in records(e,t)] for t in ['CONTACTS','UGECAM','SITES','ESMS','Autodiagnostic','Autodiagnostic_DEV','Autodiagnostic_Historique','Autodiagnostic_Historique_DEV','DEMANDES_ACCES']}
 for name,fin in [('UGECAM PACA-C','130037815'),('UGECAM Alsace','670013754')]:
  rr=records(e,'UGECAM');found=[r for r in rr if fin in str(r.get('FINESS_Juridique') or '').replace(' ','')]
  if not found:bulk(e,'UGECAM',[dict(id=max(r['id'] for r in rr)+1,UGECAM=name,FINESS_Juridique=fin)])
 table(e,'DONNEES_PUBLIQUES',[(k,t,'') for k,t in [('CLE','Text'),('SOURCE','Text'),('FINESS','Text'),('FINESS_JURIDIQUE','Text'),('UGECAM','Ref:UGECAM'),('DONNEES_JSON','Text'),('RESUME','Text'),('DATE_SOURCE','Text'),('SOURCE_URL','Text'),('DATE_EXTRACTION','Text'),('PRESENT_SOURCE','Bool')]]+[('ETABLISSEMENT','Ref:FINESS_CATALOGUE','FINESS_CATALOGUE.lookupOne(FINESS=$FINESS)')])
 table(e,'REFERENTIEL_FINESS',[(k,'Text','') for k in ['CLE','CODE','LIBELLE','DOMAINE','PARENT','STATUT','VERSION','SOURCE_URL','DATE_SOURCE','SECTEUR_CORRECTION']]);owner_only(e,'REFERENTIEL_FINESS')
 table(e,'SOURCES_PUBLIQUES',[(k,'Text','') for k in ['SOURCE','LIBELLE','STATUT','DATE_SOURCE','DATE_VERIFICATION','DATE_EXTRACTION','URL','SHA256','AVERTISSEMENT']]+[('NB_FINESS','Int','')]);owner_only(e,'SOURCES_PUBLIQUES')
 table(e,'ACTUALISATIONS_PUBLIQUES',[(k,'Text','') for k in ['DATE','SNAPSHOT','STATUT','BILAN_JSON','RESTAURATION_JSON']]);owner_only(e,'ACTUALISATIONS_PUBLIQUES')
 gate="user.demande_acces.STATUT == 'Validé' and user.droits_supp.ACCES_LISTE_ESMS is True"
 scope="(user.droits_supp.DNGU is True or (user.droits_supp.SIEGE is True and user.droits_supp.UGECAM == rec.ETABLISSEMENT.UGECAM) or (user.droits_supp.SIEGE != True and user.droits_supp.DNGU != True and user.droits_supp.id in rec.ETABLISSEMENT.CONTACTS_PERIMETRE))"
 acl(e,'DONNEES_PUBLIQUES',[('user.Access == OWNER','+CRUD'),(gate+' and rec.ETABLISSEMENT != 0 and '+scope,'+R-CUD'),('','-CRUD')])
 col(e,'FINESS_CATALOGUE','SOURCE_PUBLIQUE','Ref:DONNEES_PUBLIQUES','DONNEES_PUBLIQUES.lookupOne(CLE="structures:" + $FINESS)')
 col(e,'FINESS_CATALOGUE','DATE_EXTRACTION_PUBLIQUE','Text','$SOURCE_PUBLIQUE.DATE_EXTRACTION')
 col(e,'FINESS_CATALOGUE','DONNEES_PUBLIQUES_JSON','Text','''import json
return json.dumps([{"source":r.SOURCE,"resume":r.RESUME,"date":r.DATE_SOURCE,"url":r.SOURCE_URL,"donnees":json.loads(r.DONNEES_JSON or "{}")} for r in DONNEES_PUBLIQUES.lookupRecords(FINESS=$FINESS) if r.PRESENT_SOURCE], ensure_ascii=False)''')
 fields={'NOM_PUBLIC':'RAISON_SOCIALE','CATEGORIE_CODE_PUBLIC':'CATEGORIE_CODE','CATEGORIE_PUBLIC':'CATEGORIE','ADRESSE_PUBLIQUE':'ADRESSE','DISPOSITIF_PUBLIC':'DISPOSITIF','ETAT_PUBLIC':'ETAT','DATE_FERMETURE_PUBLIQUE':'DATE_FERMETURE','DATE_OUVERTURE_PUBLIQUE':'DATE_OUVERTURE','DATE_MAJ_PUBLIQUE':'DATE_MAJ_SOURCE','SECTEUR_SUGGERE':'SECTEUR_SUGGERE'}
 for k,src in fields.items():col(e,'FINESS_CATALOGUE',k,'Text',f'''import json
return str(json.loads($SOURCE_PUBLIQUE.DONNEES_JSON or "{{}}").get("{src}") or "") if $SOURCE_PUBLIQUE.PRESENT_SOURCE else ""''')
 col(e,'FINESS_CATALOGUE','CATEGORIE_REFERENTIEL','Ref:REFERENTIEL_FINESS','REFERENTIEL_FINESS.lookupOne(CLE="categorie:"+($CATEGORIE_CODE_PUBLIC or $CATEGORIE_CODE))')
 col(e,'FINESS_CATALOGUE','SECTEUR','Text','$CATEGORIE_REFERENTIEL.SECTEUR_CORRECTION or $SECTEUR_SUGGERE or "À qualifier"')
 col(e,'ESMS','DISPOSITIF_CORRECTION','Text')
 col(e,'FINESS_CATALOGUE','DISPOSITIF','Text','''vv = sorted(set(r.DISPOSITIF_CORRECTION.strip() for r in ESMS.all if $FINESS in (r.FINESS_CODES or []) and r.DISPOSITIF_CORRECTION.strip()))
return " · ".join(vv) if vv else $DISPOSITIF_PUBLIC''')
 col(e,'ESMS','DISPOSITIF','Text','''return $DISPOSITIF_CORRECTION or " · ".join(sorted(set(r.DISPOSITIF for r in FINESS_CATALOGUE.all if r.FINESS in ($FINESS_CODES or []) and r.DISPOSITIF)))''')
 col(e,'ESMS','SECTEUR','Text','''return " · ".join(sorted(set(r.SECTEUR for r in FINESS_CATALOGUE.all if r.FINESS in ($FINESS_CODES or []) and r.SECTEUR)))''')
 col(e,'ESMS','DONNEES_PUBLIQUES_JSON','Text','''import json
return json.dumps([{"finess":r.FINESS,"nom":r.NOM_PUBLIC or r.RAISON_SOCIALE,"sources":json.loads(r.DONNEES_PUBLIQUES_JSON or "[]")} for r in FINESS_CATALOGUE.all if r.FINESS in ($FINESS_CODES or [])], ensure_ascii=False)''')
 for status,name in [('09','PLACES_AUTORISEES_PUBLIQUES'),('08','PLACES_INSTALLEES_PUBLIQUES')]:
  col(e,'FINESS_CATALOGUE',name,'Numeric',f'''import json
if not $SOURCE_PUBLIQUE.PRESENT_SOURCE or $ETAT_PUBLIC != "A" or $DATE_FERMETURE_PUBLIQUE: return None
vv = [v.get("nombre") for v in json.loads($SOURCE_PUBLIQUE.DONNEES_JSON or "{{}}").get("CAPACITES", []) if v.get("unite") == "02" and v.get("statut") == "{status}"]
return sum(vv) if vv else None''')
 # Use the same JS planner in the offline migration and in the live widget.
 state={t:records(e,t) for t in ['UGECAM','FINESS_CATALOGUE','DONNEES_PUBLIQUES','REFERENTIEL_FINESS','SOURCES_PUBLIQUES']}
 for t,rr in state.items():
  for r in rr:
   for k,v in list(r.items()):
    if isinstance(v,tuple):r[k]=list(v)
 root=pathlib.Path(__file__).resolve().parents[1];planner=root/'dev/moad-airmes-20261028/target/public-sync-v1-dev.js'
 program='const fs=require("fs"),p=require(process.argv[1]),data=JSON.parse(fs.readFileSync(0,"utf8"));process.stdout.write(JSON.stringify(p.plan(data.pack,data.state,data.hash)));'
 import hashlib,gzip
 blob=pathlib.Path(packfile).read_bytes();raw=gzip.decompress(blob) if str(packfile).endswith('.gz') else blob;snapshot=hashlib.sha256(blob).hexdigest()
 result=subprocess.run(['node','-e',program,str(planner)],input=json.dumps(dict(pack=json.loads(raw),state=state,hash=snapshot),default=str),text=True,capture_output=True,check=True);plan=json.loads(result.stdout)
 act(e,*plan['actions'])
 # New URLs only. The original full Airmes tree is unchanged.
 paths={'v6-dev4.html':'v6-dev5.html','liste-finess-v1-dev.html':'liste-finess-v2-dev.html'}
 for r in records(e,'_grist_Views_section'):
  old=r.get('options') or '';new=old
  for a,b in paths.items():new=new.replace('/target/'+a,'/target/'+b)
  if new!=old:update(e,'_grist_Views_section',r['id'],options=new)
 # Remove only supplemental raw-table pages from navigation, never their data.
 extra_names={'SITES','ESMS','Autodiagnostic_DEV','Autodiagnostic_Historique_DEV','MIGRATION_A_ARBITRER','MIGRATION_SITES','PROFIL_SESSION','FINESS_CATALOGUE','FINESS_EQUIPEMENTS','FINESS_IMPORTS','FINESS_ACCES_PAGE','REPRISE_FINESS_HISTORIQUE','ARBO_ESMS_REFERENCES','ARBORESCENCE_AIRMES_DEV','DONNEES_PUBLIQUES','REFERENTIEL_FINESS','SOURCES_PUBLIQUES','ACTUALISATIONS_PUBLIQUES'}
 views={v['id']:v for v in records(e,'_grist_Views')};gone=[p['id'] for p in records(e,'_grist_Pages') if views.get(p['viewRef'],{}).get('name') in extra_names]
 if gone:act(e,['BulkRemoveRecord','_grist_Pages',gone])
 act(e,['Calculate'])
 # Existing business data are compared by their original columns, including IDs.
 for t,rr in before.items():
  after={r['id']:r for r in records(e,t)}
  for r in rr:
   assert all(after[r['id']][k]==v for k,v in r.items()),'Donnée préexistante modifiée : '+t+':'+str(r['id'])
 export(e,source,destination)
 report=dict(source_preserved=source,destination=destination,snapshot=snapshot,bilan=plan['summary'],ugecam=[{'id':r['id'],'nom':r['UGECAM'],'finess_juridique':r['FINESS_Juridique']} for r in records(e,'UGECAM')],pages_retirees=len(gone),tables_business_preservees=list(before),tables={t:len(records(e,t)) for t in ['FINESS_CATALOGUE','DONNEES_PUBLIQUES','REFERENTIEL_FINESS','SOURCES_PUBLIQUES','ACTUALISATIONS_PUBLIQUES']})
 pathlib.Path(reportfile).write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main(*sys.argv[1:])
