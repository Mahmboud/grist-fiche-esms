"""Add HAS results page using existing public-data storage and validated-directory gate."""
import sys,json,pathlib,hashlib,collections,gzip,base64
from offline_grist import load,records,act,export,objtypes
src,dst,extractfile=sys.argv[1:];assert pathlib.Path(src).resolve()!=pathlib.Path(dst).resolve();e=load(src)
def rr(t):return records(e,t)
before={t['tableId']:rr(t['tableId']) for t in rr('_grist_Tables')};meta={t:rr(t) for t in ['_grist_Tables','_grist_Tables_column','_grist_ACLRules','_grist_ACLResources']};oldviews={r['id']:r for r in rr('_grist_Views')};oldsections={r['id']:r for r in rr('_grist_Views_section')};oldpages={r['id']:r for r in rr('_grist_Pages')};oldtabs={r['id']:r for r in rr('_grist_TabBar')};pack=json.loads(pathlib.Path(extractfile).read_text());info=pack['info'];groups=pack['groups'];cat={r['FINESS']:r for r in before['FINESS_CATALOGUE']};oldfacts={r['CLE']:r for r in before['DONNEES_PUBLIQUES']};aa=[];undo=[];nextid=max(r['id'] for r in before['DONNEES_PUBLIQUES'])+1
for code,evs in groups.items():
 c=cat[code];assert evs and code==c['FINESS'];values=dict(CLE='has-essms:'+code,SOURCE='has-essms',FINESS=code,FINESS_JURIDIQUE=c['FINESS_JURIDIQUE'],UGECAM=c['UGECAM'],DONNEES_JSON=json.dumps(dict(evaluations=evs,lien='https://www.has-sante.fr/fiche-essms/'+code),ensure_ascii=False,allow_nan=False),RESUME='Évaluation clôturée le '+str(evs[0].get('eval_date_cloture_tech') or '')[:10]+' · niveau '+str(evs[0].get('indice_qualite') or 'non renseigné'),DATE_SOURCE=info['sourceDate'],SOURCE_URL=info['sourceUrl'],DATE_EXTRACTION=info['extractedAt'],PRESENT_SOURCE=True)
 old=oldfacts.get(values['CLE'])
 if old:
  aa.append(['UpdateRecord','DONNEES_PUBLIQUES',old['id'],values]);undo.append(['UpdateRecord','DONNEES_PUBLIQUES',old['id'],{k:objtypes.encode_object(old[k]) for k in values}])
 else:aa.append(['AddRecord','DONNEES_PUBLIQUES',nextid,values]);undo.append(['RemoveRecord','DONNEES_PUBLIQUES',nextid]);nextid+=1
for old in before['DONNEES_PUBLIQUES']:
 if old['SOURCE']=='has-essms' and old['FINESS'] not in groups:aa.append(['UpdateRecord','DONNEES_PUBLIQUES',old['id'],{'PRESENT_SOURCE':False,'DATE_EXTRACTION':info['extractedAt']}]);undo.append(['UpdateRecord','DONNEES_PUBLIQUES',old['id'],{'PRESENT_SOURCE':old['PRESENT_SOURCE'],'DATE_EXTRACTION':old['DATE_EXTRACTION']}])
source=next(s for s in before['SOURCES_PUBLIQUES'] if s['SOURCE']=='has-essms');values=dict(STATUT='ok',DATE_SOURCE=info['sourceDate'],DATE_VERIFICATION=info['extractedAt'],DATE_EXTRACTION=info['extractedAt'],URL=info['sourceUrl'],SHA256=info['sha256'],NB_FINESS=len(groups),AVERTISSEMENT='Cotations du rapport et échelle qualité jointes par eval_code. Évaluations multi-ESSMS signalées.');aa.append(['UpdateRecord','SOURCES_PUBLIQUES',source['id'],values]);undo.append(['UpdateRecord','SOURCES_PUBLIQUES',source['id'],{k:source[k] for k in values}]);aa.append(['AddRecord','ACTUALISATIONS_PUBLIQUES',None,dict(DATE=info['extractedAt'],SNAPSHOT='has:'+info['sha256'],STATUT='Terminé',BILAN_JSON=json.dumps(dict(source='has-essms',finess=len(groups),ressources=info['resourceUrls']),ensure_ascii=False),RESTAURATION_JSON=json.dumps(undo[::-1],ensure_ascii=False))]);act(e,*aa)
tref=next(t['id'] for t in rr('_grist_Tables') if t['tableId']=='FINESS_ACCES_PAGE');created=act(e,['CreateViewSection',tref,0,'custom',None,None]).retValues[0];vid,sid=created['viewRef'],created['sectionRef'];name='Résultats évaluation HAS';options={'customView':json.dumps(dict(mode='url',url='https://mahmboud.github.io/grist-fiche-esms/widgets/moad-20261125-r18/has-results.html',access='full',renderAfterReady=False,columnsMapping=None))}
act(e,['UpdateRecord','_grist_Views',vid,{'name':name,'layoutSpec':json.dumps({'leaf':sid,'collapsed':[]})}],['UpdateRecord','_grist_Views_section',sid,{'title':name,'options':json.dumps(options)}]);page=next(p for p in rr('_grist_Pages') if p['viewRef']==vid);act(e,['UpdateRecord','_grist_Pages',page['id'],{'pagePos':4.75,'indentation':0}]);tab=next(t for t in rr('_grist_TabBar') if t['viewRef']==vid);act(e,['UpdateRecord','_grist_TabBar',tab['id'],{'tabPos':4.75}])
# New immutable FINESS URL uses a planner that preserves newer HAS imports.
section=next(s for s in rr('_grist_Views_section') if s['id']==255);o=json.loads(section['options']);v=json.loads(o['customView']);v['url']='https://mahmboud.github.io/grist-fiche-esms/widgets/moad-20261125-r18/liste-finess.html';o['customView']=json.dumps(v);act(e,['UpdateRecord','_grist_Views_section',255,{'options':json.dumps(o)}])
for t,old in meta.items():assert old==rr(t),t
for t,index in [('_grist_Views',oldviews),('_grist_Views_section',oldsections),('_grist_Pages',oldpages),('_grist_TabBar',oldtabs)]:
 now={r['id']:r for r in rr(t)}
 for i,r in index.items():
  if t=='_grist_Views_section' and i==255:
   assert {k:v for k,v in r.items() if k!='options'}=={k:v for k,v in now[i].items() if k!='options'}
  else:assert r==now[i],(t,i)
for t,old in before.items():
 now={r['id']:r for r in rr(t)};tr=next(r['id'] for r in rr('_grist_Tables') if r['tableId']==t);physical=[c['colId'] for c in rr('_grist_Tables_column') if c['parentId']==tr and not c['isFormula']]
 for r in old:
  if t=='DONNEES_PUBLIQUES' and r['SOURCE']=='has-essms' or t=='SOURCES_PUBLIQUES' and r['SOURCE']=='has-essms':continue
  for k in physical:assert objtypes.equal_encoding(r[k],now[r['id']][k]),(t,r['id'],k)
 if t not in ['DONNEES_PUBLIQUES','ACTUALISATIONS_PUBLIQUES']:assert len(now)==len(old),t
for t in ['CONTACTS','Autodiagnostic','Autodiagnostic_Historique','GristHidden_SITES']:
 now={r['id']:r for r in rr(t)}
 for r in before[t]:
  for k,v in r.items():assert objtypes.equal_encoding(v,now[r['id']][k]),(t,r['id'],k)
for t in before:assert not [(r['id'],k) for r in rr(t) for k,v in r.items() if isinstance(v,objtypes.RaisedException)],t
projection=json.loads(gzip.decompress(base64.b64decode(rr('FINESS_ACCES_PAGE')[0]['ANNUAIRE_GZIP'])));assert len([f for f in projection['DONNEES_PUBLIQUES'] if f['SOURCE']=='has-essms' and f['PRESENT_SOURCE']])==len(groups)
assert next(s for s in rr('_grist_Views_section') if s['id']==sid)['tableRef']==next(s for s in rr('_grist_Views_section') if s['id']==255)['tableRef'];assert min(rr('_grist_Pages'),key=lambda r:r['pagePos'])['viewRef']==20
export(e,src,dst)
fixture={t:rr(t) for t in ['FINESS_CATALOGUE','DONNEES_PUBLIQUES','GristHidden_SITES','GristHidden_UGECAM','ESMS','FINESS_ACCES_PAGE','DEMANDES_ACCES','SOURCES_PUBLIQUES','ACTUALISATIONS_PUBLIQUES']};pathlib.Path(dst).with_suffix('.ui-fixture.json').write_text(json.dumps(fixture,ensure_ascii=False,default=objtypes.encode_object));report=dict(source=pathlib.Path(src).name,has_finess=len(groups),source_date=info['sourceDate'],evaluation_count=len({r['eval_code'] for rr in groups.values() for r in rr}),page_view=vid,page_section=sid,same_gate_as_finess=True,acl_unchanged=True,old_widget_files_unchanged=True,autodiag_preserved=len(before['Autodiagnostic']),business_tables=len(before),no_extra_table=True);pathlib.Path(dst).with_suffix('.verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
