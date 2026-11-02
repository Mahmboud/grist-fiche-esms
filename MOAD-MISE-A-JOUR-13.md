# Mise à jour 13 — inscription et page d’arrivée

L’inscription pouvait être enregistrée tout en déclenchant « Unexpected row removal » pendant la diffusion des actions aux clients. La règle de création accordait également la lecture via `newRec`, alors que Grist ajoute d’abord la ligne sans EMAIL puis renseigne EMAIL par une formule déclenchée avec l’identité authentifiée.

Le filtre natif de diffusion vérifie d’abord les lignes avec `rec` seul. L’ancienne règle rendait la lecture indéterminée (`mixed`) sans `newRec`, mais la refusait lorsqu’il était fourni sur l’état intermédiaire sans email. La ligne passait donc une étape du filtre puis échouait à la suivante. Les anciens tests sur le seul état final ne reproduisaient pas cette séquence.

Le correctif retire uniquement R de la règle de création : `+CR` devient `+C`. La lecture de sa propre demande reste accordée par la règle indépendante basée sur `rec.EMAIL == user.Email`. La ligne intermédiaire est correctement masquée, puis l’actualisation de l’email produit une addition de la ligne complète. L’identité authentifiée, l’interdiction de s’auto-valider, le refus de resoumettre après validation et les droits du propriétaire sont conservés.

Pour l’arrivée sur Bienvenue / Mon accès, les deux ordres sont alignés : `_grist_Pages.pagePos` pour les clients récents et `_grist_TabBar.tabPos` pour l’ancien mécanisme. Les noms, dispositions et autres pages restent inchangés. Un lien explicitement dirigé vers une autre page (`/p/...`) conserve naturellement cette destination. L’accueil présente le formulaire avant soumission, l’attente après envoi et la confirmation après validation.

Les trois fichiers de l’accueil sont copiés à l’identique sous une nouvelle URL `widgets/moad-20261102-r13/`. Aucun widget déjà publié n’est modifié. Le questionnaire conserve la version sans volet Siège en préparation.

Validation : conservation de toutes les cellules des 22 tables métier, du schéma et des autres ACL ; contrôles de l’ordre des pages ; huit scénarios de régression sur les véritables actions générées par le moteur Python et les méthodes de prunage, PermissionInfo, RecordView et compilateur TypeScript officiels. Le test reproduit exactement l’erreur avec les anciennes règles, puis vérifie la diffusion complète et confidentielle avec les nouvelles. Il couvre aussi les autres comptes, les anonymes, la création avant/après apparition de l’attribut de demande, l’usurpation et l’auto-validation refusées. Seuls le chargement de l’infrastructure et les mémos de journalisation sont simulés ; aucune session du serveur personnel n’est pilotée.

Les tests utilisent Grist au commit 2afde758fefeff32579639be58c2855804e85859. `build_grist_pruner_r13.py` construit le module à partir de ce code non modifié ; dépendances de test : esbuild, lodash et grainjs. Les fixtures et les données des documents restent privées et ne sont pas commises.

La copie livrée dérive du fichier de mise à jour 12 disponible dans la conversation. Elle ne contient pas les demandes ou saisies ajoutées ensuite sur l’instance distante ; un export courant est nécessaire pour préserver ces ajouts dans une autre copie corrigée. Aucun essai d’inscription n’est enregistré dans le fichier livré.
