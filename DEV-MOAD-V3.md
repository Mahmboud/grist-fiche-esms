# DEV v3 — direction détaillée et FINESS

Cette évolution ajoute de nouvelles URLs et une nouvelle copie de recette du
`.grist`. Aucun widget PROD ni fichier DEV déjà livré n'est modifié.

## Fiches Site et ESMS/service

- Le libellé « Fiche site Airmes » devient « Fiche du site ».
- `CONTACTS.TELEPHONE` conserve un numéro professionnel comme texte, sans
  supprimer le zéro initial. Le formulaire administrateur de nouveau référent
  dispose d'un champ facultatif correspondant.
- `SITES.DIRECTION_CONTACTS_JSON` est une projection calculée de CONTACTS :
  fonctions 20/21/23, site principal ou responsabilité. Nom, fonction, mail et
  téléphone sont présentés sur les deux fiches. Les coordonnées ne sont pas
  copiées dans ESMS. La projection bénéficie des mêmes ACL de colonnes que la
  direction existante.
- Le bloc RGPD synthétique cite désormais le téléphone professionnel.

## Bulle FINESS et modèle extensible

Le survol ou la prise de focus d'un FINESS ouvre une carte rectangulaire. Elle
se referme à la sortie du pointeur, à la perte de focus ou avec Échap. Elle
présente capacités autorisées/installées, création, ouverture, autorisation,
catégorie et millésimes. Le contenu est échappé et la carte reste dans le
viewport. Aucun appel data.gouv n'est effectué au survol.

`FINESS_CATALOGUE` conserve une ligne par FINESS géographique. La date de
création est un champ indépendant et reste vide si elle n'est pas fournie.
`DONNEES_COMPLEMENTAIRES` contient un objet JSON extensible, dont les propriétés
peuvent être affichées dans la carte sans modifier sa structure. Les colonnes
sources et les données brutes restent disponibles pour les évolutions futures.

`FINESS_EQUIPEMENTS` conserve les lignes par discipline/activité/clientèle, les
capacités totales, les indicateurs de suppression, dates et données sources.
Les totaux ne comptent que les lignes actives (indicateur N). Les sous-capacités
hommes/femmes/aide sociale ne sont pas ajoutées aux totaux. Des lignes strictement
identiques sont dédupliquées ; des lignes contradictoires sont signalées, et
les totaux correspondants ne sont pas présentés comme fiables. Un manque de
données n'est pas transformé en capacité zéro.

## Page « Liste des FINESS du Groupe UGECAM »

La liste est identifiée via `nofinessej`, comparé exclusivement aux FINESS
juridiques renseignés dans UGECAM. Elle prend en compte les deux FINESS EJ de
CENTRE-ALPC et normalise les identifiants espacés tout en préservant les zéros
initiaux et les identifiants alphanumériques valides. Aucune correspondance
ESMS/site n'est déduite d'une ressemblance de nom.

L'import initial a retenu 254 établissements et 454 lignes d'équipement à
partir de 11 FINESS juridiques. Il couvre les catégories sanitaires et
médico-sociales présentes dans le fichier établissements ; les équipements
sociaux ne renseignent pas nécessairement les capacités du domaine sanitaire.

La page exige une demande validée et ACCES_LISTE_ESMS. La DNGU habilitée lit le
groupe ; un profil Siège lit son UGECAM ; un profil standard lit les FINESS des
ESMS attachés à son site principal ou à ses sites en responsabilité, y compris
si un FINESS est lié à plusieurs sites. Les FINESS encore sans rattachement
restent accessibles aux profils Siège/DNGU correspondants et au propriétaire.
La liste technique des contacts servant au contrôle de périmètre est masquée.
Les écritures et journaux d'import sont réservés au propriétaire.

## Réimport des deux CSV

Un panneau propriétaire permet de sélectionner les deux fichiers, de vérifier
le rapprochement, puis d'appliquer l'import en une transaction Grist. Il
reconnaît les sections officielles `structureet`, `geolocalisation` et
`equipementsocial`, sans supposer une première ligne d'en-têtes ordinaire.
Seules les lignes du groupe sont conservées. Les millésimes, noms de fichiers,
empreintes SHA-256, comptages et avertissements sont journalisés dans
`FINESS_IMPORTS`.

Les identifiants de lignes, compléments manuels et dates de création déjà
renseignées sont préservés au réimport. Les lignes absentes d'un import sont
signalées, sans suppression. Un changement intervenu depuis la prévisualisation
oblige à vérifier à nouveau les fichiers. Contacts, sites et questionnaires ne
sont jamais modifiés par cet import.

Sources utilisées :

- https://www.data.gouv.fr/datasets/finess-extraction-du-fichier-des-etablissements
- https://www.data.gouv.fr/datasets/finess-extraction-des-equipements-sociaux-et-medico-sociaux

Publications du 12 mai 2026 ; les producteurs annoncent un arrêt des données
au 4 mai 2026, et une migration vers les nouveaux flux FINESS+. Ces deux anciens
flux sont pris en charge ici comme demandé. Ils fournissent des dates
d'ouverture et d'autorisation, pas une date de création à substituer.

## Livraisons et validation

La copie de recette part de la dernière V2 livrée, dont les contacts étaient
anonymisés. Elle n'inclut pas les contacts complétés dans une instance Grist
après cette livraison. Appliquer le script d'évolution au `.grist` courant
permet de conserver ces contacts ; aucun remplacement du document courant par
la copie de recette ne doit être présenté comme une conservation de ces ajouts.

Les tests couvrent le moteur Grist, les prédicats ACL, le parseur/importeur et
les interactions DOM de la carte et de l'import. Une recette réelle avec des
comptes distincts sur l'instance Grist reste nécessaire.

```sh
node tools/test_finess_core.cjs
export PYTHONPATH=/chemin/grist-core/sandbox/grist:/chemin/dependances:tools
python tools/upgrade_moad_dev_v3.py courant-v2.grist recette-v3.grist plan-finess.json
python tools/verify_moad_v3.py recette-v3.grist
```
