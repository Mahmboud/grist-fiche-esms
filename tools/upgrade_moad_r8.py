"""Restore own-contact prefill without exposing hidden tables or other profiles."""
import sys,pathlib,json,sqlite3
from offline_grist import load,records,act,export,objtypes
from migrate_moad_dev import col,acl,update
from predicate_formula import parse_predicate_formula

def main(src,dst):
 e=load(src);before={t:records(e,t) for t in ['CONTACTS','ESMS','Autodiagnostic','Autodiagnostic_Historique','DEMANDES_ACCES']}
 formula='''import json
return json.dumps(dict(id=$id,NOM=$NOM,PRENOM=$PRENOM,EMAIL=$EMAIL,FONCTION=$FONCTION.id,UGECAM=$UGECAM.id,SITE_PRINCIPAL=$SITE_PRINCIPAL.id,SITES_RESP_AIRMES=[r.id for r in ($SITES_RESP_AIRMES or [])],SIEGE=$SIEGE,DNGU=$DNGU),ensure_ascii=False)'''
 col(e,'CONTACTS','MON_PROFIL_JSON','Text',formula)
 own='user.IsLoggedIn is True and rec.id == user.droits_supp.id'
 acl(e,'CONTACTS',[('user.Access == OWNER','+CRUD'),(own,'+R-CUD'),('','-CRUD')],'MON_PROFIL_JSON')
 # The server's user attribute lookup is case-insensitive on email. Matching its
 # contact id also works with differently cased emails and before any request.
 rid=next(r['id'] for r in records(e,'_grist_ACLResources') if r['tableId']=='CONTACTS' and r['colIds']=='*')
 act(e,['AddRecord','_grist_ACLRules',None,dict(resource=rid,aclFormula=own,aclFormulaParsed=parse_predicate_formula(own),permissionsText='+R-CUD')])
 allrules=records(e,'_grist_ACLRules');ordered=[]
 for res in sorted(records(e,'_grist_ACLResources'),key=lambda r:r['id']):
  rr=sorted([r for r in allrules if r['resource']==res['id']],key=lambda r:r['rulePos'])
  if res['tableId']=='CONTACTS':
   rr.sort(key=lambda r:0 if r['aclFormula'] in ['user.Access == OWNER','user.Access in [OWNER]'] else 1 if r['aclFormula']==own else 3 if not r['aclFormula'] else 2)
  ordered+=rr
 act(e,['BulkUpdateRecord','_grist_ACLRules',[r['id'] for r in ordered],{'rulePos':[10000+i*10 for i in range(len(ordered))]}])
 for s in records(e,'_grist_Views_section'):
  old=s.get('options') or ''
  if '/moad-20261029-r7/mon-acces.html' in old:update(e,'_grist_Views_section',s['id'],options=old.replace('/moad-20261029-r7/mon-acces.html','/moad-20261029-r8/mon-acces.html'))
 act(e,['Calculate'])
 for t,rr in before.items():
  after={r['id']:r for r in records(e,t)}
  for r in rr:
   for k,v in r.items():assert objtypes.equal_encoding(after[r['id']][k],v),(t,r['id'],k)
  assert len(after)==len(rr),t
 assert all(not isinstance(r['MON_PROFIL_JSON'],objtypes.RaisedException) for r in records(e,'CONTACTS'))
 export(e,src,dst)
 db=sqlite3.connect(dst);assert db.execute('pragma integrity_check').fetchone()[0]=='ok';db.close()
 print(json.dumps(dict(output=dst,business_data_preserved=True,new_tables=0,widget_sections_changed=[205]),ensure_ascii=False))
if __name__=='__main__':main(*sys.argv[1:])
