# DEV V4 — FINESS historiques et arborescence originale

La V4 repart de la copie de recette V3. Elle ajoute de nouvelles URLs sans
modifier les fichiers PROD ni les précédents widgets DEV.

## Reprise des FINESS

Les 168 lignes de ESMS_Liste_UGECAM_ sont toutes conservées et tracées dans
REPRISE_FINESS_HISTORIQUE. Les 157 lignes portant un FINESS géographique
représentent 145 codes distincts : tous ces codes sont désormais présents dans
le champ FINESS des lignes servant aux fiches, avec leurs zéros initiaux.

Les liens explicites déjà présents vers les services Airmes sont exploités.
Un FINESS peut être partagé par plusieurs services. Les codes absents de la
source des fiches donnent lieu à 128 lignes d'établissements historiques,
identifiées comme telles, sans identifiant de service Airmes inventé.
Leur site est renseigné uniquement lorsque la correspondance historique est
univoque ; trois établissements restent dans « Établissements à rapprocher ».
La source des fiches comprend désormais 432 lignes. Les noms historiques
restent disponibles pour la recherche et la traçabilité.

Les numéros des sièges sont traités comme FINESS juridiques, pas comme faux
établissements géographiques. UGECAM.FINESS_Juridique reste la source et
UGECAM.FINESS_JURIDIQUES fournit la liste normalisée (11 codes, dont deux pour
CENTRE-ALPC). Les numéros sont affichés dans le bandeau UGECAM et disponibles
dans les colonnes juridiques de la source des fiches. Un texte tel que
« en cours de création » est conservé comme information, sans devenir un code.

Le catalogue data.gouv garde ses règles de rapprochement par entité juridique.
Un FINESS historique non trouvé dans ce catalogue n'est pas présenté comme une
donnée publique importée. Les correspondances exactes et périmètres du catalogue
sont recalculés depuis les codes associés aux fiches.

## Présentation de la direction

Le symbole @ est remplacé par le libellé Email. Les coordonnées utilisent une
carte avec initiales, nom, fonction et deux zones Email / Téléphone adaptées
aux petits écrans. La direction reste calculée depuis CONTACTS.

## Arborescence restaurée

airmes-arborescence-v4-dev.html reprend l'HTML, le CSS et la logique d'interface
de airmes-arborescence-v1.html à l'identique. Seuls les alias des lecteurs de
données changent. Recherche, filtres UGECAM/établissement, compteurs, détail des
niveaux, Tout déplier, Tout replier et affichage uniquement des feuilles sont
conservés.

Les projections ARBORESCENCE_AIRMES_DEV et ARBO_ESMS_REFERENCES contiennent les
1 174 lignes de hiérarchie et les 168 références historiques, sans exposer les
anciennes colonnes de direction ni les données personnelles des tables source.
La recherche dispose de 1 171 lignes utiles : l'en-tête et deux lignes entièrement
vides ne deviennent pas des nœuds artificiels. Les libellés UGECAM sont résolus
à partir des références ou de leur libellé, sans afficher les erreurs de références.

Les ACL exigent une demande validée et le droit ACCES_ARBORESCENCE : principal
et responsabilités pour un professionnel, UGECAM pour le Siège, national pour
la DNGU. Le propriétaire conserve la totalité. Les noms de contexte des branches
autorisées sont conservés. Les trois référentiels initialement réservés au
propriétaire restent protégés.

## Vérifications et utilisation

Tests du moteur Grist : couverture exhaustive des FINESS, conservation des
sources, conservation des lignes Airmes existantes, absence d'erreurs dans les
nouvelles cellules et matrice des prédicats de permissions. Tests DOM : cartes
de direction, lignes historiques et sans site, comparaison exacte du widget
original après remplacement des trois alias, recherche, filtres et vue feuilles.
Le transport des tests DOM est simulé ; une recette multi-comptes sur le serveur
Grist reste nécessaire.

La copie de recette conserve les contacts anonymisés de la V3 livrée. Pour
préserver les contacts complétés après cette livraison, appliquer l'évolution
au fichier .grist courant, pas remplacer ce document par la copie anonymisée.

```sh
export PYTHONPATH=/chemin/grist-core/sandbox/grist:/chemin/dependances:tools
python tools/upgrade_moad_dev_v4.py courant-v3.grist recette-v4.grist reprise-finess.json
python tools/verify_moad_v4.py courant-v3.grist recette-v4.grist
```
