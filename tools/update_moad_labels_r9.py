"""New immutable Autodiag labels; no answer/permission changes."""
import pathlib,json,sys
from offline_grist import load,records,act,export,objtypes
from migrate_moad_dev import update
ROOT=pathlib.Path(__file__).resolve().parents[1]
LABELS={'Statistiques et rapports de don':'Statistiques et rapports de données','Attentes sur les évol fonc':"Attentes sur les évolutions fonctionnelles d'Airmes"}
def main(src,dst):
 base=ROOT/'widgets/moad-20261029-r7';out=ROOT/'widgets/moad-20261029-r9';out.mkdir(exist_ok=True)
 for name in ['moad-api.js','moad-ref-config.js','autodiagnostic-questionnaire.html','autodiagnostic-synthese.html','administration-exports.html']:
  text=(base/name).read_text()
  if name=='moad-ref-config.js':
   old=json.loads(text[text.index('({')+1:text.rindex('})')+1]);new=json.loads(json.dumps(old))
   for q in new['questions']:q[1]=LABELS.get(q[1],q[1])
   assert len(new['questions'])==116
   for a,b in zip(old['questions'],new['questions']):assert a[:1]+a[2:]==b[:1]+b[2:]
   text='window.loadMoadRefConfig=async()=>('+json.dumps(new,ensure_ascii=False)+');\n'
  (out/name).write_text(text)
 e=load(src);before={t['tableId']:records(e,t['tableId']) for t in records(e,'_grist_Tables')}
 changed=[]
 for r in records(e,'AUTODIAG_REFERENTIEL_QUESTIONS'):
  if r['VOLET'] in LABELS:update(e,'AUTODIAG_REFERENTIEL_QUESTIONS',r['id'],VOLET=LABELS[r['VOLET']]);changed.append(r['id'])
 for s in records(e,'_grist_Views_section'):
  old=s.get('options') or '';new=old
  for name in ['autodiagnostic-questionnaire.html','autodiagnostic-synthese.html','administration-exports.html']:new=new.replace('/moad-20261029-r7/'+name,'/moad-20261029-r9/'+name)
  if new!=old:update(e,'_grist_Views_section',s['id'],options=new)
 for t,rr in before.items():
  if t=='AUTODIAG_REFERENTIEL_QUESTIONS':continue
  after=records(e,t);assert len(after)==len(rr),t
  for a,b in zip(rr,after):
   for k,v in a.items():assert objtypes.equal_encoding(v,b[k]),(t,a['id'],k)
 export(e,src,dst)
 print(json.dumps(dict(labels=LABELS,questions_updated=len(changed),questions=116,business_data_preserved=True,output=dst),ensure_ascii=False,indent=2))
if __name__=='__main__':main(*sys.argv[1:])
