import sys,json,pathlib
from offline_grist import load,records,act,objtypes
src,dst,out=sys.argv[1:];e=load(dst);old=load(src);checks=[]
for t in ['CONTACTS','ESMS','Autodiagnostic','Autodiagnostic_Historique','DEMANDES_ACCES']:
 after={r['id']:r for r in records(e,t)}
 for r in records(old,t):
  for k,v in r.items():assert objtypes.equal_encoding(v,after[r['id']][k]),(t,r['id'],k)
 checks.append('Cellules préexistantes inchangées : '+t)
# Compare permissions by resource semantics; global positions are renumbered.
def permissions(eng,table):
 res={r['id']:r for r in records(eng,'_grist_ACLResources') if r['tableId']==table}
 return sorted((res[r['resource']]['colIds'],r['aclFormula'],r['permissionsText']) for r in records(eng,'_grist_ACLRules') if r['resource'] in res)
for t in ['Autodiagnostic','Autodiagnostic_Historique','GristHidden_SITES','GristHidden_UGECAM','GristHidden_PROFIL_SESSION']:
 assert permissions(e,t)==permissions(old,t);checks.append('Droits inchangés : '+t)
assert len(records(e,'_grist_Tables'))==len(records(old,'_grist_Tables'));checks.append('Aucune nouvelle table')
act(e,['AddRecord','CONTACTS',1,dict(EMAIL='Inscription@Example.Invalid',NOM='PRÉREMPLI',PRENOM='Alice',FONCTION=20,UGECAM=1,SITE_PRINCIPAL=4,SITES_RESP_AIRMES=['L',74],SIEGE=False,DNGU=False)])
contact=next(r for r in records(e,'CONTACTS') if r['id']==1);personal=json.loads(contact['MON_PROFIL_JSON']);assert personal['NOM']=='PRÉREMPLI' and personal['SITE_PRINCIPAL']==4 and personal['SITES_RESP_AIRMES']==[74];checks.append('Projection personnelle complète avant toute demande, sans profil technique')
f=dict(tables={r['tableId']:records(e,r['tableId']) for r in records(e,'_grist_Tables')},acl=dict(resources=records(e,'_grist_ACLResources'),rules=records(e,'_grist_ACLRules')))
pathlib.Path(out).write_text(json.dumps(f,ensure_ascii=False,default=objtypes.encode_object))
import useractions
identity={'Email':'inscription@example.invalid','Name':'Alice','Access':'editors','UserID':999,'UserRef':'test','Origin':None,'SessionID':'test','IsLoggedIn':True,'ShareRef':None,'LinkKey':{}}
e.apply_user_actions([useractions.from_repr(['AddRecord','DEMANDES_ACCES',None,dict(NOM='PRÉREMPLI',PRENOM='Alice',STATUT='À valider',CONTACT=0,CONFIRMATION=True,PROFIL_ACCES='SITE')])],identity)
request=next(r for r in records(e,'DEMANDES_ACCES') if r['STATUT']=='À valider');assert request['EMAIL']==identity['Email'];checks.append('Email de soumission fixé par le compte Grist, même si la fiche contact a une casse différente')
print(json.dumps(dict(passed=len(checks),checks=checks),ensure_ascii=False,indent=2))
