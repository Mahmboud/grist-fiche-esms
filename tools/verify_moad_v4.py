"""Verify complete historical FINESS coverage and restored-tree permissions."""
import sys,json,types
from offline_grist import load,records,objtypes,act
from upgrade_moad_dev_v4 import norm,keys,name
old=load(sys.argv[1]);e=load(sys.argv[2]);act(e,['Calculate']);checks=[]
def check(n,b):
    assert b,n
    checks.append(n)
for table in ['CONTACTS','UGECAM','ESMS_Liste_UGECAM_','Import_entite_AIRMES','Autodiagnostic','Autodiagnostic_DEV','DEMANDES_ACCES']:
    before={r['id']:r for r in records(old,table)};after={r['id']:r for r in records(e,table)};ref=next(t['id'] for t in records(old,'_grist_Tables') if t['tableId']==table);physical=[c['colId'] for c in records(old,'_grist_Tables_column') if c['parentId']==ref and not c['isFormula']]
    check(table+' : lignes et données physiques préservées',before.keys()==after.keys() and all(objtypes.equal_encoding(before[i][k],after[i][k]) for i in before for k in physical))
legacy=records(e,'ESMS_Liste_UGECAM_');codes={k for r in legacy if not name(r['ESMS_raison_sociale']).startswith(('siege','dngu')) for k in keys(r['FINESS'])};allrows=records(e,'ESMS')
check('145 FINESS géographiques distincts présents dans le champ FINESS des fiches',len(codes)==145 and codes<={norm(r['FINESS']) for r in allrows})
check('157 lignes sources FINESS géographiques tracées',sum(r['TYPE']=='FINESS géographique historique' for r in records(e,'REPRISE_FINESS_HISTORIQUE'))==157)
check('Les 11 FINESS juridiques UGECAM sont repris comme identifiants juridiques',sum(len(r['FINESS_JURIDIQUES'] or []) for r in records(e,'UGECAM'))==11)
check('Les sièges ne sont pas ajoutés comme faux ESMS géographiques',not any(name(r['RAISON_SOCIALE']).startswith(('siege','dngu')) for r in allrows if r['ORIGINE_DONNEES']=='Reprise FINESS historique'))
before={r['id']:r for r in records(old,'ESMS')};after={r['id']:r for r in allrows};keep=['RAISON_SOCIALE','SITE','UGECAM','TYPOLOGIE','ADRESSE','Latitude','Longitude','AIRMES_ID','SOURCE_LIGNE','ESMS_LEGACY_IDS']
check('Les 304 lignes Airmes déjà présentes restent intactes',all(all(objtypes.equal_encoding(r[k],after[i][k]) for k in keep) for i,r in before.items()))
extra=[r for r in allrows if r['id'] not in before];check('128 établissements historiques identifiés sans identifiant Airmes inventé',len(extra)==128 and all(not r['AIRMES_ID'] and r['SOURCE_LIGNE']==0 and 'historique' in r['STATUT_REPRISE_FINESS'] for r in extra))
check('Les sites inconnus restent explicitement à rapprocher',all(r['UGECAM_SOURCE'] and 'site à rapprocher' in r['STATUT_REPRISE_FINESS'] for r in extra if not r['SITE']))
tree=records(e,'ARBORESCENCE_AIRMES_DEV');raw=records(e,'Import_entite_AIRMES');check('Arborescence : les 1174 lignes sources sont conservées',{r['id'] for r in tree}=={r['id'] for r in raw} and len(tree)==1174)
check('Arborescence : les dix niveaux sont prévus',all('NIVEAU'+str(i) in tree[0] for i in range(10)))
check('Arborescence : les 168 noms et références ESMS historiques restent disponibles',{r['id'] for r in records(e,'ARBO_ESMS_REFERENCES')}=={r['id'] for r in legacy})
for t in ['UGECAM','ESMS','FINESS_CATALOGUE','ARBORESCENCE_AIRMES_DEV','ARBO_ESMS_REFERENCES']:
    errors=[(r['id'],k) for r in records(e,t) for k,v in r.items() if isinstance(v,objtypes.RaisedException)]
    check(t+' sans erreur dans ses cellules',not errors)
resources=records(e,'_grist_ACLResources');rules=records(e,'_grist_ACLRules');ns=types.SimpleNamespace
def user(valid=True,arbo=True,siege=False,dngu=False,uid=1,main=4,other=[33],role='editors'):
    return ns(Access=role,demande_acces=ns(STATUT='Validé' if valid else 'À valider'),droits_supp=ns(ACCES_ARBORESCENCE=arbo,SIEGE=siege,DNGU=dngu,UGECAM=uid,SITE_PRINCIPAL=main,SITES_RESP_AIRMES=other))
def allow(u,r):
    rid=next(x['id'] for x in resources if x['tableId']=='ARBORESCENCE_AIRMES_DEV' and x['colIds']=='*')
    for rule in sorted((r for r in rules if r['resource']==rid),key=lambda r:r['rulePos']):
        if not rule['aclFormula'] or eval(rule['aclFormula'],{'__builtins__':{},'OWNER':'owners'},{'user':u,'rec':r}):return rule['permissionsText']
r=ns(UGECAM_SCOPE=1,SITE_SCOPE=4,NIVEAU_NUM=4)
check('Arborescence refusée avant validation ou sans droit',allow(user(valid=False),r)==allow(user(arbo=False),r)=='-CRUD')
check('Arborescence standard limitée au principal et aux responsabilités',allow(user(),r)=='+R-CUD' and allow(user(main=9999,other=[]),r)=='-CRUD')
check('Arborescence Siège et DNGU cohérente avec le périmètre',allow(user(siege=True),r)=='+R-CUD' and allow(user(siege=True,uid=2),r)=='-CRUD' and allow(user(dngu=True,uid=2),r)=='+R-CUD')
sec=next(r for r in records(e,'_grist_Views_section') if r['id']==37);ref=next(t['id'] for t in records(e,'_grist_Tables') if t['tableId']=='ARBORESCENCE_AIRMES_DEV');check('Vue originale rebranchée sur la hiérarchie complète',sec['tableRef']==ref and 'airmes-arborescence-v4-dev.html' in sec['options'])
print(json.dumps({'passed':len(checks),'checks':checks,'limits':['Matrice des prédicats testée hors ligne ; recette multi-comptes requise']},ensure_ascii=False,indent=2))
