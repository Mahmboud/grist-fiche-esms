import sys,json,pathlib
from offline_grist import load,records,act,objtypes
src,dst,out=sys.argv[1:];old=load(src);e=load(dst);checks=[]
for t in records(old,'_grist_Tables'):
 name=t['tableId'];before=records(old,name);after=records(e,name)
 assert len(before)==len(after),name
 for a,b in zip(before,after):
  for k,v in a.items():assert objtypes.equal_encoding(v,b[k]),(name,a['id'],k)
checks.append('Toutes les tables et cellules métier préexistantes sont inchangées')
for meta in ['_grist_ACLResources','_grist_Tables','_grist_Tables_column']:
 assert records(old,meta)==records(e,meta),meta
checks.append('Aucune modification des tables, colonnes ou ressources de droits')
a=records(old,'_grist_ACLRules');b=records(e,'_grist_ACLRules');assert len(a)==len(b)
changed=[]
for x,y in zip(a,b):
 if x!=y:
  assert 'newRec.EMAIL == user.Email' in x['aclFormula']
  assert y['aclFormula']==x['aclFormula']+" and user.demande_acces.STATUT != 'Validé'"
  for k,v in x.items():
   if k not in ['aclFormula','aclFormulaParsed']:assert v==y[k],k
  changed.append(x['id'])
assert len(changed)==1;checks.append('Une seule règle modifiée : création de nouvelle demande refusée après validation')
assert min(records(e,'_grist_Pages'),key=lambda r:r['pagePos'])['viewRef']==20;checks.append('Bienvenue est la première page, avant Administration pour tous les rôles')
act(e,['AddRecord','CONTACTS',1,dict(EMAIL='inscription@example.invalid',NOM='TEST',PRENOM='Alice',FONCTION=20,UGECAM=1,SITE_PRINCIPAL=4,SITES_RESP_AIRMES=['L',74],SIEGE=False,DNGU=False)])
f=dict(tables={r['tableId']:records(e,r['tableId']) for r in records(e,'_grist_Tables')},acl=dict(resources=records(e,'_grist_ACLResources'),rules=records(e,'_grist_ACLRules')),pages=records(e,'_grist_Pages'),views=records(e,'_grist_Views'),sections=records(e,'_grist_Views_section'))
pathlib.Path(out).write_text(json.dumps(f,ensure_ascii=False,default=objtypes.encode_object));print(json.dumps(dict(passed=len(checks),checks=checks),ensure_ascii=False,indent=2))
