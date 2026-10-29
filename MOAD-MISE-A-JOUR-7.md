# Mise à jour 7

Corrige l’erreur `loadMoadRefConfig is not defined` des deux widgets Autodiag : le référentiel est chargé par une URL relative du nouveau bundle immuable. Les tests résolvent le chemin complet ; charger seulement le nom de fichier avait masqué cette erreur auparavant.

Les tables SITES, UGECAM et profils techniques sont désormais refusées aux non-propriétaires par ACL. Le préfixe `GristHidden_` seul n’est pas suffisant sur toutes les versions de serveur. Les widgets obtiennent des projections calculées : sélecteurs minimaux avant inscription, profil personnel sur sa propre demande, directions et coordonnées nationales après validation. Un enregistrement technique de DEMANDES_ACCES fournit les sélecteurs, sans email ni données personnelles ; les écrans de validation continuent de filtrer le statut « À valider ».

Les sources ESMS, FINESS, faits publics et arborescence sont également réservées au propriétaire. Une projection partagée sur la table de page FINESS déjà existante les expose en lecture aux profils validés, sans duplication des gros extraits dans chaque demande. Les sections personnalisées ESMS et Airmes sont rattachées à cette table de page. Aucune restriction géographique ne s’applique à ces annuaires. Les autorisations d’écriture restent réservées au propriétaire. Les ACL Autodiagnostic et Historique sont inchangées, avec le périmètre site principal + responsabilités / siège UGECAM / DNGU nationale. Les référentiels, archives et outils administratifs restent privés.

Dans Liste ESMS, la navigation s’arrête au site : les feuilles ESMS sous chaque site sont retirées, les cartes et fiches détaillées restent disponibles. Les établissements à rapprocher restent accessibles puisqu’ils n’ont pas encore de site. La page historique Arborescence Airmes conserve sa recherche et sa vue feuilles.

Le fichier est une copie de la mise à jour 6 livrée, sans accès aux saisies ultérieures du serveur de l’utilisateur. Les données métier existantes (contacts, services, questionnaires et historique) sont comparées cellule par cellule. Identités de test uniquement dans des fixtures privées, jamais dans le fichier livré ni dans le dépôt.

Validation : moteur Python officiel Grist, compilateur ACL TypeScript officiel, DOM jsdom et export Excel rouvert. Les tests vérifient le refus des sources, l’accès national après validation, la confidentialité du profil, l’inscription sans contact préalable, les directions inter-UGECAM et l’Autodiag éditeur. Aucun test de session n’a été effectué sur le serveur personnel de l’utilisateur.

Déploiement par ajouts uniquement sous `widgets/moad-20261029-r7/`. Aucune URL antérieure ni aucun fichier de production n’est modifié. Le garde-fou des 37 fichiers de production reste obligatoire.
