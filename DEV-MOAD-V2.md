# Correctifs DEV v2 — bandeau UGECAM, localisation et administration

La copie `MOAD_2026_DEV_AIRMES_CORRECTIFS_V2.grist` dérive de la livraison DEV
Airmes précédente. Elle conserve toutes les données et les arbitrages de migration.

## Nouvelles URLs

Dans `dev/moad-airmes-20261028/target/` :

- `v6-dev2.html` et `airmes-arborescence-v2-dev.html` : bandeau DG, responsable
  médico-social, RSI et qualité au-dessus des fiches Site **et** ESMS ; cartes et
  adresses disponibles en bas de fiche.
- `admin-maintenance-v2-dev.html` : sauvegarde .grist, CONTACTS.csv, exports CSV,
  sauvegarde/restauration Excel de l'Autodiag DEV.
- `admin-nouveau-referent-v2-dev.html` : création atomique de CONTACTS,
  PROFIL_SESSION et DEMANDES_ACCES validée. Les ESMS sont déduits des sites.
- `admin-exports-excel-v2-dev.html` : réponses intégrales, statistiques de
  remplissage et détail des réponses, avec les 116 questions actuelles.

Les anciennes URLs DEV et toutes les URLs PROD restent inchangées. Le .grist
v2 doit être utilisé pour bénéficier des nouvelles colonnes calculées.

## Données et accès

`UGECAM.DG_NOMS`, `RESP_MS_NOMS`, `RSI_NOMS` et `QUALITE_NOMS` sont calculées
depuis CONTACTS, fonctions 53, 47, 49 et 48. La priorité aux contacts Siège
reproduit la logique V5. Une ACL de colonnes limite leur lecture aux profils
validés habilités sur l'UGECAM, ou à la DNGU ; le propriétaire conserve l'accès.
Le widget peut aussi lire les contacts déjà autorisés à son profil.

`SITES.LOCALISATIONS_JSON` conserve les adresses et coordonnées sources dont
le rattachement au site Airmes est établi par MIGRATION_SITES : 99 localisations
sur 54 sites. Les anciennes appellations ne deviennent pas une nouvelle source
métier. Aucun point unique n'est choisi lorsque plusieurs adresses existent.
Les coordonnées d'un ESMS ne sont transférées que si leur correspondance est
univoque. Des coordonnées absentes ou (0,0) ne génèrent jamais de carte.

Les trois outils d'administration exigent un accès propriétaire. Le téléchargement
.grist utilise un jeton de lecture de l'API du document, sans dépendre du format
de l'URL dans la barre d'adresse. En cas de refus de ce point d'API par l'instance,
le widget indique le téléchargement natif Grist.

Les restaurations Excel sont entièrement validées avant la transaction : sites
inconnus, correspondances multiples et historique non rattachable annulent
l'import sans mutation. La restauration CSV des contacts exclut les colonnes
calculées et refuse la suppression de contacts pour conserver leurs références.
La restauration intégrale d'un document s'effectue à partir de sa sauvegarde .grist.

## Tests

- Contrôles du moteur Grist : conservation des sources, formules, ACL déclarées,
  direction et déclencheurs d'audit de la première livraison.
- Tests supplémentaires des rôles UGECAM, priorité Siège, mise à jour dynamique,
  localisation, création réelle du référent et de sa demande validée.
- Tests DOM des nouvelles vues, refus des non-propriétaires, transaction de
  création, sauvegarde, restauration compatible et rejet avant mutation.
- Génération réelle des trois fichiers XLSX et de la sauvegarde Excel ; relecture
  avec SheetJS et openpyxl. Statistiques : espaces, espaces insécables et listes
  Grist vides ne comptent pas comme réponses ; répartitions multichoix incluses.

Le transport des tests d'interface est simulé. Une recette sur l'instance Grist
avec plusieurs comptes reste nécessaire. Les conflits de migration de la
livraison précédente restent conservés et non arbitrés.

```sh
export PYTHONPATH=/chemin/grist-core/sandbox/grist:/chemin/dependances:tools
python tools/upgrade_moad_dev_v2.py /chemin/MOAD_2026_DEV_AIRMES_MIGRATION.grist /chemin/MOAD_2026_DEV_AIRMES_CORRECTIFS_V2.grist
```
