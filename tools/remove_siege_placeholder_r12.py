"""Remove the empty Siege placeholder in a new immutable widget/copy."""
import pathlib,json,sys
from offline_grist import load,records,export,objtypes
from migrate_moad_dev import update
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main(src,dst):
 if pathlib.Path(src).resolve()==pathlib.Path(dst).resolve():raise ValueError('Une nouvelle copie est obligatoire.')
 old=ROOT/'widgets/moad-20261029-r9';out=ROOT/'widgets/moad-20261102-r12';out.mkdir(exist_ok=True)
 s=(old/'autodiagnostic-questionnaire.html').read_text()
 replacements={
 "function visibleSections(){const base=CONFIG.sections;return (state.isSiege||state.isOwner)?[{title:'Questionnaire Siège UGECAM',questions:[],notes:false,siegeOnly:true,placeholder:true},...base]:base}":"function visibleSections(){return CONFIG.sections}",
 "${s.placeholder?'En préparation':(c.done+'/'+c.total+' · '+c.pct+'%')}":"${c.done+'/'+c.total+' · '+c.pct+'%'}",
 "${sec.placeholder?'Réservé aux professionnels affectés au Siège UGECAM':(sc.done+'/'+sc.total+' · '+sc.pct+'%')}":"${sc.done+'/'+sc.total+' · '+sc.pct+'%'}",
 "${sec.placeholder?'<div class=\"qcard\"><div class=\"qtext\">Volet en préparation</div><div class=\"explain\">Les questions du « Questionnaire Siège UGECAM » seront ajoutées ultérieurement. Ce volet est visible uniquement pour les professionnels ayant une affectation SIEGE.</div></div>':sec.questions.map(qHtml).join('')}":"${sec.questions.map(qHtml).join('')}"
 }
 for a,b in replacements.items():assert s.count(a)==1,a;s=s.replace(a,b)
 assert all(x not in s for x in ['Questionnaire Siège UGECAM','sec.placeholder','s.placeholder','siegeOnly'])
 (out/'autodiagnostic-questionnaire.html').write_text(s)
 for n in ['moad-api.js','moad-ref-config.js']:(out/n).write_bytes((old/n).read_bytes())
 e=load(src);before={t['tableId']:records(e,t['tableId']) for t in records(e,'_grist_Tables')};meta={n:records(e,n) for n in ['_grist_ACLRules','_grist_ACLResources','_grist_Tables','_grist_Tables_column','_grist_Pages','_grist_Views']}
 section=next(r for r in records(e,'_grist_Views_section') if r['id']==153)
 source='https://mahmboud.github.io/grist-fiche-esms/widgets/moad-20261029-r9/autodiagnostic-questionnaire.html';target='https://mahmboud.github.io/grist-fiche-esms/widgets/moad-20261102-r12/autodiagnostic-questionnaire.html'
 assert section['options'].count(source)==1
 update(e,'_grist_Views_section',153,options=section['options'].replace(source,target))
 for t,rr in before.items():
  aa=records(e,t);assert len(rr)==len(aa),t
  assert all(r.keys()==a.keys() and all(objtypes.equal_encoding(v,a[k]) for k,v in r.items()) for r,a in zip(rr,aa)),t
 for n,rr in meta.items():assert rr==records(e,n),n
 export(e,src,dst)
 print(json.dumps(dict(output=dst,tables_preserved=len(before),permissions_preserved=True,section_changed=153,placeholder_removed=True),ensure_ascii=False,indent=2))
if __name__=='__main__':main(*sys.argv[1:])
