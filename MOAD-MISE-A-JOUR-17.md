# Logiciels des sites et tri des UGECAM

La fiche du site affiche deux encarts, « DUI déployé » et « Autres logiciels métier », à côté du titre sur écran large et en dessous sur les petits écrans. Toutes les valeurs sélectionnées sont affichées sous forme d’étiquettes échappées. L’absence de valeur est signalée par « Non renseigné ». Les UGECAM sont triées selon les règles françaises dans la navigation de Liste ESMS PH.

Deux colonnes ChoiceList éditables sont ajoutées à GristHidden_SITES : DUI_DEPLOYE et AUTRES_LOGICIELS_METIER. Airmes est initialisé pour les 61 sites hors PACA-C et Alsace ; les 12 sites de ces deux UGECAM restent vides. Une formule de valeur par défaut, appliquée uniquement à la création, couvre les nouveaux sites et n’écrase pas une modification manuelle. Aucun autre logiciel n’est présumé.

Le propriétaire peut saisir un logiciel par ligne dans Administration > Sauvegarde & restauration > Référentiels > Sites. L’enregistrement ajoute les nouvelles valeurs au choix des colonnes, dans la même transaction que la ligne du site. Une comparaison des valeurs des listes détecte les modifications concurrentes. Les colonnes restent protégées par les ACL propriétaires existantes ; les profils validés consultent les valeurs via la projection nationale déjà utilisée. Le catalogue minimal d’inscription n’est pas enrichi de ces données.

La migration crée une copie ; les anciennes cellules métier, réponses d’autodiagnostic et règles ACL sont vérifiées inchangées. Seules deux URL de vues changent vers le nouveau répertoire immuable. Tests DOM avec API simulée pour les deux rôles et les écritures administrateur ; projection et valeurs par défaut vérifiées avec le moteur Grist officiel. Pas de validation sur une session serveur utilisateur.
