"""Add two multi-valued site software columns, without changing existing data/ACLs."""
import sys,pathlib,json
from offline_grist import load,records,act,export,objtypes
src,dst=sys.argv[1:];assert pathlib.Path(src).resolve()!=pathlib.Path(dst).resolve();e=load(src)
def rr(t):return records(e,t)
before={r['tableId']:rr(r['tableId']) for r in rr('_grist_Tables')};meta={t:rr(t) for t in ['_grist_Tables','_grist_ACLRules','_grist_ACLResources','_grist_Views','_grist_Pages','_grist_TabBar']};oldcols={r['id']:r for r in rr('_grist_Tables_column')}
newcols=[('DUI_DEPLOYE','DUI déployé'),('AUTRES_LOGICIELS_METIER','Autres logiciels métier')]
aa=[]
for field,label in newcols:
 info=dict(type='ChoiceList',isFormula=False,formula='',label=label,widgetOptions=json.dumps({'choices':['Airmes'] if field=='DUI_DEPLOYE' else []},ensure_ascii=False))
 if field=='DUI_DEPLOYE':info.update(formula="['Airmes'] if $UGECAM and $UGECAM.id not in (12, 13) else []",recalcWhen=0)
 aa.append(['AddColumn','GristHidden_SITES',field,info])
act(e,*aa)
# Apply the requested initial value to existing sites; the editable default also covers new sites.
assert next(r for r in rr('GristHidden_UGECAM') if r['id']==12)['UGECAM']=='UGECAM PACA-C'
assert next(r for r in rr('GristHidden_UGECAM') if r['id']==13)['UGECAM']=='UGECAM Alsace'
sites=rr('GristHidden_SITES');act(e,['BulkUpdateRecord','GristHidden_SITES',[r['id'] for r in sites],{'DUI_DEPLOYE':[['L'] if r['UGECAM'] in (12,13) else ['L','Airmes'] for r in sites]}])
projection=next(c for c in rr('_grist_Tables_column') if c['colId']=='PORTAIL_SITES_JSON');old=projection['formula'];assert 'DUI_DEPLOYE' not in old
# Use an exact replacement with the original closing parenthesis retained.
formula=old.replace('DIRECTION_CONTACTS_JSON=r.DIRECTION_CONTACTS_JSON','DIRECTION_CONTACTS_JSON=r.DIRECTION_CONTACTS_JSON,DUI_DEPLOYE=list(r.DUI_DEPLOYE or []),AUTRES_LOGICIELS_METIER=list(r.AUTRES_LOGICIELS_METIER or [])')
act(e,['UpdateRecord','_grist_Tables_column',projection['id'],{'formula':formula}])
urls={40:'sites-esms.html',212:'administration-sauvegardes.html'}
for sid,name in urls.items():
 s=next(s for s in rr('_grist_Views_section') if s['id']==sid);o=json.loads(s['options']);v=json.loads(o['customView']);assert '/moad-20261030-r11/' in v['url'];v['url']='https://mahmboud.github.io/grist-fiche-esms/widgets/moad-20261124-r17/'+name;o['customView']=json.dumps(v,ensure_ascii=False);act(e,['UpdateRecord','_grist_Views_section',sid,{'options':json.dumps(o,ensure_ascii=False)}])
for t,old in meta.items():assert old==rr(t),t
for t,old in before.items():
 now={r['id']:r for r in rr(t)};assert len(now)==len(old),t
 for r in old:
  for k,v in r.items():assert objtypes.equal_encoding(v,now[r['id']][k]),(t,r['id'],k)
for i,r in oldcols.items():
 now=next(c for c in rr('_grist_Tables_column') if c['id']==i)
 for k,v in r.items():
  if i==projection['id'] and k=='formula':continue
  assert objtypes.equal_encoding(v,now[k]),('schema',i,k)
for t in before:
 assert not [(r['id'],k) for r in rr(t) for k,v in r.items() if isinstance(v,objtypes.RaisedException)],t
assert all(list(s['DUI_DEPLOYE'] or [])==([] if s['UGECAM'] in (12,13) else ['Airmes']) and not s['AUTRES_LOGICIELS_METIER'] for s in rr('GristHidden_SITES'))
export(e,src,dst)
report={'source':pathlib.Path(src).name,'existing_tables_preserved':len(before),'new_columns':newcols,'site_count':len(rr('GristHidden_SITES')),'esms_count':len(rr('ESMS')),'autodiag_count':len(rr('Autodiagnostic')),'changed_widget_sections':urls,'acl_preserved':True,'airmes_defaults':sum(bool(s['DUI_DEPLOYE']) for s in rr('GristHidden_SITES')),'excluded_sites':sum(s['UGECAM'] in (12,13) for s in rr('GristHidden_SITES'))};pathlib.Path(dst).with_suffix('.verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
# Private fixture: public directory + metadata only, no real contacts.
fixture={t:rr(t) for t in ['GristHidden_SITES','GristHidden_UGECAM','ESMS','FINESS_CATALOGUE','FINESS_ACCES_PAGE','DEMANDES_ACCES','ADMIN_OUTILS','_grist_Tables','_grist_Tables_column']};fixture['CONTACTS']=[];pathlib.Path(dst).with_suffix('.ui-fixture.json').write_text(json.dumps(fixture,ensure_ascii=False,default=objtypes.encode_object))
# Verify full projection with temporary software, not exported.
act(e,['UpdateRecord','GristHidden_SITES',4,{'DUI_DEPLOYE':['L','Airmes','DUI test'],'AUTRES_LOGICIELS_METIER':['L','Logiciel test','Outil complémentaire']}],['AddRecord','DEMANDES_ACCES',None,{'EMAIL':'regression-r17@example.invalid','STATUT':'Validé'}])
row=next(r for r in rr('DEMANDES_ACCES') if r['EMAIL']=='regression-r17@example.invalid');site=next(r for r in json.loads(row['PORTAIL_SITES_JSON']) if r['id']==4);assert site['DUI_DEPLOYE']==['Airmes','DUI test'] and site['AUTRES_LOGICIELS_METIER']==['Logiciel test','Outil complémentaire'];seed=next(r for r in rr('DEMANDES_ACCES') if r['id']==1);assert 'DUI_DEPLOYE' not in json.loads(seed['PORTAIL_SITES_JSON'])[0];print('Projection validée : toutes les valeurs, sans élargir les sélecteurs avant inscription. Aucun jeu de test exporté.')

for ug,expected in [(1,['Airmes']),(12,[]),(13,[])]:
 rid=act(e,['AddRecord','GristHidden_SITES',None,{'NOM':'TEST NON EXPORTÉ','UGECAM':ug}]).retValues[0];assert list(next(s for s in rr('GristHidden_SITES') if s['id']==rid)['DUI_DEPLOYE'] or [])==expected
print('Valeur par défaut des nouveaux sites : Airmes, sauf PACA-C et Alsace ; tests non exportés.')
