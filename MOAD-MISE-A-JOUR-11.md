# Préparation de la mise à jour 11

Cette évolution est préparée sur une branche séparée. Aucun ancien fichier de widget n’est modifié. Elle doit être vérifiée sur le dernier export Grist de l’utilisateur avant activation : la copie de travail précédente n’est plus disponible après maintenance de l’espace temporaire et les outils de lecture Library ne sont pas exposés dans cette session. Aucun fichier Grist n’a été reconstitué à partir de données partielles.

## Ajouter un site

L’ancien panneau permettait de modifier les lignes, sans bouton de création. Le panneau préparé propose : Administration → Sauvegarde & restauration → Référentiels Sites, UGECAM et profils → Ajouter un site. Le propriétaire choisit l’UGECAM, saisit le nom de niveau 2 Airmes et, si connu, l’identifiant Airmes. Une transaction ajoute le site et son questionnaire Autodiagnostic, après vérification du schéma. La création refuse un nom identique dans la même UGECAM, un identifiant Airmes déjà utilisé et une ancienne référence orpheline qui risquerait de créer deux questionnaires pour le même site. Les collisions d’identifiants font échouer la transaction entière.

Les ESMS/services sont ensuite rattachés au site et les responsables affectés depuis CONTACTS. Un formulaire séparé permet de rattacher les ESMS sans site à un site de leur même UGECAM, avec relecture préalable. Seul leur champ SITE est modifié ; le FINESS et les réponses ne sont pas remplacés. Les formules existantes recalculent les liens FINESS. Les autorisations restent réservées au propriétaire. Cette création locale ne modifie pas l’application Airmes ni l’import historique de son arborescence.

## FINESS et rattachements

Le filtre Catégorie utilise le même code et libellé effectifs que la colonne affichée, y compris la donnée publique lorsqu’elle est disponible. Il se combine avec la recherche, l’UGECAM, le secteur, le rattachement et l’activité, et conserve sa sélection lors des actualisations.

Les FINESS publics sont identifiés par le FINESS juridique de leur UGECAM ; cette correspondance ne détermine pas un site Airmes. Le catalogue comprend notamment des établissements sanitaires et des structures absentes de l’import Airmes. Le site est calculé depuis les ESMS/services portant ce FINESS, uniquement lorsqu’un site unique est établi. L’interface distingue absence de correspondance, ESMS sans site et sites multiples à arbitrer.

Les trois établissements montrés dans la capture — DITEP MERCIN ET VAUX, MAS DE BEAUROUVRE et ESRP — proviennent de la reprise de l’ancienne liste ESMS / FINESS, décrite dans la migration V4. Ils ont été conservés sans attribuer arbitrairement un site lorsqu’une correspondance unique n’était pas disponible. La nouvelle interface rappelle cette provenance et indique où les rattacher. Leur situation actuelle doit être contrôlée dans l’export courant avant toute décision métier.

## Accueil

Le titre et le paragraphe d’introduction reprennent le texte demandé sur la plateforme Grist du secteur MS UGECAM, l’expérimentation DNGU / équipe DUI, l’autodiagnostic Airmes, les informations d’Airmes ou de data.gouv.fr et l’expérimentation à venir sur les indicateurs d’activités.

Les finalités détaillent le recueil des réponses à l’autodiagnostic et l’exposition des données relatives aux établissements du Groupe UGECAM : arborescence, sites, ESMS/services, responsables et référents. Le logo, le préremplissage, les états d’accès et la confirmation d’exactitude des informations professionnelles sont conservés.

## Validation et application

Dix contrôles DOM/API simulée passent. Ils couvrent les combinaisons de filtres et leur conservation, les catégories absentes, les explications de rattachement, le nouvel accueil et ses champs conservés, la provenance des ESMS sans site, la création site + questionnaire, les doublons, l’échec de transaction sans écriture partielle, le rattachement d’un ESMS sans altérer ses autres champs et l’absence des outils pour un non-propriétaire. Les 37 widgets et dépendances de production protégés sont inchangés.

Le script `upgrade_moad_r11.py` est prêt à changer uniquement les quatre URLs concernées dans une nouvelle copie d’un export explicitement fourni, avec comparaison de toutes les cellules métier. Il n’a pas encore été exécuté sur cet export. Les contrôles du moteur Grist et de ses ACL sur la copie réelle restent donc à réaliser avant publication/activation.
