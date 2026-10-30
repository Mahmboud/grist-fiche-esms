# Mise à jour 11 — sites, catégories FINESS et accueil

Le propriétaire peut désormais créer un site depuis Administration → Sauvegarde & restauration → Référentiels Sites, UGECAM et profils → Ajouter un site. Il choisit l’UGECAM, le nom de niveau 2 Airmes et, si connu, l’identifiant Airmes. Une transaction crée le site et son unique questionnaire Autodiag. Les doublons de nom dans une UGECAM, d’identifiant Airmes et les anciennes références orphelines sont contrôlés avant écriture. Les ESMS/services et leurs responsables sont ensuite rattachés au site ; la création locale ne modifie pas l’application Airmes ni l’import historique de son arborescence.

Un formulaire réservé au propriétaire permet de rattacher un ESMS/service sans site à un site de sa même UGECAM. Seul le champ SITE est modifié. Le nom, le FINESS et les réponses existantes sont conservés. Le site et le statut du FINESS sont recalculés par les formules, puis répercutés dans les projections des widgets. La fiche ESMS ne conserve pas une alerte « site à rapprocher » après ce rattachement.

La liste FINESS propose un filtre Catégorie par code et libellé effectifs, combinable avec les autres filtres et conservé lors des actualisations. Elle explique les trois cas : absence de correspondance avec les ESMS/services de la base, ESMS sans site et plusieurs sites possibles. Un FINESS juridique identifie l’UGECAM, sans déterminer son site Airmes ; le catalogue comprend aussi des structures sanitaires ou absentes de l’import Airmes.

Les trois établissements sans site du document fourni — DITEP MERCIN ET VAUX (020016655), MAS DE BEAUROUVRE (280007741) et ESRP (770510022) — sont des reprises de l’ancienne liste ESMS/FINESS. Ils restent disponibles pour rattachement explicite : aucune correspondance métier n’a été imposée automatiquement.

L’accueil reprend le titre et le paragraphe demandés sur la plateforme Grist du secteur MS UGECAM, l’expérimentation DNGU / équipe DUI, les informations d’Airmes ou de data.gouv.fr et les futurs indicateurs d’activités. Les finalités précisent le recueil des réponses à l’autodiagnostic et la mise à disposition des informations sur l’arborescence, les sites, les ESMS/services et leurs responsables. Le logo, le préremplissage, les états d’accès et la confirmation d’exactitude professionnelle sont conservés.

## Copie Grist et validation

La livraison est produite depuis l’export explicitement fourni dans la conversation, avec le moteur Grist officiel épinglé au commit 2afde758fefeff32579639be58c2855804e85859. Seules quatre URLs de widgets changent dans les métadonnées. Toutes les cellules métier, les identifiants, les schémas, les ACL et l’ordre des pages sont comparés à l’export fourni et restent inchangés. Aucun site de test ni rattachement expérimental n’est enregistré dans le fichier livré.

Validation : 34 contrôles de conservation/intégrité, 10 scénarios DOM/API simulée et 8 scénarios reliant les véritables widgets au moteur Python Grist. Les derniers vérifient la création site + questionnaire, les sélecteurs d’inscription, le rattachement d’un établissement historique, les formules FINESS, la projection nationale, la fiche affichée, les réponses préexistantes et l’absence d’export des essais. Les contrôles ACL confirment l’égalité des règles et ressources avant/après. La session du serveur personnel n’est pas pilotée.

Aucun ancien widget n’est modifié. Les nouvelles URLs sont regroupées dans `widgets/moad-20261030-r11/`. La comparaison Git montre uniquement de nouveaux fichiers par rapport à la production ; le garde-fou des 37 widgets et dépendances PROD protégés passe également.
