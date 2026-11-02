"""Separate creation from visibility; align both Grist default-page orders."""
import sys,pathlib,json
from offline_grist import load,records,export,objtypes
from migrate_moad_dev import update
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main(src,dst):
 if pathlib.Path(src).resolve()==pathlib.Path(dst).resolve():raise ValueError('Une nouvelle copie est obligatoire.')
 e=load(src);before={t['tableId']:records(e,t['tableId']) for t in records(e,'_grist_Tables')}
 resource=next(r['id'] for r in records(e,'_grist_ACLResources') if r['tableId']=='DEMANDES_ACCES' and r['colIds']=='*')
 create=[r for r in records(e,'_grist_ACLRules') if r['resource']==resource and 'newRec.EMAIL == user.Email' in r['aclFormula']]
 assert len(create)==1 and create[0]['permissionsText']=='+CR'
 update(e,'_grist_ACLRules',create[0]['id'],permissionsText='+C')
 own=[r for r in records(e,'_grist_ACLRules') if r['resource']==resource and r['aclFormula']=='user.IsLoggedIn is True and rec.EMAIL == user.Email']
 assert len(own)==1 and own[0]['permissionsText']=='+R-UD'
 assert not any('newRec' in r['aclFormula'] and 'R' in r['permissionsText'] for r in records(e,'_grist_ACLRules') if r['resource']==resource)
 page=next(r for r in records(e,'_grist_Pages') if r['viewRef']==20);tab=next(r for r in records(e,'_grist_TabBar') if r['viewRef']==20)
 update(e,'_grist_Pages',page['id'],pagePos=min(r['pagePos'] for r in records(e,'_grist_Pages'))-1)
 update(e,'_grist_TabBar',tab['id'],tabPos=min(r['tabPos'] for r in records(e,'_grist_TabBar'))-1)
 out=ROOT/'widgets/moad-20261102-r13';out.mkdir(exist_ok=True)
 for name in ['mon-acces.html','moad-api.js','moad-ref-config.js']:(out/name).write_bytes((ROOT/'widgets/moad-20261030-r11'/name).read_bytes())
 s=next(r for r in records(e,'_grist_Views_section') if r['id']==205);old='/widgets/moad-20261030-r11/mon-acces.html';assert old in s['options'];update(e,'_grist_Views_section',205,options=s['options'].replace(old,'/widgets/moad-20261102-r13/mon-acces.html'))
 for t,rr in before.items():
  aa=records(e,t);assert len(rr)==len(aa),t
  assert all(r.keys()==a.keys() and all(objtypes.equal_encoding(v,a[k]) for k,v in r.items()) for r,a in zip(rr,aa)),t
 assert min(records(e,'_grist_Pages'),key=lambda r:r['pagePos'])['viewRef']==20
 assert min(records(e,'_grist_TabBar'),key=lambda r:r['tabPos'])['viewRef']==20
 export(e,src,dst)
 print(json.dumps(dict(output=dst,tables_preserved=len(before),creation_rule=create[0]['id'],read_uses_rec_only=True,default_page=20,legacy_default_page=20),ensure_ascii=False,indent=2))
if __name__=='__main__':main(*sys.argv[1:])
