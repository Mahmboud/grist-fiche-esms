# Mise à jour 10 — accueil et suivi des accès

La page Bienvenue / Mon accès est placée en premier, avant les pages réservées aux propriétaires. Administration est déplacée en dernier. Grist détermine sa page par défaut à partir de la première page visible (`DocInfoRec.newDefaultViewId`) ; l’ordre antérieur plaçait Administration en premier, exposant un écran de widgets censurés aux éditeurs. La disposition de Bienvenue contient une seule section, sans volet personnalisé replié. Une URL pointant explicitement sur une autre page conserve sa destination.

Après validation, l’accueil affiche une confirmation « Votre demande d’accès a été validée », le professionnel, l’UGECAM, le profil et le périmètre Autodiag. Le formulaire disparaît. Une vérification au changement des données et toutes les quinze secondes permet de passer de l’attente à la validation sans rechargement ; les rafraîchissements ne réinitialisent pas les saisies d’un formulaire en cours. La règle de création de DEMANDES_ACCES interdit aussi une nouvelle demande lorsque l’attribut utilisateur indique déjà Validé. Les autres droits restent inchangés.

Une présentation explique l’expérimentation menée par la DNGU et l’équipe DUI, invite les référents ESMS à renseigner l’autodiagnostic et décrit les périmètres de consultation : site principal et responsabilités, siège de l’UGECAM, DNGU nationale. Le logo Groupe UGECAM fourni est intégré à l’identique, sans hébergement tiers, dans la nouvelle page. L’introduction reste présente pendant l’attente et après validation.

Aucune donnée métier modifiée, aucune table ajoutée ou supprimée. Le fichier est dérivé de la mise à jour 9 disponible dans la conversation et n’intègre pas les saisies ultérieures d’un serveur externe. Les identités synthétiques des tests ne sont pas enregistrées dans le fichier livré.

Vérification : moteur Grist officiel pour la copie, compilation ACL TypeScript officielle, DOM jsdom pour le formulaire, préremplissage, refus de resoumission, profils site/siège/DNGU, bascule après validation et conservation des saisies pendant la synchronisation. Le logo est comparé octet par octet à l’image fournie. Aucun test effectué dans la session personnelle du serveur utilisateur.

Déploiement par ajouts uniquement dans `widgets/moad-20261029-r10/`. La section Bienvenue utilise cette nouvelle URL ; tous les widgets antérieurs restent immuables. Le formulaire, les statuts et le logo sont regroupés dans la nouvelle page sans changer les URLs Autodiag corrigées de la mise à jour 9.
