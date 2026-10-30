"""Read-only delivery check and optional stdin bridge to the official Grist engine."""
import sys,json,pathlib,sqlite3,hashlib,traceback
from offline_grist import load,act,records,objtypes

def verify(src,dst):
 a=load(src);e=load(dst);checks=[]
 def check(label,ok):
  assert ok,label
  checks.append(label)
 tables=records(a,'_grist_Tables');check('Tables et schéma inchangés',tables==records(e,'_grist_Tables') and records(a,'_grist_Tables_column')==records(e,'_grist_Tables_column'))
 for t in tables:
  name=t['tableId'];before=records(a,name);after=records(e,name)
  check(name+' : toutes les lignes et cellules conservées',len(before)==len(after) and all(x.keys()==y.keys() and all(objtypes.equal_encoding(v,y[k]) for k,v in x.items()) for x,y in zip(before,after)))
 for meta in ['_grist_ACLRules','_grist_ACLResources','_grist_Pages','_grist_Views','_grist_Views_section_field','_grist_DocInfo']:
  check(meta+' inchangé',records(a,meta)==records(e,meta))
 before={r['id']:r for r in records(a,'_grist_Views_section')};after={r['id']:r for r in records(e,'_grist_Views_section')};changed=[]
 check('Aucune section ajoutée ou retirée',before.keys()==after.keys())
 for rid,r in before.items():
  for k,v in r.items():
   if k!='options':assert objtypes.equal_encoding(v,after[rid][k]),(rid,k)
  if r['options']!=after[rid]['options']:changed.append(rid)
 check('Champs des sections hors URL conservés',True)
 check('Seules les quatre URL prévues ont changé',set(changed)=={205,255,40,212} and all('/widgets/moad-20261030-r11/' in after[i]['options'] for i in changed))
 errors=[(t['tableId'],r['id'],k,str(v)) for t in tables for r in records(e,t['tableId']) for k,v in r.items() if isinstance(v,objtypes.RaisedException)]
 check('Aucune erreur de formule',not errors)
 db=sqlite3.connect('file:'+dst+'?mode=ro',uri=True);check('SQLite intègre',db.execute('pragma integrity_check').fetchone()[0]=='ok');db.close()
 counts={t['tableId']:len(records(e,t['tableId'])) for t in tables}
 print(json.dumps(dict(passed=len(checks),tables=len(tables),counts=counts,sections=changed,checks=checks,source_sha256=hashlib.sha256(pathlib.Path(src).read_bytes()).hexdigest()),ensure_ascii=False,indent=2))

def bridge(file):
 e=load(file);original={r['id']:r for r in records(e,'Autodiagnostic')}
 def encode(v):return objtypes.encode_object(v)
 print(json.dumps(dict(ready=True)),flush=True)
 for line in sys.stdin:
  req=json.loads(line)
  try:
   if req['op']=='fetch':
    td=e.fetch_table(req['table'],formulas=True);value=dict(id=list(td.row_ids),**{k:[encode(v) for v in vv] for k,vv in td.columns.items()})
   elif req['op']=='apply':
    out=act(e,*req['actions']);value=dict(retValues=out.retValues)
   elif req['op']=='answers_unchanged':
    rr={r['id']:r for r in records(e,'Autodiagnostic')};value=all(i in rr and all(objtypes.equal_encoding(v,rr[i][k]) for k,v in r.items()) for i,r in original.items())
   elif req['op']=='errors':value=[(t['tableId'],r['id'],k,str(v)) for t in records(e,'_grist_Tables') for r in records(e,t['tableId']) for k,v in r.items() if isinstance(v,objtypes.RaisedException)]
   else:raise ValueError('Unknown operation')
   print(json.dumps(dict(id=req['id'],value=value),ensure_ascii=False,default=encode),flush=True)
  except Exception as err:print(json.dumps(dict(id=req['id'],error=str(err))),flush=True)
if __name__=='__main__':
 if sys.argv[1]=='--bridge':bridge(sys.argv[2])
 else:verify(*sys.argv[1:])
