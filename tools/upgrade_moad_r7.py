"""Owner-only source tables; safe request-scoped projections for widgets."""
import pathlib,json,sys,sqlite3
from offline_grist import load,act,records,export,objtypes
from migrate_moad_dev import col,bulk,update,owner_only
from predicate_formula import parse_predicate_formula
BASE='https://mahmboud.github.io/grist-fiche-esms/widgets/moad-20261029-r7/'
def rule(e,res,expr,perm):
 act(e,['AddRecord','_grist_ACLRules',None,dict(resource=res,aclFormula=expr,aclFormulaParsed=parse_predicate_formula(expr) if expr else '',permissionsText=perm)])
def replace(e,t,expr,columns='*'):
 rr=[r for r in records(e,'_grist_ACLResources') if r['tableId']==t and r['colIds']==columns]
 if rr:
  rid=rr[0]['id'];ids=[r['id'] for r in records(e,'_grist_ACLRules') if r['resource']==rid]
  if ids:act(e,['BulkRemoveRecord','_grist_ACLRules',ids])
 else:rid=act(e,['AddRecord','_grist_ACLResources',None,dict(tableId=t,colIds=columns)]).retValues[0]
 rule(e,rid,'user.Access == OWNER','+CRUD');rule(e,rid,expr,'+R-CUD');rule(e,rid,'','-CRUD')
def main(src,dst,fixture):
 e=load(src);before={t:records(e,t) for t in ['CONTACTS','ESMS','Autodiagnostic','Autodiagnostic_Historique']}
 valid="user.IsLoggedIn is True and user.demande_acces.STATUT == 'Validé'"
 # A single non-personal bootstrap row contains only the inscription selectors.
 # Personal rows remain own-email readable. Source tables are truly owner-only.
 sid=max((r['id'] for r in records(e,'DEMANDES_ACCES')),default=0)+1
 bulk(e,'DEMANDES_ACCES',[dict(id=sid,STATUT='Référentiel inscription',EMAIL='',NOM='',PRENOM='')])
 sites="""import json
full = $STATUT == 'Validé'
return json.dumps([dict(id=r.id,NOM=r.NOM,UGECAM=r.UGECAM.id,**(dict(LOCALISATIONS_JSON=r.LOCALISATIONS_JSON,DIRECTION_NOMS=r.DIRECTION_NOMS,DIRECTION_CONTACTS_JSON=r.DIRECTION_CONTACTS_JSON) if full else {})) for r in GristHidden_SITES.all],ensure_ascii=False)"""
 ugs="""import json
full = $STATUT == 'Validé'
return json.dumps([dict(id=r.id,UGECAM=r.UGECAM,**(dict(FINESS_Juridique=r.FINESS_Juridique,FINESS_JURIDIQUES=list(r.FINESS_JURIDIQUES or []),DG_NOMS=r.DG_NOMS,RESP_MS_NOMS=r.RESP_MS_NOMS,RSI_NOMS=r.RSI_NOMS,QUALITE_NOMS=r.QUALITE_NOMS) if full else {})) for r in GristHidden_UGECAM.all],ensure_ascii=False)"""
 profile="""import json
p = GristHidden_PROFIL_SESSION.lookupOne(EMAIL=$EMAIL) if $EMAIL else None
return json.dumps([dict(id=p.id,CONTACT=p.CONTACT.id,EMAIL=p.EMAIL,SIEGE=p.SIEGE,DNGU=p.DNGU)] if p else [],ensure_ascii=False)"""
 for name,formula in [('PORTAIL_SITES_JSON',sites),('PORTAIL_UGECAM_JSON',ugs),('PORTAIL_PROFIL_JSON',profile)]:col(e,'DEMANDES_ACCES',name,'Text',formula)
 for t in ['GristHidden_SITES','GristHidden_UGECAM','GristHidden_PROFIL_SESSION']:owner_only(e,t)
 rid=next(r['id'] for r in records(e,'_grist_ACLResources') if r['tableId']=='DEMANDES_ACCES' and r['colIds']=='*')
 rule(e,rid,f'user.IsLoggedIn is True and rec.id == {sid}','+R-CUD')
 # One shared projection on the existing FINESS page avoids copying national
 # extracts into every professional's request. Physical source tables are denied.
 directory=['ESMS','FINESS_CATALOGUE','DONNEES_PUBLIQUES','ARBO_ESMS_REFERENCES','ARBORESCENCE_AIRMES']
 expressions=[]
 for t in directory:
  ref=next(r['id'] for r in records(e,'_grist_Tables') if r['tableId']==t)
  cc=[c for c in records(e,'_grist_Tables_column') if c['parentId']==ref and c['colId'] not in ['CONTACTS_PERIMETRE','CONTACTS_DROITS'] and not c['colId'].startswith('gristHelper_')]
  # Grist values are encoded exactly as the API expects (RefList/ChoiceList L).
  def expr(c):
   k=c['colId'];v='r.'+k;typ=c['type']
   if typ.startswith('Ref:'):v+=' .id'
   elif typ.startswith('RefList:'):v="['L']+[x.id for x in ("+v+" or [])]"
   elif typ=='ChoiceList':v="['L']+list("+v+" or [])"
   elif typ.startswith(('DateTime:','Date')):v='cell('+v+')'
   else:v='objtypes.encode_object('+v+')'
   return k+'='+v
  expressions.append(repr(t)+': [dict(id=r.id,'+','.join(expr(c) for c in cc)+') for r in '+t+'.all]')
 formula='import json\nimport gzip\nimport base64\nimport objtypes\nimport datetime\nimport calendar\ndef cell(v):\n  if isinstance(v, datetime.datetime): return v.timestamp()\n  if isinstance(v, datetime.date): return calendar.timegm(v.timetuple())\n  return objtypes.encode_object(v)\nreturn base64.b64encode(gzip.compress(json.dumps({'+','.join(expressions)+'},ensure_ascii=False).encode("utf-8"),mtime=0)).decode("ascii")'
 col(e,'FINESS_ACCES_PAGE','ANNUAIRE_GZIP','Text',formula)
 replace(e,'FINESS_ACCES_PAGE',valid)
 for t in directory:owner_only(e,t)
 gate=next(r['id'] for r in records(e,'_grist_Tables') if r['tableId']=='FINESS_ACCES_PAGE')
 for section in records(e,'_grist_Views_section'):
  if section['id'] in [37,40]:
   fields=[r['id'] for r in records(e,'_grist_Views_section_field') if r['parentId']==section['id']]
   if fields:act(e,['BulkRemoveRecord','_grist_Views_section_field',fields])
   update(e,'_grist_Views_section',section['id'],tableRef=gate)
 # Annuaire droit unchanged, but contacts shown on site/ESMS cards are projected
 # dynamically by the engine, independent of the viewer's contact table access.
 # Autodiag and its history ACL are deliberately unchanged, including all scopes.
 # Keep global positions unique and bootstrap before the final deny.
 allrules=records(e,'_grist_ACLRules');ordered=[]
 for res in sorted(records(e,'_grist_ACLResources'),key=lambda r:r['id']):
  rr=sorted([r for r in allrules if r['resource']==res['id']],key=lambda r:r['rulePos'])
  if res['tableId'] not in ['*','*SPECIAL']:rr.sort(key=lambda r:0 if r['aclFormula'] in ['user.Access == OWNER','user.Access in [OWNER]'] else 3 if not r['aclFormula'] else 1 if 'newRec' in r['aclFormula'] else 2)
  ordered+=rr
 act(e,['BulkUpdateRecord','_grist_ACLRules',[r['id'] for r in ordered],{'rulePos':[10000+i*10 for i in range(len(ordered))]}])
 for section in records(e,'_grist_Views_section'):
  old=section.get('options') or '';new=old.replace('/moad-20261029-r6/','/moad-20261029-r7/')
  if new!=old:update(e,'_grist_Views_section',section['id'],options=new)
 act(e,['Calculate'])
 tables={r['tableId']:records(e,r['tableId']) for r in records(e,'_grist_Tables')}
 for t,rr in before.items():
  assert [[objtypes.encode_object(v) for v in r.values()] for r in rr]==[[objtypes.encode_object(v) for v in r.values()] for r in tables[t]],t
 for t,rr in tables.items():
  errors=[(r['id'],k,str(v)) for r in rr for k,v in r.items() if isinstance(v,objtypes.RaisedException)]
  assert not errors,(t,errors[:3])
 export(e,src,dst)
 db=sqlite3.connect(dst);assert db.execute('pragma integrity_check').fetchone()[0]=='ok';db.close()
 out=dict(tables=tables,acl=dict(resources=records(e,'_grist_ACLResources'),rules=records(e,'_grist_ACLRules')),metadata={t:records(e,t) for t in ['_grist_Tables','_grist_Views_section','_grist_Tables_column']},bootstrap=sid)
 pathlib.Path(fixture).write_text(json.dumps(out,ensure_ascii=False,default=objtypes.encode_object));print(json.dumps(dict(output=dst,bootstrap=sid,business_data_preserved=True)))
if __name__=='__main__':main(*sys.argv[1:])
