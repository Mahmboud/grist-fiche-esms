"""Clean a V5 copy, preserve retired data in one owner-only archive, fix signup.

All mutations use the official Grist engine. The exported SQLite copy is rebuilt
to the registered schema so removed tables/columns do not survive as orphans.
The input document is read only and is never overwritten.
"""
import sys,json,pathlib,sqlite3,marshal,re
from offline_grist import load,act,records,export,objtypes,decode
from migrate_moad_dev import col,table,bulk,update,acl,owner_only
from predicate_formula import parse_predicate_formula

RENAMES={'SITES':'GristHidden_SITES','UGECAM':'GristHidden_UGECAM','PROFIL_SESSION':'GristHidden_PROFIL_SESSION','Autodiagnostic_DEV':'Autodiagnostic','Autodiagnostic_Historique_DEV':'Autodiagnostic_Historique','ARBORESCENCE_AIRMES_DEV':'ARBORESCENCE_AIRMES'}
RETIRED=['ESMS_Liste_UGECAM__summary_UGECAM','ESMS_Liste_UGECAM__summary_SITES_nomenclature_UGECAM_UGECAM','ESMS_liste_a_partir_sites_AIRMES','REFERENTIEL_INSCRIPTION_ESMS','REPRISE_FINESS_HISTORIQUE','MIGRATION_A_ARBITRER','MIGRATION_SITES','FINESS_IMPORTS','FINESS_EQUIPEMENTS','Autodiagnostic_Historique','Autodiagnostic','SITES_nomenclature_AIRMES','SITES_nomenclature_UGECAM','ESMS_Liste_UGECAM_','Import_entite_AIRMES']
def dumps(v):return json.dumps(v,ensure_ascii=False,default=objtypes.encode_object)
def modify(e,t,c,**v):act(e,['ModifyColumn',t,c,v])
def cols(e,t):
 ref=next(r['id'] for r in records(e,'_grist_Tables') if r['tableId']==t)
 return [c for c in records(e,'_grist_Tables_column') if c['parentId']==ref]
def preserve_archive(e,source):
 table(e,'ARCHIVES_MIGRATION',[('TABLE_ORIGINE','Text',''),('TYPE','Text',''),('SCHEMA_JSON','Text',''),('DONNEES_JSON','Text',''),('NB_LIGNES','Int','')]);owner_only(e,'ARCHIVES_MIGRATION')
 db=sqlite3.connect('file:'+str(source)+'?mode=ro',uri=True);out=[]
 for t in RETIRED:
  cur=db.execute('SELECT * FROM "'+t+'"');keys=[k[0] for k in cur.description];rr=[{k:objtypes.encode_object(decode(v)) for k,v in zip(keys,row)} for row in cur]
  out.append(dict(TABLE_ORIGINE=t,TYPE='Table retirée',SCHEMA_JSON=dumps(cols(e,t)),DONNEES_JSON=json.dumps(rr,ensure_ascii=False),NB_LIGNES=len(rr)))
 # Keep original values of compatibility fields before dropping their live refs.
 for t,keys in [('CONTACTS',['SITES_nomenclature_UGECAM','SITES_EN_RESPONSABILITE','ESMS_Liste_UGECAM_','Typologie_ESMS_depuis_Liste_UGECAM']),('DEMANDES_ACCES',['SITE','ESMS','SITES_EN_RESPONSABILITE']),('ESMS',['ESMS_LEGACY_IDS','DISPOSITIF','DISPOSITIF_CORRECTION']),('Autodiagnostic_DEV',['SITES_nomenclatures_UGECAM'])]:
  rr=[{k:objtypes.encode_object(v) for k,v in r.items() if k=='id' or k in keys} for r in records(e,t)]
  out.append(dict(TABLE_ORIGINE=t,TYPE='Champs de compatibilité retirés',SCHEMA_JSON=dumps([c for c in cols(e,t) if c['colId'] in keys]),DONNEES_JSON=json.dumps(rr,ensure_ascii=False),NB_LIGNES=len(rr)))
 db.close();bulk(e,'ARCHIVES_MIGRATION',out);return out
def main(source,destination,reportfile):
 if pathlib.Path(source).resolve()==pathlib.Path(destination).resolve():raise ValueError('Une nouvelle copie est obligatoire.')
 e=load(source)
 if any(t['tableId']=='ARCHIVES_MIGRATION' for t in records(e,'_grist_Tables')):raise ValueError('Copie déjà migrée.')
 before={t:records(e,t) for t in ['CONTACTS','SITES','UGECAM','ESMS','Autodiagnostic_DEV','Autodiagnostic_Historique_DEV','DEMANDES_ACCES','ARBORESCENCE_AIRMES_DEV']}
 archives=preserve_archive(e,source)
 # No ESMS/service-level propagation of administrative FINESS conventions.
 modify(e,'FINESS_CATALOGUE','DISPOSITIF',formula='$DISPOSITIF_PUBLIC',isFormula=True)
 modify(e,'FINESS_CATALOGUE','SECTEUR_SUGGERE',formula='''import json
s = str(json.loads($SOURCE_PUBLIQUE.DONNEES_JSON or "{}").get("SECTEUR_SUGGERE") or "") if $SOURCE_PUBLIQUE.PRESENT_SOURCE else ""
return "Médico-social et social" if s == "Social et médico-social" else s''',isFormula=True)
 modify(e,'FINESS_CATALOGUE','SECTEUR',formula='''s = $CATEGORIE_REFERENTIEL.SECTEUR_CORRECTION or $SECTEUR_SUGGERE or "À qualifier"
return "Médico-social et social" if s == "Social et médico-social" else s''',isFormula=True)
 modify(e,'ESMS','DONNEES_PUBLIQUES_JSON',formula='''import json
out = []
for r in FINESS_CATALOGUE.all:
  if r.FINESS not in ($FINESS_CODES or []): continue
  sources = json.loads(r.DONNEES_PUBLIQUES_JSON or "[]")
  for source in sources:
    if source.get("source") == "structures":
      source.get("donnees", {}).pop("DISPOSITIF", None)
      source.get("donnees", {}).pop("DISPOSITIFS", None)
  out.append({"finess":r.FINESS,"nom":r.NOM_PUBLIC or r.RAISON_SOCIALE,"sources":sources})
return json.dumps(out, ensure_ascii=False)''',isFormula=True)
 # Replace legacy capacity formulas before retiring their old 2026-05 feed.
 modify(e,'FINESS_CATALOGUE','NB_PLACES_AUTORISEES',formula='$PLACES_AUTORISEES_PUBLIQUES',isFormula=True)
 modify(e,'FINESS_CATALOGUE','NB_PLACES_INSTALLEES',formula='$PLACES_INSTALLEES_PUBLIQUES',isFormula=True)
 modify(e,'FINESS_CATALOGUE','STATUT_CAPACITES',formula='''import json
return json.loads($SOURCE_PUBLIQUE.DONNEES_JSON or "{}").get("STATUT_CAPACITES", "Non renseigné dans la source actuelle")''',isFormula=True)
 remove={'CONTACTS':['SITES_nomenclature_UGECAM','SITES_EN_RESPONSABILITE','ESMS_Liste_UGECAM_','Typologie_ESMS_depuis_Liste_UGECAM','gristHelper_Display','gristHelper_Display5','gristHelper_Display_SitesResponsabilite'], 'DEMANDES_ACCES':['SITE','ESMS','SITES_EN_RESPONSABILITE','gristHelper_Display_SitesResponsabilite'], 'ESMS':['ESMS_LEGACY_IDS','DISPOSITIF','DISPOSITIF_CORRECTION'], 'Autodiagnostic_DEV':['SITES_nomenclatures_UGECAM']}
 # Strip the retired identity column from column-level ACL before removal.
 for res in records(e,'_grist_ACLResources'):
  if res['tableId']=='Autodiagnostic_DEV' and 'SITES_nomenclatures_UGECAM' in res['colIds']:
   update(e,'_grist_ACLResources',res['id'],colIds=','.join(c for c in res['colIds'].split(',') if c!='SITES_nomenclatures_UGECAM'))
 for t,kk in remove.items():
  for k in kk:
   if k in {c['colId'] for c in cols(e,t)}:act(e,['RemoveColumn',t,k])
 # Collapsed historical summary uses the retained, scoped Airmes projection.
 for r in records(e,'_grist_Views_section_field'):
  if r['parentId']==195:act(e,['RemoveRecord','_grist_Views_section_field',r['id']])
 act(e,['RemoveRecord','_grist_Views_section',195])
 layout=json.loads(next(v['layoutSpec'] for v in records(e,'_grist_Views') if v['id']==9));layout['collapsed']=[s for s in layout.get('collapsed',[]) if s.get('leaf')!=195];update(e,'_grist_Views',9,layoutSpec=json.dumps(layout))
 # Every remaining reference/formula to retired tables must now be gone.
 for c in records(e,'_grist_Tables_column'):
  parent=next(t['tableId'] for t in records(e,'_grist_Tables') if t['id']==c['parentId'])
  if parent in RETIRED or parent=='ARCHIVES_MIGRATION':continue
  assert c['type'].split(':',1)[-1] not in RETIRED,(parent,c['colId'],c['type'])
  assert not any(re.search(r'\b'+re.escape(t)+r'\b',c['formula']) for t in RETIRED),(parent,c['colId'],c['formula'])
 # Break references between already archived tables before removal. Otherwise
 # Grist asks its web process to format those discarded references as text.
 for c in list(records(e,'_grist_Tables_column')):
  parent=next((t['tableId'] for t in records(e,'_grist_Tables') if t['id']==c['parentId']),None)
  if parent is None:continue
  if parent in RETIRED and c['type'].split(':',1)[-1] in RETIRED:
   if parent in {t['tableId'] for t in records(e,'_grist_Tables')} and c['colId'] in {x['colId'] for x in cols(e,parent)}:
    act(e,['RemoveColumn',parent,c['colId']])
 for t in RETIRED:
  if t in {r['tableId'] for r in records(e,'_grist_Tables')}:act(e,['RemoveTable',t])
 retired_resources={r['id'] for r in records(e,'_grist_ACLResources') if r['tableId'] in RETIRED}
 stale_rules=[r['id'] for r in records(e,'_grist_ACLRules') if r['resource'] in retired_resources]
 if stale_rules:act(e,['BulkRemoveRecord','_grist_ACLRules',stale_rules])
 if retired_resources:act(e,['BulkRemoveRecord','_grist_ACLResources',sorted(retired_resources)])
 for old,new in RENAMES.items():act(e,['RenameTable',old,new])
 # The registration grant must not deny Read on the very row it creates.
 # Own-row read remains available independently of creation, with no U/D grant.
 owner_only(e,'DEMANDES_ACCES')
 rid=next(r['id'] for r in records(e,'_grist_ACLResources') if r['tableId']=='DEMANDES_ACCES' and r['colIds']=='*')
 deny=next(r['id'] for r in records(e,'_grist_ACLRules') if r['resource']==rid and not r['aclFormula']);update(e,'_grist_ACLRules',deny,rulePos=100)
 create="user.IsLoggedIn is True and user.Access == EDITOR and newRec.EMAIL == user.Email and newRec.STATUT == 'À valider' and newRec.CONTACT == 0 and not newRec.DATE_VALIDATION and not newRec.VALIDE_PAR and newRec.CONFIRMATION is True and newRec.PROFIL_ACCES in ['SITE', 'SIEGE', 'DNGU']"
 for pos,expr,perm in [(10,create,'+CR'),(20,'user.IsLoggedIn is True and rec.EMAIL == user.Email','+R-UD')]:
  act(e,['AddRecord','_grist_ACLRules',None,dict(resource=rid,aclFormula=expr,aclFormulaParsed=parse_predicate_formula(expr),permissionsText=perm,rulePos=pos)])
 # Fix reference traversal in the history/facts rules. Server ACL references are
 # numeric, so scope is projected onto direct columns before evaluation.
 col(e,'Autodiagnostic_Historique','SITE_DROITS','Ref:GristHidden_SITES','$Site.SITE')
 col(e,'Autodiagnostic_Historique','UGECAM_DROITS','Ref:GristHidden_UGECAM','$Site.UGECAM')
 col(e,'DONNEES_PUBLIQUES','CONTACTS_DROITS','RefList:CONTACTS','$ETABLISSEMENT.CONTACTS_PERIMETRE')
 valid="user.demande_acces.STATUT == 'Validé'"
 scope="(user.droits_supp.DNGU is True or (user.droits_supp.SIEGE is True and user.droits_supp.UGECAM == rec.UGECAM_DROITS) or (user.droits_supp.SIEGE != True and user.droits_supp.DNGU != True and rec.SITE_DROITS != 0 and (user.droits_supp.SITE_PRINCIPAL == rec.SITE_DROITS or rec.SITE_DROITS in user.droits_supp.SITES_RESP_AIRMES)))"
 owner_only(e,'Autodiagnostic_Historique');hr=next(r['id'] for r in records(e,'_grist_ACLResources') if r['tableId']=='Autodiagnostic_Historique');hd=next(r['id'] for r in records(e,'_grist_ACLRules') if r['resource']==hr and not r['aclFormula']);update(e,'_grist_ACLRules',hd,rulePos=100)
 # A user's append is admitted only for their own identity and a site in scope.
 # Direct creation scope columns are supplied by the widget and cannot be read
 # as a way to authorize another Site: SITE_LIEN is checked against allowed rows.
 for pos,expr,perm in [(10,valid+' and user.droits_supp.ACCES is True and '+scope,'+R'),(15,valid+" and user.droits_supp.ACCES is True and newRec.Auteur_contact == user.droits_supp.id and newRec.Site in user.droits_supp.AUTODIAGS_AUTORISES",'+CR')]:
  act(e,['AddRecord','_grist_ACLRules',None,dict(resource=hr,aclFormula=expr,aclFormulaParsed=parse_predicate_formula(expr),permissionsText=perm,rulePos=pos)])
 col(e,'CONTACTS','AUTODIAGS_AUTORISES','RefList:Autodiagnostic','''return [r.id for r in Autodiagnostic.all if $ACCES and ($DNGU or ($SIEGE and r.UGECAM.id == $UGECAM.id) or (not $SIEGE and not $DNGU and (r.SITE.id == $SITE_PRINCIPAL.id or r.SITE.id in [s.id for s in $SITES_RESP_AIRMES])))]''')
 owner_only(e,'DONNEES_PUBLIQUES');dr=next(r['id'] for r in records(e,'_grist_ACLResources') if r['tableId']=='DONNEES_PUBLIQUES');dd=next(r['id'] for r in records(e,'_grist_ACLRules') if r['resource']==dr and not r['aclFormula']);update(e,'_grist_ACLRules',dd,rulePos=100)
 ds=valid+" and user.droits_supp.ACCES_LISTE_ESMS is True and rec.ETABLISSEMENT != 0 and (user.droits_supp.DNGU is True or (user.droits_supp.SIEGE is True and user.droits_supp.UGECAM == rec.UGECAM) or (user.droits_supp.SIEGE != True and user.droits_supp.DNGU != True and user.droits_supp.id in rec.CONTACTS_DROITS))"
 act(e,['AddRecord','_grist_ACLRules',None,dict(resource=dr,aclFormula=ds,aclFormulaParsed=parse_predicate_formula(ds),permissionsText='+R-CUD',rulePos=10)])
 acl(e,'DONNEES_PUBLIQUES',[('user.Access == OWNER','+CRUD'),('','-CRUD')],'CONTACTS_DROITS')
 # rulePos is a shared PositionNumber column. Reusing small positions for new
 # resources can trigger global rebalancing and place a deny before a grant.
 # Assign distinct, ordered positions in one bulk action after all ACL edits.
 resources=records(e,'_grist_ACLResources');allrules=records(e,'_grist_ACLRules');ordered=[]
 for res in sorted(resources,key=lambda r:r['id']):
  rr=sorted([r for r in allrules if r['resource']==res['id']],key=lambda r:r['rulePos'])
  if res['colIds']=='*' and res['tableId'] in ['DEMANDES_ACCES','Autodiagnostic_Historique','DONNEES_PUBLIQUES']:
   def rank(r):
    if 'OWNER' in r['aclFormula']:return 0
    if not r['aclFormula']:return 99
    if res['tableId']=='DEMANDES_ACCES':return 1 if 'newRec.EMAIL' in r['aclFormula'] else 2
    return 2 if 'newRec.' in r['aclFormula'] else 1
   rr.sort(key=rank)
  ordered.extend(rr)
 act(e,['BulkUpdateRecord','_grist_ACLRules',[r['id'] for r in ordered],{'rulePos':[10000+i*10 for i in range(len(ordered))]}])
 # New immutable widget bundle, with no development labels in the interface.
 manifest=json.loads((pathlib.Path(__file__).resolve().parents[1]/'widgets/moad-20261029-r6/manifest.json').read_text());base='https://mahmboud.github.io/grist-fiche-esms/widgets/moad-20261029-r6/'
 for s in records(e,'_grist_Views_section'):
  old=s.get('options') or '';new=old
  for a,b in manifest['files'].items():new=new.replace('https://mahmboud.github.io/grist-fiche-esms/dev/moad-airmes-20261028/target/'+a,base+b)
  values={}
  if new!=old:values['options']=new
  for field in ['title','description']:
   value=s.get(field) or ''
   clean=re.sub(r'(?i)\bDEV\b\s*[—·:-]?\s*','',value).replace('Migration Airmes — recette requise','')
   if clean!=value:values[field]=clean
  if values:update(e,'_grist_Views_section',s['id'],**values)
 # Keep only existing business pages; hidden reference views are managed in Admin.
 original_pages={3,9,19,20,21,22,34}
 for p in records(e,'_grist_Pages'):
  if p['id'] not in original_pages:act(e,['RemoveRecord','_grist_Pages',p['id']])
 act(e,['Calculate'])
 errors=[]
 for t in ['CONTACTS','GristHidden_SITES','GristHidden_UGECAM','ESMS','Autodiagnostic','Autodiagnostic_Historique','DEMANDES_ACCES','FINESS_CATALOGUE','DONNEES_PUBLIQUES']:
  errors.extend((t,r['id'],k,str(v)) for r in records(e,t) for k,v in r.items() if isinstance(v,objtypes.RaisedException))
 assert not errors,errors[:10]
 for old,rr in before.items():
  target=RENAMES.get(old,old);after={r['id']:r for r in records(e,target)};keep={c['colId'] for c in cols(e,target) if not c['isFormula']}
  for r in rr:
   for k,v in r.items():
    if k=='id' or k in keep:assert objtypes.equal_encoding(after[r['id']][k],v),(old,r['id'],k)
 export(e,source,destination)
 # Rebuild each user table to the exact live schema, retaining every registered
 # cell verbatim. Old physical tables/columns are already archived above.
 db=sqlite3.connect(destination);names={t['tableId'] for t in records(e,'_grist_Tables')}
 for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
  if not name.startswith('_grist') and name not in names:db.execute('DROP TABLE "'+name+'"')
 for name in names:
  registered=['id']+[c['colId'] for c in cols(e,name)];physical=[r[1] for r in db.execute('PRAGMA table_info("'+name+'")')]
  for k in physical:
   if k not in registered:db.execute('ALTER TABLE "'+name+'" DROP COLUMN "'+k+'"')
 db.commit();db.execute('VACUUM');assert db.execute('pragma integrity_check').fetchone()[0]=='ok';db.close()
 report=dict(tables_retirees=RETIRED,archives=len(archives),lignes_archivees=sum(r['NB_LIGNES'] for r in archives),renommages=RENAMES,tables_finales=sorted(names),widgets=base,source_preservee=source,sortie=destination)
 pathlib.Path(reportfile).write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main(*sys.argv[1:])
