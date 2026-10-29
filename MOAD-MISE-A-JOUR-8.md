# Mise à jour 8 — préremplissage du formulaire

Un contact existant qui n’avait pas encore de demande d’accès perdait le préremplissage : l’identification du contact dépendait du profil technique, lui-même obtenu à travers sa demande. Le formulaire s’appuie désormais directement sur une projection personnelle de CONTACTS, sans dépendre d’une demande ou d’un profil technique préalable.

La colonne calculée `CONTACTS.MON_PROFIL_JSON` contient nom, prénom, email, fonction, UGECAM, site principal, autres sites et profil Siège/DNGU. Son ACL la réserve au propriétaire et au contact identifié par `user.droits_supp.id`. Elle est censurée sur les autres lignes, même si l’utilisateur peut consulter l’annuaire. L’identification utilise l’attribut utilisateur Grist, dont la recherche email est insensible à la casse. Le formulaire ne choisit aucune personne si aucune projection personnelle unique n’est disponible.

L’email soumis est déterminé par la valeur automatique `user.Email` de Grist ; le formulaire affiche l’email professionnel connu mais ne le fournit pas dans l’action de création. Cela préserve le contrôle de l’identité, y compris avec des différences de casse.

Seule l’URL de la section Bienvenue / Mon accès change, vers le nouveau bundle `widgets/moad-20261029-r8/`. Aucun widget existant n’est réécrit. Aucune nouvelle table, aucune donnée métier supprimée ou remplacée. Les restrictions Autodiag et les ACL des tables techniques restent inchangées.

Validation : moteur Python officiel Grist, compilateur TypeScript ACL officiel et tests DOM du formulaire. Cas couverts : contact sans demande préalable, annuaire contenant plusieurs contacts avec colonnes censurées, profil Siège, DNGU, nouvel utilisateur sans contact, demande en attente et soumission du formulaire prérempli. Les cellules préexistantes sont comparées et l’email automatique testé avec un contexte éditeur. Pas de test sur le serveur personnel de l’utilisateur.

La livraison est une copie de la mise à jour 7 disponible dans la conversation et ne contient pas d’éventuelles saisies réalisées depuis sur un serveur externe. Les fixtures d’identité sont privées et ne sont jamais enregistrées dans le fichier livré ni dans le dépôt.
