import sys,json,pathlib,sqlite3,gzip,base64
from offline_grist import load,records,act,objtypes
from predicate_formula import parse_predicate_formula
src,dst,fixture=sys.argv[1:];e=load(dst);before=load(src);checks=[]
for t in ['CONTACTS','ESMS','Autodiagnostic','Autodiagnostic_Historique']:
 assert [{k:objtypes.encode_object(v) for k,v in r.items()} for r in records(e,t)]==[{k:objtypes.encode_object(v) for k,v in r.items()} for r in records(before,t)],t
 checks.append('Toutes les cellules conservées : '+t)
for t in ['GristHidden_SITES','GristHidden_UGECAM','GristHidden_PROFIL_SESSION']:
 res={r['id'] for r in records(e,'_grist_ACLResources') if r['tableId']==t}
 rr=[r for r in records(e,'_grist_ACLRules') if r['resource'] in res]
 assert len(rr)==2 and {r['aclFormula'] for r in rr}=={'user.Access == OWNER',''}
 checks.append('Table réellement propriétaire uniquement : '+t)
for t in ['Autodiagnostic','Autodiagnostic_Historique']:
 def acl(engine):
  rr={r['id']:r for r in records(engine,'_grist_ACLResources') if r['tableId']==t}
  return sorted((rr[r['resource']]['colIds'],r['aclFormula'],r['permissionsText']) for r in records(engine,'_grist_ACLRules') if r['resource'] in rr)
 assert acl(e)==acl(before);checks.append('Droits géographiques inchangés : '+t)
gate=records(e,'FINESS_ACCES_PAGE')[0];directory=json.loads(gzip.decompress(base64.b64decode(gate['ANNUAIRE_GZIP'])))
for t,rr in directory.items():
 assert len(rr)==len(records(e,t));assert all('CONTACTS_PERIMETRE' not in r and 'CONTACTS_DROITS' not in r for r in rr)
assert isinstance(directory['ESMS'][0]['SITE'],int)
checks.append('Projection nationale compressée : volumes complets, références numériques, aucun périmètre nominatif exposé')
f=json.loads(pathlib.Path(fixture).read_text());bootstrap=next(r for r in records(e,'DEMANDES_ACCES') if r['id']==f['bootstrap'])
ss=json.loads(bootstrap['PORTAIL_SITES_JSON']);uu=json.loads(bootstrap['PORTAIL_UGECAM_JSON']);assert all(set(s)=={'id','NOM','UGECAM'} for s in ss);assert all(set(u)=={'id','UGECAM'} for u in uu);assert json.loads(bootstrap['PORTAIL_PROFIL_JSON'])==[];checks.append('Avant validation : uniquement sélecteurs inscription, aucun contact ou profil tiers')
# Tests use synthetic identities only, never saved in the delivered .grist.
act(e,['AddRecord','CONTACTS',1,dict(EMAIL='inscription@example.invalid',NOM='TEST',PRENOM='Compte',SITE_PRINCIPAL=4,UGECAM=1,ACCES=True,ACCES_LISTE_ESMS=True)])
act(e,['AddRecord','GristHidden_PROFIL_SESSION',1,dict(CONTACT=1)])
act(e,['AddRecord','DEMANDES_ACCES',None,dict(EMAIL='inscription@example.invalid',CONTACT=1,STATUT='Validé',CONFIRMATION=True,PROFIL_ACCES='SITE')])
valid=next(r for r in records(e,'DEMANDES_ACCES') if r['EMAIL']=='inscription@example.invalid');sites=json.loads(valid['PORTAIL_SITES_JSON']);ugs=json.loads(valid['PORTAIL_UGECAM_JSON']);profile=json.loads(valid['PORTAIL_PROFIL_JSON']);assert len(sites)==len(records(e,'GristHidden_SITES')) and all('DIRECTION_CONTACTS_JSON' in r for r in sites);assert len(ugs)==13;assert profile[0]['CONTACT']==1;checks.append('Profil validé : tous les sites et toutes les directions UGECAM, profil personnel seulement')
# CONTACTS modification must update JSON on another territory immediately.
other=next(r for r in records(e,'GristHidden_SITES') if r['UGECAM']!=1)
act(e,['UpdateRecord','CONTACTS',2,dict(NOM='DIRECTION',PRENOM='Autre UGECAM',EMAIL='direction@example.invalid',TELEPHONE='0102030405',FONCTION=20,SITE_PRINCIPAL=other['id'],UGECAM=other['UGECAM'])])
new=next(r for r in records(e,'DEMANDES_ACCES') if r['id']==valid['id']);site=next(r for r in json.loads(new['PORTAIL_SITES_JSON']) if r['id']==other['id']);assert 'direction@example.invalid' in site['DIRECTION_CONTACTS_JSON'] and '0102030405' in site['DIRECTION_CONTACTS_JSON'];checks.append('Direction inter-UGECAM : email et téléphone recalculés depuis CONTACTS')
f['tables']={r['tableId']:records(e,r['tableId']) for r in records(e,'_grist_Tables')};f['request']=valid;pathlib.Path(fixture).write_text(json.dumps(f,ensure_ascii=False,default=objtypes.encode_object))
print(json.dumps(dict(passed=len(checks),checks=checks),ensure_ascii=False,indent=2))
