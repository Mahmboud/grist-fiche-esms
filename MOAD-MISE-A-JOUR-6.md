# Mise à jour 6

Cette copie reprend la dernière V5 livrée et utilise exclusivement un nouveau
paquet de widgets : widgets/moad-20261029-r6/. Les URLs précédentes, dont
v5.html, restent inchangées.

## Affichage

- Suppression des bandeaux et titres de développement dans les widgets actifs.
- Dispositif conservé uniquement dans la Liste FINESS et son détail de source.
- Aucun dispositif administratif n'est propagé aux fiches Site ou ESMS/service.
- Libellé de secteur : « Médico-social et social ».
- L'arborescence complète, ses filtres, sa recherche et sa vue feuilles restent
  disponibles. Le panneau historique vide qui l'accompagnait est retiré.

Les conventions Dispositif proviennent des engagements DISP de FINESS+
Structures, extraction du 29 octobre 2026. Pour le FINESS 700780109 : engagement
DIT à effet du 1er janvier 2025 et PCP à effet du 1er janvier 2021. Ces dates
administratives ne sont pas les dates d'extraction, ni une preuve d'attribution
individuelle à chaque service Airmes.

## Accès et tables masquées

La règle de création de DEMANDES_ACCES accordait C mais refusait R sur la ligne
créée. Elle accorde maintenant création et lecture de sa propre demande, sans
autoriser modification, suppression, auto-validation ou usurpation d'email.
L'email reste contrôlé par l'identité Grist et sa formule déclenchée côté serveur.
Le formulaire bloque une double soumission et vérifie les choix obligatoires.

Les positions des règles sont normalisées en un seul lot après création : la
colonne rulePos est globale et ses rééquilibrages pouvaient déplacer un refus
avant une autorisation. Les règles sont testées avec le compilateur TypeScript
et RecordView officiels de Grist, avec des références numériques réelles.
Les parcours de références imbriqués dans les ACL des données publiques et de
l'historique sont remplacés par des projections directes.

Les trois tables signalées utilisent le préfixe natif GristHidden_ : SITES,
UGECAM et PROFIL_SESSION. Elles disparaissent des listes de données sources et
des sélecteurs de tables. Le propriétaire les consulte dans Administration,
Sauvegardes, « Référentiels Sites, UGECAM et profils » ; Sites et UGECAM y sont
modifiables avec contrôle de concurrence. Le masquage est une règle de
présentation, distincte des ACL : les widgets conservent leurs accès API autorisés
aux libellés et à leur propre profil. Les colonnes privées restent protégées.

## Nettoyage

15 tables sont retirées de la base active : les deux anciennes nomenclatures de
sites, l'ancienne liste ESMS et ses deux tables de synthèse, la liste dérivée
Airmes, l'import Airmes historique, le référentiel d'inscription remplacé, les
anciennes tables Autodiag et historique, les trois tables d'audit/migration et
les anciens équipements/imports FINESS de mai 2026.

Leurs données et schémas sont regroupés dans ARCHIVES_MIGRATION, réservée au
propriétaire : 19 entrées, 3 623 lignes archivées, y compris les 72 questionnaires
historiques et les 437 arbitrages. Les champs de compatibilité retirés sont
également archivés. Les données actives (contacts, sites, ESMS, réponses et
identifiants) sont conservées. Les deux tables Autodiag actives prennent les noms
Autodiagnostic et Autodiagnostic_Historique.

La copie finale contient 22 tables actives, contre 36 auparavant. Les tables
utilitaires restantes servent aux droits des pages, aux widgets, aux sources
publiques ou à l'administration. Les anciennes tables et colonnes physiques
orphelines sont supprimées de SQLite après export ; les archives restent dans
une seule table privée. Le fichier source n'est jamais modifié.

## Validation

- 52 contrôles du moteur Python officiel : conservation, archives, références,
  formules, schéma SQLite exact et email déclenché sous identité éditeur.
- 10 contrôles avec le véritable compilateur ACL TypeScript et RecordView :
  reproduction du défaut initial, création/lecture, refus de fraude, droits de
  site/Siège/DNGU, historique et masquage natif.
- 10 contrôles DOM : inscription, suppression des bandeaux, dispositifs limités
  aux FINESS, libellé de secteur, arborescence, sauvegarde/historique Autodiag,
  navigation des 116 questions, export Excel réellement généré et rouvert,
  administration propriétaire et refus aux non-propriétaires.
- Les 37 fichiers et dépendances de production conservent leurs empreintes.

La session multi-comptes du serveur Grist n'a pas été pilotée. Les tests DOM
utilisent un transport simulé ; les compilateurs et le moteur de données sont
ceux du projet Grist officiel.

```sh
python tools/build_moad_r6.py
# Avec le moteur officiel Grist dans PYTHONPATH :
python tools/upgrade_moad_r6.py courant-v5.grist mise-a-jour-6.grist nettoyage.json
python tools/verify_moad_r6.py courant-v5.grist mise-a-jour-6.grist fixtures.json
node tools/test_moad_r6_acl.cjs fixtures.json /chemin/compilation-native-grist-acl.cjs
node tools/test_moad_r6_ui.cjs fixtures.json /chemin/node_modules
```
