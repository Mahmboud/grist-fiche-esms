"""Real Grist-engine regression checks for the public-source DEV migration."""
import sys,json,pathlib,gzip,hashlib,types
from offline_grist import load,act,records,objtypes
old=load(sys.argv[1]);e=load(sys.argv[2]);act(e,['Calculate']);checks=[]
def check(n,b):
 assert b,n
 checks.append(n)
old_tables=records(old,'_grist_Tables');cols=records(old,'_grist_Tables_column')
for t in old_tables:
 name=t['tableId'];before={r['id']:r for r in records(old,name)};after={r['id']:r for r in records(e,name)};physical=[c['colId'] for c in cols if c['parentId']==t['id'] and not c['isFormula']]
 check(name+' : données physiques et identifiants préservés',before.keys()<=after.keys() and all(objtypes.equal_encoding(r[k],after[i][k]) for i,r in before.items() for k in physical))
check('Aucune table ancienne supprimée',{t['tableId'] for t in old_tables}<={t['tableId'] for t in records(e,'_grist_Tables')})
uge=records(e,'UGECAM');check('PACA-C et Alsace ajoutées avec les FINESS juridiques demandés',any(r['UGECAM']=='UGECAM PACA-C' and r['FINESS_Juridique']=='130037815' for r in uge) and any(r['UGECAM']=='UGECAM Alsace' and r['FINESS_Juridique']=='670013754' for r in uge))
finess=records(e,'FINESS_CATALOGUE');facts=records(e,'DONNEES_PUBLIQUES');sources=records(e,'SOURCES_PUBLIQUES');esms=records(e,'ESMS');refs=records(e,'REFERENTIEL_FINESS')
check('433 FINESS uniques ; 321 actifs et 112 inactifs conservés',len(finess)==len({r['FINESS'] for r in finess})==433 and sum(r['ETAT_PUBLIC']=='A' for r in finess)==321 and sum(r['ETAT_PUBLIC']=='I' for r in finess)==112)
check('Les huit sources sont intégrées sans erreur',len(sources)==8 and all(s['STATUT']=='ok' for s in sources))
check('Chaque donnée publique est reliée au FINESS exact',all(r['ETABLISSEMENT'] and next(x for x in finess if x['id']==r['ETABLISSEMENT'])['FINESS']==r['FINESS'] for r in facts))
check('Le nouveau périmètre contient 46 structures PACA-C et 31 Alsace',sum(r['FINESS_JURIDIQUE']=='130037815' for r in finess)==46 and sum(r['FINESS_JURIDIQUE']=='670013754' for r in finess)==31)
check('Aucun site ou service Airmes inventé pour les nouvelles UGECAM',len(records(e,'SITES'))==len(records(old,'SITES')) and len(esms)==len(records(old,'ESMS')))
check('Nomenclature officielle : 09 autorisé, 08 installé constaté',next(r['LIBELLE'] for r in refs if r['CLE']=='statuts-capacite:09')=='Autorisé' and next(r['LIBELLE'] for r in refs if r['CLE']=='statuts-capacite:08')=='Installé constaté')
check('Capacités des structures inactives exclues des totaux actuels',all(r['PLACES_AUTORISEES_PUBLIQUES'] is None and r['PLACES_INSTALLEES_PUBLIQUES'] is None for r in finess if r['ETAT_PUBLIC']!='A' or r['DATE_FERMETURE_PUBLIQUE']))
for r in finess:
 data=json.loads(next(x['DONNEES_JSON'] for x in facts if x['CLE']=='structures:'+r['FINESS']))
 for status,column in [('09','PLACES_AUTORISEES_PUBLIQUES'),('08','PLACES_INSTALLEES_PUBLIQUES')]:
  vv=[v['nombre'] for v in data['CAPACITES'] if v['statut']==status and v['unite']=='02'];expected=sum(vv) if vv and r['ETAT_PUBLIC']=='A' and not r['DATE_FERMETURE_PUBLIQUE'] else None
  assert objtypes.equal_encoding(expected,r[column]),(r['FINESS'],column)
check('Toutes les capacités de place concordent avec les détails, sans lits ni logements',True)
for name in ['UGECAM','ESMS','FINESS_CATALOGUE','DONNEES_PUBLIQUES','REFERENTIEL_FINESS']:
 errors=[(r['id'],k,str(v)) for r in records(e,name) for k,v in r.items() if isinstance(v,objtypes.RaisedException)]
 check(name+' : absence d’erreurs de formule',not errors)
for t in ['_grist_ACLResources','_grist_ACLRules']:
 oldrows={r['id']:r for r in records(old,t)};new={r['id']:r for r in records(e,t)}
 check('ACL antérieures conservées : '+t,all(new[i]==r for i,r in oldrows.items()))
resource=next(r for r in records(e,'_grist_ACLResources') if r['tableId']=='DONNEES_PUBLIQUES' and r['colIds']=='*');rules=sorted((r for r in records(e,'_grist_ACLRules') if r['resource']==resource['id']),key=lambda r:r['rulePos']);ns=types.SimpleNamespace
def allowed(valid=True,right=True,role='editors',siege=False,dngu=False,uge=1,contact=1,record_uge=1,contacts=[1],linked=5):
 u=ns(Access=role,demande_acces=ns(STATUT='Validé' if valid else 'À valider'),droits_supp=ns(ACCES_LISTE_ESMS=right,DNGU=dngu,SIEGE=siege,UGECAM=uge,id=contact));r=ns(ETABLISSEMENT=ns(UGECAM=record_uge,CONTACTS_PERIMETRE=contacts) if linked else 0)
 for rule in rules:
  if not rule['aclFormula'] or eval(rule['aclFormula'],{'__builtins__':{},'OWNER':'owners'},{'user':u,'rec':r}):return rule['permissionsText']
check('Propriétaire peut actualiser ; éditeur limité à la lecture',allowed(role='owners')=='+CRUD' and allowed()=='+R-CUD')
check('Refus avant validation, sans droit, hors site ou sans rattachement',all(allowed(**k)=='-CRUD' for k in [dict(valid=False),dict(right=False),dict(contacts=[]),dict(linked=0)]))
check('Siège limité à son UGECAM ; DNGU nationale',allowed(siege=True)=='+R-CUD' and allowed(siege=True,uge=2)=='-CRUD' and allowed(dngu=True,uge=2,contacts=[])=='+R-CUD')
views={r['id']:r['name'] for r in records(e,'_grist_Views')};visible=[views[p['viewRef']] for p in records(e,'_grist_Pages')]
check('Navigation limitée aux pages métier existantes et à la liste FINESS',not set(visible)&{'SITES','ESMS','FINESS_CATALOGUE','DONNEES_PUBLIQUES','REFERENTIEL_FINESS','SOURCES_PUBLIQUES','ACTUALISATIONS_PUBLIQUES','MIGRATION_A_ARBITRER'})
oldsecs={r['id']:r for r in records(old,'_grist_Views_section')};newsecs={r['id']:r for r in records(e,'_grist_Views_section')}
check('Arborescence complète et outils administratifs inchangés',all(newsecs[i]==r for i,r in oldsecs.items() if '/target/v6-dev4.html' not in str(r.get('options')) and '/target/liste-finess-v1-dev.html' not in str(r.get('options'))))
# Verify the shared local override changes both widgets' data immediately.
item=next(r for r in esms if r['FINESS_REF']);act(e,['UpdateRecord','ESMS',item['id'],{'DISPOSITIF_CORRECTION':'Dispositif local de contrôle'}]);act(e,['Calculate']);updated=next(r for r in records(e,'ESMS') if r['id']==item['id']);fin=next(r for r in records(e,'FINESS_CATALOGUE') if r['id']==updated['FINESS_REF'])
check('Correction locale Dispositif partagée immédiatement entre les deux pages',updated['DISPOSITIF']=='Dispositif local de contrôle' and 'Dispositif local de contrôle' in fin['DISPOSITIF'])
cat=next(r for r in refs if r['CLE']=='categorie:'+fin['CATEGORIE_CODE_PUBLIC']);act(e,['UpdateRecord','REFERENTIEL_FINESS',cat['id'],{'SECTEUR_CORRECTION':'Secteur local de contrôle'}]);act(e,['Calculate']);check('La sectorisation peut être corrigée sans modifier la catégorie officielle',next(r for r in records(e,'FINESS_CATALOGUE') if r['id']==fin['id'])['SECTEUR']=='Secteur local de contrôle')
print(json.dumps(dict(passed=len(checks),checks=checks,limits=['Moteur Grist officiel et prédicats ACL testés hors ligne ; recette multi-comptes sur serveur non effectuée.']),ensure_ascii=False,indent=2))
