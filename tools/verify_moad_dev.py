"""Offline structural, preservation, formula and ACL-predicate checks.

ACL-predicate checks do not replace a multi-account test against a Grist server.
"""
import sys,json,hashlib,sqlite3,collections,types
from offline_grist import load,act,records,objtypes

source,dev=sys.argv[1:3]
original=load(source);e=load(dev);act(e,['Calculate'])
results=[]
def check(label,condition):
    assert condition,label
    results.append(label)
for t in ['Autodiagnostic','CONTACTS','ESMS_Liste_UGECAM_','Import_entite_AIRMES','SITES_nomenclature_UGECAM','SITES_nomenclature_AIRMES','AUTODIAG_REFERENTIEL_QUESTIONS']:
    old={r['id']:r for r in records(original,t)};new={r['id']:r for r in records(e,t)}
    check(t+': toutes les lignes sources conservées',old.keys()==new.keys())
    tr=next(r['id'] for r in records(e,'_grist_Tables') if r['tableId']==t)
    cols=[r['colId'] for r in records(original,'_grist_Tables_column') if r['parentId']==tr and not r['isFormula']]
    check(t+': valeurs non calculées conservées',all(objtypes.equal_encoding(old[i][k],new[i][k]) for i in old for k in cols))
sites=records(e,'SITES');esms=records(e,'ESMS');aa=records(e,'Autodiagnostic_DEV')
check('59 sites Airmes et une ligne Autodiag par site',len(sites)==len(aa)==59 and {r['SITE'] for r in aa}=={r['id'] for r in sites})
check('ESMS rattachés à un site valide',all(r['SITE'] in {s['id'] for s in sites} for r in esms))
errors=[]
for t in ['SITES','ESMS','Autodiagnostic_DEV','PROFIL_SESSION']:
    for r in records(e,t):
        for k,v in r.items():
            if isinstance(v,objtypes.RaisedException):errors.append((t,r['id'],k,objtypes.encode_object(v)))
check('Aucune erreur dans les cellules des nouvelles tables',not errors)
check('116 questions conservées',len(records(e,'AUTODIAG_REFERENTIEL_QUESTIONS'))==116)
ref=next(t['id'] for t in records(e,'_grist_Tables') if t['tableId']=='Autodiagnostic_DEV')
audit={r['colId']:r for r in records(e,'_grist_Tables_column') if r['parentId']==ref}
check('Déclencheurs date et auteur conservés',audit['Derniere_mise_a_jour']['recalcWhen']==audit['Derniere_mise_a_jour_contact']['recalcWhen']==2)
first_id=aa[0]['id']
act(e,['UpdateRecord','Autodiagnostic_DEV',first_id,{'Derniere_mise_a_jour':1}])
act(e,['UpdateRecord','Autodiagnostic_DEV',first_id,{'ORG01_Texte':'Test de déclencheur en mémoire uniquement'}])
check('Date de modification recalculée lors de la saisie',next(r for r in records(e,'Autodiagnostic_DEV') if r['id']==first_id)['Derniere_mise_a_jour']>1)
for t in ['AUTODIAG_REFERENTIEL_QUESTIONS','REFERENTIEL_FONCTIONS','REFERENTIEL_INSCRIPTION_ESMS']:
    rid=next(r['id'] for r in records(e,'_grist_ACLResources') if r['tableId']==t)
    rr=sorted([r for r in records(e,'_grist_ACLRules') if r['resource']==rid],key=lambda r:r['rulePos'])
    check(t+': ACL propriétaire uniquement',len(rr)==2 and rr[0]['aclFormula']=='user.Access == OWNER' and rr[1]['permissionsText']=='-CRUD')
# Real engine dependency propagation, with synthetic data in memory only.
s1,s2=sites[0]['id'],sites[1]['id'];testid=max(r['id'] for r in records(e,'CONTACTS'))+100
act(e,['AddRecord','CONTACTS',testid,{'NOM':'TEST_DIRECTION','PRENOM':'Recette','EMAIL':'fixture@example.invalid','FONCTION':20,'SITE_PRINCIPAL':s1,'SITES_RESP_AIRMES':['L',s2]}])
check('Direction calculée depuis le site principal et la responsabilité',all('TEST_DIRECTION' in r['DIRECTION_NOMS'] for r in records(e,'SITES') if r['id'] in [s1,s2]))
act(e,['UpdateRecord','CONTACTS',testid,{'NOM':'NOM_CORRIGE','SITE_PRINCIPAL':s2,'SITES_RESP_AIRMES':['L']}])
check('Direction actualisée immédiatement après correction CONTACTS',all(('NOM_CORRIGE' in r['DIRECTION_NOMS'])==(r['id']==s2) for r in records(e,'SITES') if r['id'] in [s1,s2]))
act(e,['UpdateRecord','CONTACTS',testid,{'FONCTION':48}])
check('Fonction non direction exclue',all('NOM_CORRIGE' not in r['DIRECTION_NOMS'] for r in records(e,'SITES')))

# Check generated ACL formulas using Python's matching predicate semantics.
# Only the generated target resource is evaluated (never arbitrary source code).
ns=types.SimpleNamespace
rid=next(r['id'] for r in records(e,'_grist_ACLResources') if r['tableId']=='Autodiagnostic_DEV' and r['colIds']=='*')
rules=sorted([r for r in records(e,'_grist_ACLRules') if r['resource']==rid],key=lambda r:r['rulePos'])
def permission(user,site,ugecam):
    for r in rules:
        if not r['aclFormula'] or eval(r['aclFormula'],{'__builtins__':{},'OWNER':'owners'},{'user':user,'rec':ns(SITE=site,UGECAM=ugecam)}):return r['permissionsText']
def user(role='editors',valid=True,enabled=True,siege=False,dngu=False,main=s1,resp=[s2],ugecam=sites[0]['UGECAM']):
    return ns(Access=role,demande_acces=ns(STATUT='Validé' if valid else 'À valider'),droits_supp=ns(ACCES=enabled,SIEGE=siege,DNGU=dngu,SITE_PRINCIPAL=main,SITES_RESP_AIRMES=resp,UGECAM=ugecam))
check('ACL standard : principal + responsabilité, hors périmètre refusé',permission(user(),s1,1)==permission(user(),s2,2)=='+RU-CD' and permission(user(),99999,1)=='-CRUD')
check('ACL Siège limitée à son UGECAM',permission(user(siege=True),99999,sites[0]['UGECAM'])=='+RU-CD' and permission(user(siege=True),s1,99999)=='-CRUD')
check('ACL DNGU nationale',permission(user(dngu=True),99999,99999)=='+RU-CD')
check('ACL refus avant validation ou sans droit Autodiag',permission(user(valid=False),s1,1)==permission(user(enabled=False),s1,1)=='-CRUD')
check('ACL propriétaire complète',permission(user(role='owners',valid=False),99999,99999)=='+CRUD')
options='\n'.join(r.get('options') or '' for r in records(e,'_grist_Views_section'))
check('Aucun widget métier ne pointe sur une URL PROD',not any('/grist-fiche-esms/'+s in options for s in ['v5.html','acces-moad-v1.html','autodiagnostic-questionnaire-v4.html','autodiagnostic-synthese-v3.html']))
print(json.dumps({'passed':len(results),'checks':results,'limits':['ACL réellement appliquées à tester sur un serveur Grist avec comptes distincts','115 contacts anonymisés dans la pièce jointe : noms, emails et fonctions vides','Conflits de migration non arbitrés']},ensure_ascii=False,indent=2))
