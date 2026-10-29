import sys,json,pathlib
from offline_grist import load,records,act,export,objtypes
from migrate_moad_dev import update
from predicate_formula import parse_predicate_formula

def main(src,dst):
 e=load(src);before={t['tableId']:records(e,t['tableId']) for t in records(e,'_grist_Tables')}
 # Welcome must precede even the owner-only Admin page. Otherwise a restricted
 # client can start on Admin's censored widgets while selecting a fallback label.
 update(e,'_grist_Pages',20,pagePos=0.1)
 update(e,'_grist_Pages',21,pagePos=7)
 update(e,'_grist_Views',20,name='🔐 Bienvenue / Mon accès',layoutSpec=json.dumps(dict(leaf=205,collapsed=[])))
 section=next(r for r in records(e,'_grist_Views_section') if r['id']==205)
 update(e,'_grist_Views_section',205,options=section['options'].replace('/moad-20261029-r8/mon-acces.html','/moad-20261029-r10/mon-acces.html'))
 # UI status and server permission agree: a validated user cannot submit again.
 for r in records(e,'_grist_ACLRules'):
  if 'newRec.EMAIL == user.Email' in r['aclFormula']:
   expr=r['aclFormula']+" and user.demande_acces.STATUT != 'Validé'"
   update(e,'_grist_ACLRules',r['id'],aclFormula=expr,aclFormulaParsed=parse_predicate_formula(expr))
 for t,rr in before.items():
  after=records(e,t);assert len(after)==len(rr),t
  for a,b in zip(rr,after):
   for k,v in a.items():assert objtypes.equal_encoding(v,b[k]),(t,a['id'],k)
 assert min(records(e,'_grist_Pages'),key=lambda r:r['pagePos'])['viewRef']==20
 export(e,src,dst)
 print(json.dumps(dict(output=dst,default_page='Bienvenue / Mon accès',business_data_preserved=True,source_widgets_unchanged=True),ensure_ascii=False))
if __name__=='__main__':main(*sys.argv[1:])
