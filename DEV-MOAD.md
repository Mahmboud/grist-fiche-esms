# MOAD 2026 — développement Airmes

Les widgets historiques à la racine et `moad-ref-config.js` sont figés par
`tools/prod-immutable.json`. `v5.html` correspond exactement au blob
`a35d5130e1fdd025148aebdccaa471db909185b4`, identique au commit stable du
16 octobre `0aba1e35e7a9f52d6560eaaf32b506cc554656df`. La restauration était
déjà présente au démarrage (commit `b66cc6318d2be43a8858098dfe5b7b9a530500bb`).

## Environnements

| État | URL | Écriture |
| --- | --- | --- |
| PROD | Fichiers historiques à la racine | Interdite |
| DEV référence | `dev/moad-airmes-20261028/reference/` | Développement isolé |
| DEV migration | `dev/moad-airmes-20261028/target/` | Développement isolé |
| RECETTE | À créer après arbitrages, nouveaux fichiers `*-rc1.html` | Figée pendant les tests |
| Future PROD | À créer après recette, nouveaux fichiers `v6.html`, etc. | Figée après publication |

Ne pas promouvoir les fichiers DEV actuels. Créer une copie des widgets **et de
leurs dépendances statiques**, figer leurs empreintes, puis remapper une nouvelle
copie du `.grist`. Aucun fichier `.grist`, rapport avec réponses, export de
CONTACTS ou jeu de données de test réel ne doit être commité dans ce dépôt public.

## Migration réalisée

`tools/migrate_moad_dev.py` utilise le moteur Python officiel de grist-core,
chargé depuis un checkout séparé. Il ne modifie jamais le fichier source.
Il génère deux fichiers : une référence DEV et une migration DEV.

- `SITES` : 59 entités niveau 2 issues d'Import_entite_AIRMES, identifiées par
  la ligne source et l'identifiant de service Airmes ; pas de sites artificiels Siège.
- `ESMS` : 304 entités/services Airmes actifs de niveaux 3 à 6.
- `CONTACTS.SITE_PRINCIPAL` et `CONTACTS.SITES_RESP_AIRMES` : nouveaux rattachements.
  Le champ historique `SITES_EN_RESPONSABILITE` reste intact jusqu'à validation.
- `SITES.DIRECTION_NOMS` : formule dynamique sur CONTACTS, fonctions 20/21/23,
  site principal ou responsabilité. Le widget ne lit plus Direction_contact.
- `Autodiagnostic_DEV` : une ligne par nouveau site, 116 questions inchangées.
  Une valeur unique non vide est transférée ; des valeurs contradictoires ne
  sont jamais départagées automatiquement. Les réponses sources restent intactes.
- `Autodiagnostic_Historique_DEV` : historique séparé ; l'historique source ne
  change pas de signification. Le journal du widget constitue une aide au suivi,
  pas une preuve d'audit inviolable.
- `MIGRATION_SITES`, `MIGRATION_A_ARBITRER` : correspondances et arbitrages,
  réservés au propriétaire. 437 points à examiner, dont 392 conflits de champs.
- `PROFIL_SESSION` : projection technique en lecture seule de CONTACTS pour
  reconnaître le profil courant sans donner accès à l'annuaire complet.
- Inscription : UGECAM/SITES directement ; fonctions/questions en configuration
  statique DEV. REFERENTIEL_INSCRIPTION_ESMS n'est plus consulté par la cible.
- Validation : transaction unique CONTACTS + DEMANDES_ACCES ; le propriétaire
  approuve explicitement le profil et les droits. Les ESMS sont déduits du périmètre.

Les anciens référentiels et données sont conservés, réservés au propriétaire
dans la migration DEV. Aucun retrait de table ni renommage final n'est effectué.
Les modules de sauvegarde/restauration, exports, création rapide de référent et
synthèse Airmes hérités sont désactivés dans la cible en attendant leur adaptation.
Ils restent disponibles dans le document DEV de référence.

## Sécurité et contrôles

Les ACL des nouvelles tables sont fermées par défaut. L'Autodiag exige une
demande validée et le droit ACCES : standard = principal + responsabilités,
Siège = UGECAM, DNGU = national. Le propriétaire conserve les droits complets.
Les éditeurs peuvent modifier les réponses, pas le site ni l'UGECAM de la ligne.
La création des demandes n'autorise ni auto-validation ni liaison à un autre contact.
Les nomenclatures de sites nécessaires à l'inscription sont lisibles aux comptes
connectés ; les noms de direction et les ESMS détaillés restent soumis au périmètre.
Les partages de formulaires exportés sont désactivés dans la cible DEV.

Le fichier fourni est anonymisé : les 115 noms/emails/fonctions sont vides.
Les contrôles hors ligne ne prouvent pas les permissions réellement appliquées
par le serveur Grist. Une recette à plusieurs comptes est indispensable.

La recette doit couvrir : propriétaire, éditeur validé/non validé, site unique,
responsabilité multisite, Siège, DNGU, droits Annuaire/Liste/Arborescence distincts,
champs et tables refusés via API directe, nouvelle inscription et validation,
historique, statistiques, changement de direction, focus/autosauvegarde et erreurs.
Vérifier aussi la demande d'accès complet aux nouveaux widgets à l'importation.

## Reproduction

Utiliser Python 3.12, le répertoire `sandbox/grist` du dépôt officiel grist-core
et ses dépendances `sandbox/requirements.txt`. Le commit exact du moteur utilisé
figure dans le rapport de livraison privé, ainsi que l'empreinte de la source.

```sh
export PYTHONPATH=/chemin/grist-core/sandbox/grist:/chemin/dependances:tools
python tools/migrate_moad_dev.py /chemin/reference.grist /chemin/livraison
python tools/verify_moad_dev.py /chemin/reference.grist /chemin/livraison/MOAD_2026_DEV_AIRMES_MIGRATION.grist
python tools/check_prod_immutable.py
```

Les tests navigateur utilisent Playwright et une API simulée. Ils vérifient
les comportements d'interface ; ils ne doivent pas être présentés comme une
recette complète contre un serveur Grist.

Pour préparer une nouvelle itération, créer un autre répertoire daté ou une
nouvelle version ; ne pas modifier une URL déjà passée en RECETTE/PROD.
