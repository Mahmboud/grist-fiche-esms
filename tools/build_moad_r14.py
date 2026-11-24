"""Copy-only signup repair. Keep business cells byte-for-byte; embed minimal selector fallback."""
import sqlite3,json,pathlib,shutil,sys,hashlib
from predicate_formula import parse_predicate_formula
src,dst=sys.argv[1:];assert pathlib.Path(src).resolve()!=pathlib.Path(dst).resolve()
root=pathlib.Path(__file__).resolve().parents[1];bundle=root/'widgets/moad-20261124-r14'
for n in ['mon-acces.html','moad-api.js','moad-ref-config.js']:(bundle/n).write_bytes((root/'widgets/moad-20261102-r13'/n).read_bytes())
p=bundle/'mon-acces.html';s=p.read_text()
old="selectPersonal();show();grist.onRecords?"
new="""if(!S.u.length||!S.s.length){const backup=(await grist.getOptions?.())?.inscriptionReferentiel;if(backup?.version===1){if(!S.u.length&&Array.isArray(backup.ugecam))S.u=backup.ugecam.filter(r=>Number.isInteger(r.id)&&typeof r.UGECAM==='string');if(!S.s.length&&Array.isArray(backup.sites))S.s=backup.sites.filter(r=>Number.isInteger(r.id)&&Number.isInteger(r.UGECAM)&&typeof r.NOM==='string')}}if(!S.u.length||!S.s.length)throw Error('Le référentiel d’inscription est indisponible. Rechargez la page ou contactez l’administrateur MOAD.');selectPersonal();show();grist.onRecords?"""
assert old in s;s=s.replace(old,new);p.write_text(s)
shutil.copy2(src,dst);c=sqlite3.connect(dst);c.row_factory=sqlite3.Row
assert c.execute('select permissionsText from _grist_ACLRules where id=274').fetchone()[0]=='+CR'
c.execute("update _grist_ACLRules set permissionsText='+C', aclFormulaParsed=? where id=274",(json.dumps(parse_predicate_formula(c.execute("select aclFormula from _grist_ACLRules where id=274").fetchone()[0]),ensure_ascii=False),))
formula="user.Access in [OWNER, EDITOR, VIEWER] and user.Email != '' and rec.id == 1 and rec.STATUT == 'Référentiel inscription'"
c.execute('update _grist_ACLRules set aclFormula=?,aclFormulaParsed=?,rulePos=? where id=291',(formula,json.dumps(parse_predicate_formula(formula),ensure_ascii=False),223.7))
for table,pos in [('_grist_Pages','pagePos'),('_grist_TabBar','tabPos')]:c.execute(f'update {table} set {pos}=(select min({pos})-1 from {table}) where viewRef=20')
opts=json.loads(c.execute('select options from _grist_Views_section where id=205').fetchone()[0]);view=opts['customView'];view=json.loads(view) if isinstance(view,str) else view
view['url']='https://mahmboud.github.io/grist-fiche-esms/widgets/moad-20261124-r14/mon-acces.html'
backup={'version':1,'ugecam':[dict(r) for r in c.execute('select id,UGECAM from GristHidden_UGECAM order by manualSort,id')],'sites':[dict(r) for r in c.execute('select id,NOM,UGECAM from GristHidden_SITES order by manualSort,id')]}
view['widgetOptions']={**(view.get('widgetOptions') or {}),'inscriptionReferentiel':backup};opts['customView']=json.dumps(view,ensure_ascii=False);c.execute('update _grist_Views_section set options=? where id=205',(json.dumps(opts,ensure_ascii=False),));c.commit()
a=sqlite3.connect(src)
tables=[r[0] for r in a.execute("select name from sqlite_master where type='table' and name not like '_grist%' ")]
for t in tables:assert a.execute('select * from "'+t+'" order by id').fetchall()==[tuple(r) for r in c.execute('select * from "'+t+'" order by id')],t
assert c.execute('pragma integrity_check').fetchone()[0]=='ok'
report={'business_tables_preserved':len(tables),'ugecam':len(backup['ugecam']),'sites':len(backup['sites']),'fallback_fields':['id','UGECAM','NOM'],'source_sha256':hashlib.sha256(pathlib.Path(src).read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(pathlib.Path(dst).read_bytes()).hexdigest()}
pathlib.Path(dst).with_suffix('.verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
