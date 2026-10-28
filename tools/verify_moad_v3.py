"""Real Grist-engine tests plus explicit FINESS ACL predicate matrix."""
import sys,json,types,pathlib
from offline_grist import load,act,records,objtypes
e=load(sys.argv[1]);act(e,['Calculate']);checks=[]
def check(n,b):
    assert b,n
    checks.append(n)
for t in ['FINESS_CATALOGUE','FINESS_EQUIPEMENTS','SITES','ESMS']:
    errors=[(r['id'],k,objtypes.encode_object(v)) for r in records(e,t) for k,v in r.items() if isinstance(v,objtypes.RaisedException)]
    check(t+' sans erreur de formule',not errors)
cat=records(e,'FINESS_CATALOGUE');check('254 FINESS issus des EJ UGECAM et 454 lignes d’équipement',len(cat)==254 and len(records(e,'FINESS_EQUIPEMENTS'))==454)
check('Date de création jamais remplacée par une date d’ouverture',all(not r['DATE_CREATION'] for r in cat))
check('Sources et millésime conservés',all(r['MILLESIME_ETAB']=='2026-05-12' and r['DATE_ARRETE_DONNEES']=='2026-05-04' and r['DONNEES_SOURCE_JSON'] for r in cat))
# Work in memory: the delivered file is not modified by fixtures.
sites=records(e,'SITES');s1,s2=sites[0]['id'],sites[1]['id'];cid=max(r['id'] for r in records(e,'CONTACTS'))+100
act(e,['AddRecord','CONTACTS',cid,{'NOM':'DIRECTION_TEST','PRENOM':'Recette','EMAIL':'direction@example.invalid','TELEPHONE':'03 00 00 00 00','FONCTION':20,'SITE_PRINCIPAL':s1,'SITES_RESP_AIRMES':['L',s2]}])
for sid in [s1,s2]:
    c=json.loads(next(r for r in records(e,'SITES') if r['id']==sid)['DIRECTION_CONTACTS_JSON'])
    check('Direction nom/mail/tél dynamique — site '+str(sid),any(r['email']=='direction@example.invalid' and r['telephone']=='03 00 00 00 00' for r in c))
act(e,['UpdateRecord','CONTACTS',cid,{'EMAIL':'corrige@example.invalid','TELEPHONE':'04 00 00 00 00'}])
check('Coordonnées corrigées immédiatement depuis CONTACTS','corrige@example.invalid' in next(r for r in records(e,'SITES') if r['id']==s1)['DIRECTION_CONTACTS_JSON'])
f=cat[0]['FINESS'];catid=cat[0]['id'];es=records(e,'ESMS')[:2]
act(e,*[['UpdateRecord','ESMS',r['id'],{'FINESS':f,'SITE':sid}] for r,sid in zip(es,[s1,s2])])
now=next(r for r in records(e,'FINESS_CATALOGUE') if r['id']==catid)
check('Correspondance FINESS exacte, y compris plusieurs sites',set(now['SITES_LIES'])=={s1,s2} and cid in now['CONTACTS_PERIMETRE'])
for r in records(e,'FINESS_EQUIPEMENTS'):
    if r['FINESS']==f:act(e,['UpdateRecord','FINESS_EQUIPEMENTS',r['id'],{'PRESENT_SOURCE':False}])
start=max(r['id'] for r in records(e,'FINESS_EQUIPEMENTS'))+100
for n,aut,inst,flag in [(0,30,20,'N'),(1,500,600,'O'),(2,5,2,'N')]:
    act(e,['AddRecord','FINESS_EQUIPEMENTS',start+n,{'CLE_SOURCE':'test|'+str(n),'FINESS':f,'CAPACITE_AUTORISEE':aut,'CAPACITE_INSTALLEE':inst,'IND_SUP_AUT':flag,'IND_SUP_INST':flag,'PRESENT_SOURCE':True}])
now=next(r for r in records(e,'FINESS_CATALOGUE') if r['id']==catid);check('Seules les capacités actives sont totalisées',now['NB_PLACES_AUTORISEES']==35 and now['NB_PLACES_INSTALLEES']==22)
act(e,['UpdateRecord','FINESS_EQUIPEMENTS',start,{'ANOMALIE':'Contradiction'}]);now=next(r for r in records(e,'FINESS_CATALOGUE') if r['id']==catid);check('Capacités ambiguës non présentées comme un total fiable',now['NB_PLACES_AUTORISEES'] is None and now['NB_PLACES_INSTALLEES'] is None)
ns=types.SimpleNamespace
resources=records(e,'_grist_ACLResources');rules=records(e,'_grist_ACLRules')
def permission(table,u,rec):
    rid=next(r['id'] for r in resources if r['tableId']==table and r['colIds']=='*')
    for r in sorted((r for r in rules if r['resource']==rid),key=lambda r:r['rulePos']):
        if not r['aclFormula'] or eval(r['aclFormula'],{'__builtins__':{},'OWNER':'owners'},{'user':u,'rec':rec}):return r['permissionsText']
def user(valid=True,enabled=True,siege=False,dngu=False,uid=1,contact=cid,role='editors'):
    return ns(Access=role,demande_acces=ns(STATUT='Validé' if valid else 'À valider'),droits_supp=ns(ACCES_LISTE_ESMS=enabled,SIEGE=siege,DNGU=dngu,UGECAM=uid,id=contact))
record=ns(SITE=s1,UGECAM=1,CONTACTS_PERIMETRE=[cid])
check('Page FINESS masquée avant validation ou sans droit Liste ESMS',permission('FINESS_ACCES_PAGE',user(valid=False),ns())==permission('FINESS_ACCES_PAGE',user(enabled=False),ns())=='-CRUD')
check('Standard : mêmes sites autorisés ; autres sites refusés',permission('FINESS_CATALOGUE',user(),record)=='+R-CUD' and permission('FINESS_CATALOGUE',user(contact=999999),record)=='-CRUD')
check('Siège limité à son UGECAM ; DNGU nationale',permission('FINESS_CATALOGUE',user(siege=True),record)=='+R-CUD' and permission('FINESS_CATALOGUE',user(siege=True,uid=9),record)=='-CRUD' and permission('FINESS_CATALOGUE',user(dngu=True),record)=='+R-CUD')
check('Écritures/imports réservés au propriétaire',permission('FINESS_CATALOGUE',user(role='owners',valid=False),record)=='+CRUD' and permission('FINESS_IMPORTS',user(),ns())=='-CRUD')
check('Liste technique des contacts non exposée',any(r['tableId']=='FINESS_CATALOGUE' and r['colIds']=='CONTACTS_PERIMETRE' for r in resources))
check('Nouvelle page présente',any(r['name']=='Liste des FINESS du Groupe UGECAM' for r in records(e,'_grist_Views')))
print(json.dumps({'passed':len(checks),'checks':checks,'limits':['Prédicats ACL testés hors ligne ; recette réelle multi-comptes requise']},ensure_ascii=False,indent=2))
