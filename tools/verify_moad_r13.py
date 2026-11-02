"""Verify copy preservation and export real email-trigger action snapshots."""
import pathlib,json,sys,sqlite3
from offline_grist import load,records,objtypes
from useractions import from_repr
from actions import get_action_repr
from usertypes import get_type_default
src,dst,out=sys.argv[1:];old=load(src);e=load(dst);checks=[]
for t in records(old,'_grist_Tables'):
 name=t['tableId'];a=records(old,name);b=records(e,name)
 assert len(a)==len(b) and all(x.keys()==y.keys() and all(objtypes.equal_encoding(v,y[k]) for k,v in x.items()) for x,y in zip(a,b)),name
 checks.append(name+' : données conservées')
for meta in ['_grist_Tables','_grist_Tables_column','_grist_ACLResources','_grist_Views','_grist_Views_section_field','_grist_DocInfo']:
 assert records(old,meta)==records(e,meta),meta
checks.append('Schéma, ressources ACL, vues et colonnes inchangés')
a=records(old,'_grist_ACLRules');b=records(e,'_grist_ACLRules');changed=[]
assert len(a)==len(b)
for x,y in zip(a,b):
 if x!=y:
  assert x['permissionsText']=='+CR' and y['permissionsText']=='+C' and 'newRec.EMAIL' in x['aclFormula']
  assert {k:v for k,v in x.items() if k!='permissionsText'}=={k:v for k,v in y.items() if k!='permissionsText'}
  changed.append(x['id'])
assert len(changed)==1;checks.append('Une seule règle modifiée : le droit de lecture ne dépend plus de newRec')
for name,pos in [('_grist_Pages','pagePos'),('_grist_TabBar','tabPos')]:
 assert min(records(e,name),key=lambda r:r[pos])['viewRef']==20
 a={r['id']:r for r in records(old,name)};b={r['id']:r for r in records(e,name)};assert a.keys()==b.keys()
 for rid,r in a.items():
  for k,v in r.items():
   if not(r['viewRef']==20 and k==pos):assert v==b[rid][k],(name,rid,k)
 checks.append(name+' : Bienvenue en première position, autres champs conservés')
a={r['id']:r for r in records(old,'_grist_Views_section')};b={r['id']:r for r in records(e,'_grist_Views_section')};assert a.keys()==b.keys()
for rid,r in a.items():
 for k,v in r.items():
  if not(rid==205 and k=='options'):assert objtypes.equal_encoding(v,b[rid][k]),(rid,k)
assert '/moad-20261102-r13/mon-acces.html' in b[205]['options'];checks.append('Seule URL modifiée : nouvel accueil immuable')
assert not [(t['tableId'],r['id'],k) for t in records(e,'_grist_Tables') for r in records(e,t['tableId']) for k,v in r.items() if isinstance(v,objtypes.RaisedException)];checks.append('Aucune erreur de formule')
c=sqlite3.connect('file:'+dst+'?mode=ro',uri=True);assert c.execute('pragma integrity_check').fetchone()[0]=='ok';c.close();checks.append('SQLite intègre')
acl=lambda eng:{n:records(eng,n) for n in ['_grist_ACLRules','_grist_ACLResources']}
f=dict(old_acl=acl(old),acl=acl(e));ref=next(t['id'] for t in records(e,'_grist_Tables') if t['tableId']=='DEMANDES_ACCES');defaults={c['colId']:get_type_default(c['type']) for c in records(e,'_grist_Tables_column') if c['parentId']==ref}
u=dict(Email='regression-signup@example.invalid',Name='Test',Access='editors',UserID=999,UserRef='test',Origin=None,SessionID='test',IsLoggedIn=True,ShareRef=None,LinkKey={})
payload=dict(NOM='TEST',PRENOM='Test',FONCTION=20,UGECAM=1,SITE_AIRMES=4,SITES_RESP_AIRMES=['L'],PROFIL_ACCES='SITE',CONFIRMATION=True,STATUT='À valider',DATE_DEMANDE=1,CONTACT=0)
result=e.apply_user_actions([from_repr(['AddRecord','DEMANDES_ACCES',None,payload])],u);row=None;steps=[]
for action in result.stored:
 aa=get_action_repr(action)
 if aa[1]!='DEMANDES_ACCES':continue
 before=dict(row) if row else None
 if aa[0]=='AddRecord':row={'id':aa[2],**defaults,**aa[3]}
 elif aa[0]=='UpdateRecord':row.update(aa[3])
 else:raise ValueError(aa[0])
 steps.append(dict(action=aa,before=before,after=dict(row)))
final=next(r for r in records(e,'DEMANDES_ACCES') if r['EMAIL']==u['Email'])
f.update(user=u,steps=steps,final={k:objtypes.encode_object(v) for k,v in final.items()})
assert steps[0]['after']['EMAIL']=='' and steps[1]['after']['EMAIL']==u['Email'];checks.append('Séquence réelle reproduite : ajout sans email puis formule email authentifié')
pathlib.Path(out).write_text(json.dumps(f,ensure_ascii=False,default=objtypes.encode_object));print(json.dumps(dict(passed=len(checks),checks=checks,creation_rule=changed),ensure_ascii=False,indent=2))
