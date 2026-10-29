"""Verify cleanup and export fixtures for Grist's native TS ACL compiler."""
import sys,json,pathlib,sqlite3,re
from offline_grist import load,act,records,objtypes
from upgrade_moad_r6 import RETIRED,RENAMES
old=load(sys.argv[1]);e=load(sys.argv[2]);act(e,['Calculate']);checks=[]
def check(n,b):
 assert b,n
 checks.append(n)
tables={r['tableId']:r for r in records(e,'_grist_Tables')};cols=records(e,'_grist_Tables_column');oldcols=records(old,'_grist_Tables_column');oldtables={r['tableId']:r for r in records(old,'_grist_Tables')}
for name in ['CONTACTS','SITES','UGECAM','ESMS','Autodiagnostic_DEV','Autodiagnostic_Historique_DEV','DEMANDES_ACCES','ARBORESCENCE_AIRMES_DEV','FINESS_CATALOGUE']:
 target=RENAMES.get(name,name);rr={r['id']:r for r in records(old,name)};after={r['id']:r for r in records(e,target)};live={c['colId'] for c in cols if c['parentId']==tables[target]['id'] and not c['isFormula']};physical={c['colId'] for c in oldcols if c['parentId']==oldtables[name]['id'] and not c['isFormula']}
 check(name+' : lignes, identifiants et données métier restantes préservées',rr.keys()==after.keys() and all(objtypes.equal_encoding(r[k],after[i][k]) for i,r in rr.items() for k in live&physical))
archive=records(e,'ARCHIVES_MIGRATION');retired={r['TABLE_ORIGINE']:r for r in archive if r['TYPE']=='Table retirée'}
check('Les 15 tables retirées sont archivées intégralement',set(retired)==set(RETIRED) and all(r['NB_LIGNES']==len(records(old,t))==len(json.loads(r['DONNEES_JSON'])) for t,r in retired.items()))
check('Les 72 questionnaires historiques et les 437 arbitrages restent archivés',retired['Autodiagnostic']['NB_LIGNES']==72 and retired['MIGRATION_A_ARBITRER']['NB_LIGNES']==437)
check('Les anciens identifiants de tables sont réellement retirés',{oldtables[t]['id'] for t in RETIRED}.isdisjoint({t['id'] for t in tables.values()}))
for c in cols:
 if c['type'].startswith(('Ref:','RefList:')):assert c['type'].split(':',1)[1] in tables,(c['colId'],c['type'])
check('Toutes les références pointent vers une table active',True)
check('Aucune table active ne porte de suffixe DEV',all('DEV' not in t for t in tables))
check('SITES, UGECAM et PROFIL_SESSION utilisent le préfixe masqué natif',all(t in tables for t in ['GristHidden_SITES','GristHidden_UGECAM','GristHidden_PROFIL_SESSION']) and not {'SITES','UGECAM','PROFIL_SESSION'}&tables.keys())
sql=sqlite3.connect('file:'+sys.argv[2]+'?mode=ro',uri=True)
check('SQLite est intègre',sql.execute('pragma integrity_check').fetchone()[0]=='ok')
physical={r[0] for r in sql.execute("select name from sqlite_master where type='table'") if not r[0].startswith('_grist')};check('Aucune ancienne table physique ne subsiste hors du schéma actif',physical==set(tables))
check('Aucune colonne physique orpheline ne subsiste',all({r[1] for r in sql.execute('pragma table_info("'+t+'")')}=={'id'}|{c['colId'] for c in cols if c['parentId']==tr['id']} for t,tr in tables.items()))
esms=records(e,'ESMS');fc=records(e,'FINESS_CATALOGUE');check('Dispositif retiré du modèle des ESMS',not {'DISPOSITIF','DISPOSITIF_CORRECTION'}&{c['colId'] for c in cols if c['parentId']==tables['ESMS']['id']})
oldfc={r['FINESS']:r for r in records(old,'FINESS_CATALOGUE')};check('Dispositif maintenu au niveau FINESS avec la valeur officielle',all(r['DISPOSITIF']==oldfc[r['FINESS']]['DISPOSITIF_PUBLIC'] for r in fc))
check('Aucune convention Dispositif propagée dans les JSON des ESMS',all('"DISPOSITIF"' not in r['DONNEES_PUBLIQUES_JSON'] and '"DISPOSITIFS"' not in r['DONNEES_PUBLIQUES_JSON'] for r in esms))
check('Libellé Médico-social et social appliqué aux 283 FINESS concernés',sum(r['SECTEUR']=='Médico-social et social' for r in fc)==283 and all(r['SECTEUR']!='Social et médico-social' for r in fc))
for t in tables:
 if t=='ARCHIVES_MIGRATION':continue
 err=[(r['id'],k,str(v)) for r in records(e,t) for k,v in r.items() if isinstance(v,objtypes.RaisedException)]
 check(t+' : pas d’erreur de formule',not err)
resources=records(e,'_grist_ACLResources');rules=records(e,'_grist_ACLRules');check('Aucun parcours de référence numérique imbriqué dans les ACL',not any(re.search(r'\b(?:rec|newRec)\.[A-Za-z_][A-Za-z0-9_]*\.',r['aclFormula']) for r in rules))
check('Toutes les ressources ACL nomment une table existante',all(r['tableId'].startswith('*') or r['tableId'] in tables for r in resources))
sections=records(e,'_grist_Views_section');refs={r['id']:r['tableId'] for r in tables.values()};check('Les sections utilisent des tables existantes',all(not s['tableRef'] or s['tableRef'] in refs for s in sections))
check('Toutes les URLs actives utilisent le nouveau paquet immuable',all('/widgets/moad-20261029-r6/' in s['options'] for s in sections if s['parentId'] and 'https://' in str(s.get('options'))))
check('Les titres et descriptions visibles ne contiennent plus DEV',all(not re.search(r'\bDEV\b',str(s.get('title',''))+' '+str(s.get('description',''))) for s in sections))
for t in ['REFERENTIEL_FONCTIONS','AUTODIAG_REFERENTIEL_QUESTIONS','ARCHIVES_MIGRATION']:
 rid=next(r['id'] for r in resources if r['tableId']==t and r['colIds']=='*');rr=sorted([r for r in rules if r['resource']==rid],key=lambda r:r['rulePos']);check(t+' : lecture propriétaire uniquement',rr[0]['permissionsText']=='+CRUD' and 'OWNER' in rr[0]['aclFormula'] and rr[-1]['permissionsText']=='-CRUD')
# Genuine Python engine execution with an editor identity and no EMAIL payload.
from useractions import from_repr
email='demande-test@example.invalid';payload=dict(NOM='TEST',PRENOM='Demande',FONCTION=20,UGECAM=1,SITE_AIRMES=4,SITES_RESP_AIRMES=['L'],PROFIL_ACCES='SITE',CONFIRMATION=True,STATUT='À valider',CONTACT=0)
u=dict(Email=email,Name='Test inscription',Access='editors',UserID=999,UserRef='test',Origin=None,SessionID='u999',IsLoggedIn=True,ShareRef=None,LinkKey={})
result=e.apply_user_actions([from_repr(['AddRecord','DEMANDES_ACCES',None,payload])],u);added=next(r for r in records(e,'DEMANDES_ACCES') if r['EMAIL']==email);check('Le moteur Grist renseigne lui-même l’email authentifié de la nouvelle demande',added['STATUT']=='À valider' and added['CONTACT']==0)
data={t:records(e,t) for t in tables if t!='ARCHIVES_MIGRATION'};fixture=dict(tables=data,metadata={t:records(e,t) for t in ['_grist_Tables','_grist_Tables_column','_grist_Views_section','_grist_Pages']},acl=dict(resources=resources,rules=rules),old_acl=dict(resources=records(old,'_grist_ACLResources'),rules=records(old,'_grist_ACLRules')),request=added,stored=result.stored)
pathlib.Path(sys.argv[3]).write_text(json.dumps(fixture,ensure_ascii=False,default=objtypes.encode_object))
print(json.dumps(dict(passed=len(checks),checks=checks,limits=['Données et moteur Python officiels contrôlés hors ligne ; tests du compilateur TypeScript ACL séparés.']),ensure_ascii=False,indent=2))
