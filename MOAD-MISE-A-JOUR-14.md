# Inscription des nouveaux professionnels

Le formulaire charge d’abord les référentiels vivants du document. Si leur lecture ne renvoie aucune ligne, il utilise un catalogue de secours enregistré dans les options de cette vue : seulement les identifiants et noms des UGECAM et sites. Ce catalogue reflète l’export utilisé pour la livraison ; il doit être renouvelé lors d’une modification de structure si le référentiel vivant reste inaccessible.

La règle de lecture de la ligne technique passe avant les règles de création et n’exige aucun contact ou demande préalable. La création utilise +C et la lecture personnelle reste distincte. Les demandes et coordonnées des autres comptes restent privées. Si aucun catalogue n’est disponible, un message remplace le formulaire incomplet.

Le fichier de migration travaille sur une nouvelle copie. Les cellules des 22 tables métier sont comparées intégralement avec l’export source. Seules les métadonnées d’accueil, deux règles ACL et les deux ordres de navigation sont modifiés. Les anciennes URL restent immuables.

Tests : compte inconnu, référentiel vivant et secours, états en attente/validé, absence totale du catalogue, périmètre des champs de secours, permissions avec le compilateur natif Grist. Pas de session sur le serveur utilisateur.
