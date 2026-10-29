# DEV V5 — Sources publiques et actualisation au clic

Cette version dérive du document V4 joint le 29 octobre 2026. Les anciennes
URLs, notamment v5.html, restent inchangées. Les deux widgets évolués utilisent
v6-dev5.html et liste-finess-v2-dev.html, avec de nouvelles dépendances DEV.

## Fonctionnement

Le propriétaire dispose du bouton « Actualiser les données publiques » dans
la Liste des FINESS. Il télécharge une extraction publique préparée par le dépôt,
contrôle son empreinte SHA-256, sa taille, son schéma, son âge (7 jours maximum),
les FINESS et le périmètre juridique, puis importe en une transaction Grist.
Les autres profils voient les données autorisées mais ne peuvent pas actualiser.

Le traitement national est exécuté chaque jour à 05 h 35 UTC par GitHub Actions
(et peut être lancé manuellement dans Actions). Le clic ne lance pas une nouvelle
collecte nationale : il intègre la dernière extraction préparée, dont la date est
affichée. L'exploitation dépend de la disponibilité de GitHub Actions, Pages et
des producteurs. Aucun jeton Grist ni donnée du document ne quitte Grist.

Chaque extraction est un fichier gzip immuable nommé par son empreinte. Seul
dev/public-data-v1/latest.json est un pointeur évolutif. Ce répertoire contient
uniquement des données publiques sélectionnées par les FINESS juridiques de
tools/public-data/ugecam-public.json. Les fichiers nationaux sont exclus de Git.
Ajouter un FINESS juridique inconnu à Grist exige d'étendre cette configuration ;
l'import refuse un périmètre non préparé plutôt que de produire une liste partielle.

## Périmètre et sources du premier import

UGECAM PACA-C (130037815) et UGECAM Alsace (670013754) sont ajoutées. Les autres
UGECAM, identifiants, contacts, sites, services, réponses et demandes sont conservés.
Les nouvelles structures publiques restent sans site si aucun rattachement Airmes
ne les identifie déjà. Aucun nouveau site ni service Airmes n'est inventé.

| Source | FINESS rapprochés | Données |
| --- | ---: | --- |
| FINESS+ Structures ANS | 433 | Identité, état, dates, catégorie, conventions Dispositif |
| FINESS+ Activités ANS | 433 | Activités exercées, autorisations liées et capacités détaillées |
| HAS ESSMS | 133 | Évaluations publiées, dates, chapitres et cotations |
| HAS sanitaire | 75 | Certification et dernière collecte de chaque indicateur IQSS |
| ROR public ANS | 283 | Unités/offres et services, dates des fiches régionales |
| SAE DREES | 72 | Base statistique consolidée 2024, bordereau SYGEN |
| CNSA EHPAD | 13 | Derniers tarifs déclarés retrouvés et date de déclaration |
| Nomenclatures ANS | 480 codes | Catégories, engagements, unités et statuts de capacité |

433 inclut 321 structures actives et 112 inactives, consultables en désactivant
le filtre « Structures actives ». Le fichier ROR BFC proposé par le producteur
date de juin 2026 ; les autres fichiers ont leurs propres dates. Les tarifs CNSA
proviennent des derniers fichiers proposés (annuel 2025 complété par janvier
2026), et non de tarifs supposés à jour au jour du clic. Une absence de résultat
n'est jamais convertie en zéro, « aucun dispositif » ou « non évalué ».

Le référentiel de catégories actuellement utilisé par FINESS+ est TRE_R397.
Le secteur suggéré reprend le domaine SAN/SOC : Sanitaire / Social et
médico-social. REFERENTIEL_FINESS.SECTEUR_CORRECTION permet au propriétaire
d'affiner sa sectorisation sans modifier un code officiel. Les nomenclatures
non actualisées de 2020/2021 ne sont plus utilisées pour les nouveaux champs.

## Capacités et dispositifs

Les conventions Dispositif viennent des engagements FINESS+ de type DISP,
avec dates d'effet, fin et caducité. ESMS.DISPOSITIF est calculé ; son champ
DISPOSITIF_CORRECTION est la correction locale partagée avec la liste FINESS.
Ce champ et les corrections de secteur ne sont jamais écrasés par le bouton.

Attention : une phrase du schéma JSON FINESS+ décrit les statuts de capacité de
façon contradictoire avec la nomenclature actuelle TRE_R330. Le calcul utilise
les codes officiels vérifiés : 09 = Autorisé, 08 = Installé constaté, 01 = Installé.
Les colonnes « places » totalisent seulement l'unité 02 (Place), les activités
exercées actives, sans ventilation par financement/logement/genre/habilitation.
Les capacités sont dédoublonnées par identifiant et conservées séparément par
unité/statut. Les autorisations partagées ne sont pas recopiées sur chaque EGE.
Les structures inactives n'ont pas de total actuel. Lits/logements restent visibles
dans les détails, distincts des places. SAE n'est jamais ajoutée à FINESS.

## Conservation et droits

DONNEES_PUBLIQUES est séparée des données métier. Les colonnes historiques du
catalogue ne sont pas réécrites ; de nouvelles colonnes calculées présentent la
source actuelle. Les nouveaux FINESS sont ajoutés au catalogue avec leurs IDs
stables. Les données absentes d'une extraction valide sont signalées et conservées.
Une source complémentaire indisponible conserve sa dernière version ; son état
est affiché. Un échec du socle FINESS empêche la publication de l'extraction.

Le journal ACTUALISATIONS_PUBLIQUES conserve l'empreinte, le bilan et les actions
inverses des champs importés (pour restauration administrative contrôlée). Il n'y
a pas de bouton de restauration automatique qui écraserait des corrections
effectuées depuis. Les données sont relues avant la transaction pour détecter
une modification concurrente pendant le contrôle. Le double clic est bloqué.

Les ACL existantes sont préservées. DONNEES_PUBLIQUES reprend les droits de la
Liste ESMS : validation préalable et droit ACCES_LISTE_ESMS, sites autorisés pour
un professionnel, UGECAM pour le Siège, national pour DNGU. Écriture propriétaire
uniquement. Les référentiels, sources et journal sont réservés au propriétaire.
Un changement d'entité juridique d'un FINESS déjà connu exige un arbitrage avant
import, pour ne pas déplacer implicitement le périmètre de droits.

Les pages de lecture technique ajoutées en V1–V4 disparaissent de la navigation.
Les tables restent disponibles au propriétaire dans les données brutes. Aucune
ancienne table n'est supprimée : des références et arbitrages de migration y
subsistent. Les widgets d'administration et l'arborescence complète sont conservés.

## Vérification

Le moteur Python officiel Grist vérifie la conservation des données physiques de
toutes les tables existantes, les nouvelles formules, les références, les capacités
et les corrections partagées. Une matrice des prédicats teste les permissions.
Les tests jsdom exécutent les vrais scripts et le bouton avec transport simulé :
import unique avec journal, idempotence, échec d'intégrité, source indisponible,
absence de donnée, périmètre inconnu, changement juridique et droits d'interface.
Ces contrôles ne remplacent pas une recette multi-comptes sur le serveur Grist.

```sh
python -m pip install -r tools/public-data/requirements.txt
python tools/public-data/collect.py --cache /tmp/moad-public --output dev/public-data-v1
# Avec l'environnement Python du moteur officiel Grist :
python tools/upgrade_moad_dev_v5.py courant-v4.grist recette-v5.grist dev/public-data-v1/snapshots/EMPREINTE.json.gz migration.json
python tools/verify_moad_v5.py courant-v4.grist recette-v5.grist
```
