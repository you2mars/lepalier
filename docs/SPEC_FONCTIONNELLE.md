# Spécifications fonctionnelles — Gestion locative personnelle d'un immeuble de 20 lots

Oct 3, 2026 · @You2Mars

## 1. Objet, périmètre et hypothèses

Ce document spécifie une application mono-utilisateur pour gérer en autonomie la location d'une vingtaine d'appartements situés dans un même immeuble, en reprenant le socle fonctionnel relevé dans les [specs BailFacile](https://claude.ai/code/artifact/d8de0521-881c-41d0-b56f-7a2acaf60a09) et en y ajoutant ce que BailFacile ne fait pas : échéancier avec validation manuelle des paiements, suivi de l'eau par relevés, courrier papier et veille juridique.

**Hypothèses structurantes** (réponses du 3 octobre 2026) :

| Hypothèse | Valeur retenue | Conséquence sur la spec |
| --- | --- | --- |
| Propriétaire | L'immeuble appartient à une SCI soumise à l'impôt sur le revenu, représentée par son gérant ; pas de comptable | Durée du bail vide de 6 ans sauf SCI familiale (3 ans), signature par le gérant, résultat réparti entre associés (2072), exports directement reportables sur les formulaires, garde-fou fiscal intégré à l'app (§ 3.1) |
| Type de baux | Tous les lots sont loués vides (loi du 6 juillet 1989, titre I) ; l'option meublée (titre I bis) est prévue lot par lot mais désactivée, demandée à titre conservatoire | Règles de durée, dépôt de garantie, préavis, charges et inventaire portées par le type de bail de chaque location (§ 3, § 4, § 7) ; activer un meublé déclenche l'avertissement fiscal APP-SCI-05 |
| Mesure de l'eau | Compteur général unique pour l'immeuble | Pas de consommation individuelle : les relevés portent sur le compteur général et le coût est réparti par une clé fixée dans les baux ; l'app doit pouvoir basculer sur des sous-compteurs plus tard |
| Canaux d'échange | E-mail et courrier papier ; API postale (La Poste) préparée pour une v2 | Chaque document a un gabarit imprimable et un gabarit e-mail ; registre des envois ; les envois papier passent par un adaptateur dont la v1 est manuelle et la v2 l'API La Poste, recommandés compris (§ 8.3) |
| Utilisateurs | Plusieurs comptes : le gérant et les associés de la SCI, avec des rôles | Gestion des rôles et des droits, journal nominatif des actions, invitations (§ 3.2) ; toujours pas d'espace locataire |
| Patrimoine | 1 immeuble, environ 20 lots, un seul profil bailleur (la SCI) | Pas de multi-profils ni de mandataire externe dans la v1 ; structure extensible à un second immeuble |
| Interconnexions | Aucune interconnexion payante ou conventionnée en v1 ; une seule exception préparée, l'API La Poste, derrière un adaptateur désactivable | Pas de signature électronique certifiée, de paiement en ligne ni de télétransmission fiscale ; sources publiques gratuites uniquement pour la veille |

**Hors périmètre v1** : signature électronique, synchronisation bancaire, publication d'annonces et gestion des candidatures, déclaration fiscale (l'app exporte, elle ne déclare pas), colocation, bail mobilité, gestion de travaux au-delà d'une simple dépense, envoi postal par API (préparé, activé en v2).

**Conventions** : exigences numérotées `APP-<domaine>-<n°>` ; les renvois `BF-…` pointent vers les specs BailFacile. Les références légales sont données à titre d'orientation (certitude élevée sur les textes cités, à vérifier sur Légifrance avant rédaction des clauses).

## 2. Vue d'ensemble

&#91;embedded content: modules et flux · 3 chaînes, 1 sortie\]

Le référentiel alimente trois chaînes indépendantes (loyer, eau et charges, veille) ; chacune ne comporte qu'un ou deux gestes manuels, signalés sous les boîtes, et tout ce qui en sort passe par la même file d'envois puis par les archives.

## 3. Référentiel : immeuble, lots, locataires, baux

Le référentiel est une chaîne Immeuble → Lot → Location → Locataire(s), où la location porte le bail en cours et toutes les règles financières ; un lot garde l'historique de ses locations successives.

| Objet | Attributs essentiels | Règles |
| --- | --- | --- |
| Immeuble | Adresse, nombre de lots, compteur d'eau général (numéro, index de référence), total des tantièmes, zone tendue oui/non, bailleur = la SCI (§ 3.1) | Un seul immeuble en v1 ; la zone tendue conditionne le préavis réduit du locataire et l'encadrement de l'évolution du loyer à la relocation |
| Lot | Numéro, étage, surface, nombre de pièces, tantièmes (clé eau et charges), DPE (classe, date, validité), équipements, annexes (cave, parking), mode de location autorisé (vide, meublé) et liste du mobilier si meublé | La somme des tantièmes des lots = total immeuble ; un lot en classe G est bloqué à la relocation depuis le 1er janvier 2025, F en 2028, E en 2034 (loi Climat et Résilience, art. 160) ; un lot meublé doit comporter au minimum les éléments du décret n° 2015-981 |
| Location | Lot, **type de bail (vide / meublé)**, date d'effet, durée, loyer hors charges, mode de charges (provisions ou, en meublé seulement, forfait), provision ou forfait mensuel, dépôt de garantie, date de révision et IRL de référence, jour d'échéance, mode de paiement attendu, statut (en cours, préavis, terminée, archivée) | Une seule location active par lot ; terminer une location fige ses données et libère le lot ; les règles de durée, dépôt et préavis dérivent du type de bail et du bailleur personne morale (tableau ci-dessous) |
| Locataire | Civilité, nom, prénom, date de naissance, e-mail, téléphone, adresse de notification (par défaut le lot), canal préféré (e-mail, papier, les deux), accord de quittance dématérialisée | Plusieurs locataires par location (co-titulaires, conjoint ajouté par avenant) ; un seul destinataire principal pour les envois, les autres en copie |
| Garant | Identité, adresse, montant et durée de l'engagement, acte de caution joint | Facultatif ; destinataire de la mise en demeure en cas d'impayé |
| Pièces | Documents importés (assurance, pièces d'identité, diagnostics) avec date et date d'expiration éventuelle | Une date d'expiration alimente le calendrier (§ 7) |
| Utilisateur | Compte nominatif rattaché à la SCI, rôle, e-mail, second facteur, statut (invité, actif, suspendu) | Voir § 3.2 |

**Règles dérivées du type de bail** (bailleur personne morale) :

| Règle | Location vide | Location meublée |
| --- | --- | --- |
| Durée minimale | 6 ans (3 ans si la SCI est familiale, constituée entre parents et alliés jusqu'au 4e degré) — art. 10 et 13 de la loi de 1989 | 1 an, ou 9 mois non renouvelable pour un étudiant — art. 25-7 |
| Dépôt de garantie maximal | 1 mois de loyer hors charges — art. 22 | 2 mois de loyer hors charges — art. 25-6 |
| Préavis du locataire | 3 mois, 1 mois en zone tendue ou motif légal — art. 15 | 1 mois — art. 25-8 |
| Congé du bailleur | 6 mois avant l'échéance — art. 15 | 3 mois avant l'échéance — art. 25-8 |
| Charges | Provisions + régularisation annuelle, ou paiement sur justificatifs — art. 23 | Idem, ou forfait mensuel sans régularisation — art. 25-10 |
| Annexes propres | — | Inventaire et état détaillé du mobilier à l'entrée et à la sortie — art. 25-5 |
| Révision du loyer | IRL annuelle — art. 17-1 | IRL annuelle — art. 25-9 renvoyant à l'art. 17-1 |

**Exigences.**

- APP-REF-01 — Créer, modifier, archiver un lot ; un lot archivé reste consultable mais exclu des traitements.
- APP-REF-02 — Démarrer une location avec contrôle de cohérence selon le type de bail : lot libre, mode de location autorisé pour le lot, dépôt de garantie dans le plafond du type, DPE compatible, provision ou forfait renseigné, inventaire du mobilier présent si meublé.
- APP-REF-03 — Terminer une location : date de sortie, relevé du compteur général à la date de sortie (§ 6), inventaire de sortie si meublé, solde du dépôt de garantie, passage en archive.
- APP-REF-04 — Modifier loyer, provision, forfait ou locataires d'une location en cours uniquement par avenant daté (reprise de BF-LOC-03) ; le type de bail ne change pas en cours de location (une bascule vide ↔ meublé = nouvelle location).
- APP-REF-05 — Historiser toute modification de loyer, provision, forfait et indice (date, ancienne valeur, nouvelle valeur, motif : révision, régularisation, avenant, utilisateur).
- APP-REF-06 — Rechercher un lot ou un locataire par numéro, nom, étage, statut, type de bail.
- APP-REF-07 — Alerte si la part des loyers meublés dépasse le seuil fiscal paramétré (§ 3.1) ou si un lot meublé ne satisfait plus la liste de mobilier obligatoire.

### 3.1 Le bailleur : la SCI

La SCI est le seul profil bailleur de l'app ; ses attributs alimentent les documents (dénomination, forme, capital, siège, SIREN, RCS, gérant signataire) et sa composition sert aux exports fiscaux (associés, parts, quote-part de résultat).

- APP-SCI-01 — Fiche SCI : dénomination, adresse du siège, SIREN, gérant (identité, qualité, signature scannée), caractère familial oui/non (détermine la durée des baux vides), régime fiscal fixé à l'IR (art. 8 du CGI, résultat imposé entre les mains des associés), exercice calé sur l'année civile ; un passage à l'IS n'est pas géré par l'app, seulement signalé comme risque (APP-SCI-05).
- APP-SCI-02 — Associés : identité, adresse, nombre de parts, pourcentage, date d'entrée ; la somme des parts = capital ; l'historique des cessions est conservé.
- APP-SCI-03 — Tous les documents sont émis au nom de la SCI « représentée par son gérant » ; aucune signature au nom d'un associé.
- APP-SCI-04 — Export annuel pour la déclaration 2072 (2072-S pour une SCI à l'IR ne détenant que des immeubles nus) : recettes, charges déductibles par nature alignées sur les lignes du formulaire, résultat, quote-part de chaque associé selon ses parts à reporter sur sa déclaration 2044 ; sans comptable, l'état doit être reportable tel quel, ligne par ligne, avec le libellé officiel de chaque rubrique.
- APP-SCI-05 — Garde-fou meublé : l'option meublée est désactivée par défaut ; l'activer sur un premier lot affiche un avertissement bloquant à acquitter par un gérant. Motif : une SCI à l'IR qui loue meublé exerce une activité commerciale et relève de plein droit de l'IS si les recettes meublées dépassent 10 % des recettes totales hors taxes (tolérance administrative, BOI-IS-CHAMP-10-30). L'app calcule chaque mois cette part et alerte à partir d'un seuil paramétré (8 % par défaut). Sans comptable, ce contrôle est le seul garde-fou : avant de meubler un lot, vérifier la lecture de la tolérance sur le BOFiP ou auprès du service des impôts des entreprises. Certitude élevée sur le principe, moyenne sur le détail du calcul.

### 3.2 Utilisateurs et rôles

L'app devient multi-utilisateurs pour les associés de la SCI : un gérant qui administre, des associés qui consultent et exportent, et au besoin un opérateur de saisie, chacun avec un compte nominatif et un journal de ses actions.

| Rôle | Droits | Usage prévu |
| --- | --- | --- |
| Gérant (administrateur) | Tout : référentiel, baux, documents, paiements, envois, automatisations, utilisateurs, paramètres, suppressions logiques | Le gérant de la SCI ; au moins un compte, jamais zéro |
| Associé | Lecture de tout (lots, locations, échéancier, charges, documents, registre des envois, veille), exports, commentaires internes sur une location ; aucune écriture | Les associés non gérants |
| Opérateur | Saisie des relevés d'eau, des paiements, des factures et des pièces ; génération des documents courants (quittance, avis) ; pas de bail, pas d'avenant, pas d'envoi recommandé, pas de paramètre | Un associé qui aide à la gestion sans engager la SCI |

- APP-USR-01 — Invitation par e-mail par un gérant, activation avec mot de passe fort et second facteur obligatoire (TOTP) ; suspension et réactivation par un gérant ; un utilisateur suspendu perd l'accès immédiatement.
- APP-USR-02 — Un utilisateur peut être lié à un associé de la fiche SCI (APP-SCI-02) ; le lien n'est pas obligatoire (un tiers de confiance qui aide à la saisie peut être opérateur sans être associé).
- APP-USR-03 — Toute action modifiant une donnée ou émettant un document porte l'identité de l'utilisateur dans le journal (APP-NF-05) ; les documents affichent l'auteur dans leurs métadonnées, pas dans le PDF remis au locataire.
- APP-USR-04 — Notifications internes : un associé peut s'abonner aux événements (paiement en retard, alerte veille, régularisation émise) par e-mail hebdomadaire ou immédiat.
- APP-USR-05 — Un gérant ne peut pas retirer son propre rôle s'il est le dernier gérant ; les droits sont vérifiés côté serveur à chaque requête, jamais seulement masqués dans l'interface.
- APP-USR-06 — Les commentaires internes entre associés sont attachés à une location ou à un lot, horodatés, non modifiables après 15 minutes, jamais transmis au locataire.

## 4. Documents et modèles

L'app génère des PDF à partir de gabarits versionnés, pré-remplis avec le référentiel, dans un catalogue limité à la location vide et à la location meublée d'habitation ; chaque gabarit existe en version imprimable (adresse en fenêtre) et en version e-mail, et chaque document est émis au nom de la SCI représentée par son gérant.

| Famille | Documents | Reprise BailFacile |
| --- | --- | --- |
| Bail vide | Contrat de location vide (décret n° 2015-587, bail type annexe 1), notice d'information, état des lieux d'entrée et de sortie, acte de caution solidaire, grille de vétusté, attestation de remise du dépôt de garantie, accord pour quittances dématérialisées | § 4.1 début de location |
| Bail meublé | Contrat de location meublée (décret n° 2015-587, bail type annexe 2), notice d'information, inventaire et état détaillé du mobilier à l'entrée et à la sortie, contrôle de la liste minimale du décret n° 2015-981, état des lieux, caution, grille de vétusté, attestation de dépôt (jusqu'à 2 mois) | § 4.1 bail meublé, inventaire |
| Vie du bail | Avenant (loyer, locataire, clause, mobilier), lettre de révision annuelle, régularisation annuelle des charges avec décompte eau (hors locations au forfait), demande d'attestation d'assurance, demande d'attestation d'entretien chaudière, annonce d'un changement de gérant ou de coordonnées de la SCI | § 4.1 gestion courante |
| Loyer | Avis d'échéance, quittance, reçu partiel, attestation de loyer | § 4.1 loyer |
| Impayés | Relance simple, mise en demeure (locataire et garant), modèle de commandement de payer à transmettre au commissaire de justice | § 4.1 impayés |
| Fin de bail | Réponse à un préavis réduit, congé pour vente / reprise / motif légitime (délais 6 mois vide, 3 mois meublé), attestation de fin de bail, lettre de restitution ou de retenue sur dépôt de garantie avec décompte du mobilier manquant ou dégradé si meublé | § 4.1 résiliation |

**Exigences.**

- APP-DOC-01 — Gabarits en HTML/CSS ou équivalent, convertis en PDF/A ; chaque PDF embarque le numéro de version du gabarit et un identifiant unique.
- APP-DOC-02 — Pré-remplissage total depuis le référentiel (SCI, gérant, lot, location, locataires) ; les champs libres sont explicitement listés par gabarit (ex. motif d'un congé).
- APP-DOC-03 — Annexes au bail jointes automatiquement : notice d'information, DPE, diagnostics valides (amiante, plomb, électricité, gaz, ERP), état des lieux, et pour le meublé l'inventaire du mobilier ; blocage si un diagnostic obligatoire manque ou est périmé, ou si l'inventaire d'un meublé omet un élément de la liste minimale.
- APP-DOC-04 — État des lieux : saisie par pièce et par élément avec état et commentaire, photos jointes, génération de la sortie à partir de l'entrée avec mise en évidence des écarts (reprise de BF-EDL-04) ; en meublé, l'inventaire est un volet du même formulaire avec quantité, état et valeur indicative par meuble ; la signature reste manuscrite sur l'exemplaire imprimé.
- APP-DOC-05 — Publipostage : génération en une passe d'un même document pour tous les lots actifs (avis d'échéance du mois, demande d'assurance annuelle, régularisation), avec un PDF par destinataire et un PDF agrégé pour impression ou pour dépôt via l'adaptateur postal (§ 8.3).
- APP-DOC-06 — Tout document généré est archivé sous le lot et la location, horodaté, immuable ; une correction produit une nouvelle version, l'ancienne reste visible.
- APP-DOC-07 — Signature manuscrite scannée du gérant apposable sur les documents que la SCI émet seule (reprise de BF-CTR-08) ; les documents bilatéraux (bail, avenant, EDL, inventaire) sont signés sur papier.
- APP-DOC-08 — Mise à jour des gabarits sous contrôle : un changement de texte légal (§ 9) crée une nouvelle version, jamais une modification en place ; chaque gabarit déclare les types de bail auxquels il s'applique.

## 5. Échéancier, validation manuelle des paiements et quittances

Chaque location génère une échéance par mois ; l'avis d'échéance part automatiquement, la quittance ne part qu'après que le propriétaire a validé à la main le paiement intégral de cette échéance.

### 5.1 Objet « échéance »

| Attribut | Contenu |
| --- | --- |
| Période | Mois civil (ou prorata au jour pour le premier et le dernier mois) |
| Montants dus | Loyer hors charges, provision de charges, éventuel rappel de régularisation ou de révision, total |
| Paiements | Liste de paiements saisis : date, montant, mode (virement, chèque, espèces, prélèvement), référence, commentaire |
| Statut | `À venir` → `Émise` (avis envoyé) → `Partielle` / `Payée` / `En retard` → `Quittancée` |
| Documents liés | Avis d'échéance, reçu(s) partiel(s), quittance |

### 5.2 Règles

- APP-ECH-01 — Génération des échéances au plus tard 10 jours avant le jour d'échéance de chaque location, à partir des montants en vigueur à cette date (loyer révisé, provision ajustée).
- APP-ECH-02 — L'avis d'échéance est envoyé automatiquement selon le canal du locataire (§ 8) ; l'avis n'a pas de valeur légale obligatoire, il peut être désactivé par location.
- APP-ECH-03 — La saisie d'un paiement est toujours manuelle (relevé bancaire consulté par le propriétaire) ; aucune détection automatique.
- APP-ECH-04 — Un paiement est affecté à une échéance précise ; un paiement supérieur au reste dû propose l'affectation du surplus à l'échéance suivante ou à un arriéré.
- APP-ECH-05 — Au passage en `Payée`, la quittance est générée (loyer et charges distingués, période, date de paiement) et envoyée selon le canal ; en e-mail, seulement si l'accord de transmission dématérialisée est enregistré (art. 21 de la loi du 6 juillet 1989), sinon par courrier.
- APP-ECH-06 — Un paiement partiel produit un reçu partiel, jamais une quittance ; le solde reste visible sur l'échéance et sur le tableau de bord.
- APP-ECH-07 — Une échéance non soldée N jours après le jour d'échéance (N paramétrable, 10 par défaut) passe `En retard` ; l'app propose la relance simple, puis la mise en demeure (locataire et garant), puis le dossier pour commissaire de justice ; chaque palier reste une action du propriétaire, jamais un envoi automatique.
- APP-ECH-08 — Une quittance émise par erreur est annulée par une version corrective qui référence l'originale (pas de suppression silencieuse).
- APP-ECH-09 — Tableau de bord mensuel : pour chaque lot, montant dû, reçu, reste, statut, dernière action ; totaux immeuble ; export CSV de la période.
- APP-ECH-10 — Attestation de loyer et historique des quittances disponibles par location pour toute période.

**Cas particuliers** : premier mois proratisé au jour (reprise de « quittance proratisée » BailFacile) ; dépôt de garantie encaissé hors échéancier avec attestation de remise (1 mois en vide, 2 mois en meublé) ; paiement du garant enregistré comme paiement sur l'échéance avec mention du payeur ; location meublée au forfait de charges : la ligne « charges » de l'échéance et de la quittance porte le forfait, aucun rappel de régularisation n'est jamais ajouté (APP-CHG-07).

## 6. Eau et charges récupérables

Avec un seul compteur général, le suivi de l'eau sert à piloter la consommation de l'immeuble (dérive, fuite) et à alimenter la régularisation annuelle ; le coût est réparti entre les lots par la clé inscrite dans les baux, au prorata du temps d'occupation, jamais par consommation individuelle tant qu'il n'y a pas de sous-compteurs. Les locations meublées au forfait sont exclues du décompte remis au locataire mais restent dans la répartition pour mesurer l'écart entre forfait et coût réel.

### 6.1 Relevés et factures

| Objet | Attributs | Règles |
| --- | --- | --- |
| Relevé du compteur général | Date, index (m³), photo, auteur, motif (périodique, entrée/sortie d'un locataire, remplacement de compteur, facture) | Index strictement croissant sauf motif « remplacement » (nouvel index de référence) ; périodicité recommandée mensuelle, rappel au calendrier (§ 7) |
| Facture d'eau | Fournisseur, période facturée, index début/fin facturés, m³ facturés, part abonnement, part consommation, assainissement et taxes, montant TTC, justificatif PDF | Écart entre m³ facturés et m³ relevés sur la même période signalé au-delà d'un seuil (5 % par défaut) |
| Clé de répartition | Par lot : tantièmes (défaut), ou surface, ou nombre d'occupants déclaré | Une seule clé active par période ; tout changement est daté et doit correspondre à la clause de charges des baux |

### 6.2 Calculs

- APP-EAU-01 — Consommation de l'immeuble entre deux relevés = différence d'index ; consommation journalière moyenne affichée et comparée à la moyenne glissante des 12 derniers mois ; alerte au-delà de +30 % (seuil paramétrable) pour suspecter une fuite.
- APP-EAU-02 — Coût de l'eau d'une période = somme des factures affectées à la période ; les factures à cheval sont ventilées au jour.
- APP-EAU-03 — Part d'un lot = coût de la période × (clé du lot / total des clés des lots occupés) × (jours d'occupation / jours de la période) ; les jours de vacance d'un lot restent à la charge du propriétaire.
- APP-EAU-04 — Les relevés faits aux dates d'entrée et de sortie servent uniquement à documenter le décompte remis au locataire ; ils ne modifient pas la clé.
- APP-EAU-05 — Option sous-compteurs (v2) : si un lot possède un compteur individuel, sa part consommation = ses m³ × prix moyen du m³ de la période, la part fixe (abonnement) restant répartie par la clé ; le modèle de données prévoit dès la v1 un compteur rattachable à un lot.

### 6.3 Régularisation annuelle

- APP-CHG-01 — Toutes les charges récupérables de l'immeuble sont saisies par nature avec justificatif : eau, électricité des parties communes, entretien et nettoyage, ascenseur, espaces verts, taxe d'enlèvement des ordures ménagères, contrat d'entretien ; la liste de référence est l'annexe du décret n° 87-713 du 26 août 1987.
- APP-CHG-02 — Pour chaque location à provisions (vide, ou meublé ayant choisi les provisions), décompte annuel = somme des parts par nature (même formule qu'APP-EAU-03) moins provisions versées sur la période ; solde en faveur du locataire remboursé ou imputé, solde en faveur du bailleur réclamé.
- APP-CHG-03 — La lettre de régularisation comprend le décompte par nature, le mode de répartition et la mention de la mise à disposition des justificatifs pendant six mois (art. 23 de la loi du 6 juillet 1989) ; elle part un mois avant l'exigibilité du solde.
- APP-CHG-04 — Alerte si la régularisation d'une année n'est pas émise avant la fin de l'année civile suivante : au-delà, le locataire peut exiger un paiement étalé sur douze mois (même article, rédaction issue de la loi ALUR).
- APP-CHG-05 — Après régularisation, l'app propose une nouvelle provision mensuelle = charges réelles de l'année / 12, arrondie, appliquée aux échéances suivantes avec historisation (APP-REF-05).
- APP-CHG-06 — Simulation : avant d'émettre, afficher pour chaque lot l'écart entre provisions et réel, pour repérer une anomalie de saisie.
- APP-CHG-07 — Location meublée au forfait (art. 25-10) : aucun décompte ni régularisation n'est émis ; l'app affiche en interne l'écart entre forfait perçu et part réelle du lot et propose, à la date de révision, un forfait ajusté qui ne peut être « manifestement disproportionné » au regard des charges réelles ; le changement de forfait passe par avenant.

**Point d'attention juridique** : en immeuble sans sous-compteurs, la clé de répartition de l'eau doit figurer dans le bail et être la même pour tous les lots ; une clé « nombre d'occupants » impose de tenir à jour ce nombre par avenant ou déclaration, ce qui fragilise le calcul. Les tantièmes sont la clé la plus défendable. Certitude moyenne sur ce dernier point (pratique courante, pas de texte imposant une clé précise).

## 7. Automatisations et calendrier

Un ordonnanceur quotidien parcourt les locations et le calendrier de l'immeuble ; il envoie seul uniquement ce qui est sans risque (avis d'échéance, demande d'assurance, quittance après validation) et prépare le reste à la validation du propriétaire.

| Automatisation | Déclencheur | Action automatique | Ce qui reste manuel | Reprise BailFacile |
| --- | --- | --- | --- | --- |
| Avis d'échéance | J-10 avant le jour d'échéance | Génération et envoi (e-mail, lot d'impression ou adaptateur postal) | Rien | § 6.1 |
| Quittance | Passage d'une échéance en `Payée` | Génération et envoi | La validation du paiement | § 6.1, adaptée |
| Attestation d'assurance | Date anniversaire du bail, puis relance à +30 j sans réception | Génération et envoi de la demande | Enregistrer l'attestation reçue (date, assureur, échéance de la police) | § 6.1 |
| Révision annuelle du loyer | Date de révision du bail, dès publication de l'IRL du trimestre de référence | Calcul du nouveau loyer et lettre prête ; pour un éventuel meublé au forfait, proposition de forfait ajusté (APP-CHG-07) | Vérifier et envoyer ; application automatique à l'échéance suivante après envoi | § 6.1 |
| Régularisation des charges | Date choisie (après réception des factures annuelles) | Décompte et lettres préparés (§ 6.3) pour les locations à provisions | Vérifier la simulation, émettre | § 6.1 |
| Entretien chaudière | Annuel, si le lot a une chaudière individuelle | Demande d'attestation | Enregistrer la réponse | § 6.1 |
| Échéances de bail | Vide : 7 mois avant la fin (congé possible jusqu'à J-6 mois) ; meublé, si activé : 4 mois avant la fin (congé jusqu'à J-3 mois) | Rappel et lettre type de congé | Décider | § 6.1 préavis |
| Relevé d'eau | Mensuel | Rappel de saisie | Saisir l'index | Nouveau |
| Diagnostics et DPE | 90 jours avant expiration d'une pièce datée | Alerte | Faire refaire le diagnostic | Nouveau |
| Retards de paiement | Échéance non soldée à J+10 | Passage en `En retard`, proposition de relance | Envoyer | § 6 (absent chez BailFacile) |
| Part du meublé | Mensuel | Calcul de la part des recettes meublées dans les recettes de la SCI (0 % tant que tout est loué vide), alerte au-delà du seuil (APP-SCI-05) | Ne jamais dépasser la tolérance ; décision documentée avant d'activer un premier meublé | Nouveau |
| Export fiscal | Après clôture de l'année civile | État 2072 et quotes-parts par associé prêts (APP-SCI-04) | Reporter sur les formulaires et déclarer | Nouveau |
| Suivi postal | Quotidien, si l'adaptateur API est actif | Mise à jour des statuts d'envoi et récupération des preuves (§ 8.3) | Rien | Nouveau |

**Exigences.**

- APP-AUT-01 — Chaque automatisation est activable par location (avis, quittance, assurance) ou par immeuble (relevé, régularisation), avec un mode « générer sans envoyer » pour contrôle.
- APP-AUT-02 — Révision IRL : loyer révisé = loyer en cours × (IRL du trimestre de référence de l'année N / IRL du même trimestre de l'année N-1), arrondi au centime ; l'IRL provient d'une table maintenue par l'app à partir de la publication INSEE (§ 9), avec saisie manuelle possible ; la révision non appliquée dans l'année est perdue pour cette année (art. 17-1 de la loi du 6 juillet 1989).
- APP-AUT-03 — Un journal des exécutions enregistre, pour chaque jour, ce qui a été généré, envoyé, ignoré et pourquoi ; une automatisation en échec (SMTP indisponible) est rejouée au jour suivant sans doublon.
- APP-AUT-04 — Tableau « à faire » sur l'accueil : tâches préparées en attente de validation, triées par date limite, avec le document joint.
- APP-AUT-05 — Vue calendrier annuelle de l'immeuble (révisions, régularisation, fins de bail, diagnostics, relevés) exportable en iCal.

**Zone tendue** : si l'immeuble est déclaré en zone tendue (APP-REF), l'app applique le préavis locataire réduit à un mois et plafonne le loyer d'une nouvelle location au dernier loyer révisé, sauf exceptions documentées (décret n° 2017-1198 reconduit chaque année ; vérifier la version en vigueur à la date du bail).

## 8. Envois : e-mail et courrier papier

Tout envoi passe par une file unique qui route chaque document vers l'e-mail ou vers l'adaptateur postal selon le canal du locataire et la nature du document, et qui tient un registre opposable des envois ; l'adaptateur postal a deux implémentations interchangeables, manuelle (impression et dépôt) en v1, API La Poste en v2.

### 8.1 Routage

| Nature du document | Canal par défaut | Motif |
| --- | --- | --- |
| Avis d'échéance, quittance, reçu, attestation de loyer | Canal préféré du locataire ; quittance par e-mail seulement avec accord écrit enregistré | Art. 21 de la loi de 1989 pour la quittance dématérialisée |
| Demande d'attestation d'assurance ou d'entretien, lettre de révision, régularisation | Canal préféré, papier simple si aucun | Pas d'exigence de forme |
| Mise en demeure, congé, commandement | Papier recommandé avec accusé de réception (ou acte de commissaire de justice pour le congé) | Exigence de forme ou de preuve |
| Bail, avenant, état des lieux | Papier pour signature, puis copie PDF par e-mail | Signature manuscrite (pas de signature électronique) |

### 8.2 Exigences

- APP-ENV-01 — E-mail : envoi SMTP depuis une adresse dédiée de la SCI, objet et corps par gabarit, PDF en pièce jointe, copie archivée dans l'app ; accusé de lecture non requis.
- APP-ENV-02 — Lot d'impression (implémentation manuelle de l'adaptateur) : les documents papier d'une journée ou d'une sélection sont fusionnés en un seul PDF, page d'adresse compatible enveloppe à fenêtre (DL ou C5), avec une page de garde listant les destinataires et le niveau de service demandé (simple, suivi, recommandé AR).
- APP-ENV-03 — Registre des envois : pour chaque document, date, canal, implémentation utilisée (manuelle ou API), destinataire, niveau de service, statut (`préparé`, `déposé`, `en cours`, `distribué`, `avisé`, `retourné`, `échec`), identifiant de suivi (saisi à la main ou retourné par l'API), preuve de dépôt et accusé de réception (scannés ou récupérés par l'API).
- APP-ENV-04 — Un envoi `préparé` non passé à `déposé` sous 5 jours remonte dans le tableau « à faire » ; un envoi `échec` ou `retourné` crée une tâche.
- APP-ENV-05 — Choix du canal et du niveau de service modifiable par document au moment de l'envoi ; un recommandé ne peut être lancé que par un gérant (§ 3.2).
- APP-ENV-06 — Les e-mails sortants ne contiennent jamais de données bancaires en clair autres que l'IBAN de la SCI ; les pièces jointes sont des PDF, jamais des liens vers l'app.
- APP-ENV-07 — Adresse de destination contrôlée avant tout envoi papier : format postal français normalisé (6 lignes), code postal et commune cohérents ; un contrôle RNVP externe n'est utilisé que si l'adaptateur API est actif.

### 8.3 Adaptateur postal et API La Poste (préparé pour la v2)

L'adaptateur isole l'app du prestataire : la file d'envois ne connaît qu'un contrat (déposer un pli, suivre un pli, récupérer ses preuves), et le choix entre impression manuelle et API La Poste se fait par configuration, niveau de service par niveau de service, sans toucher au reste.

| Opération du contrat | Implémentation manuelle (v1) | Implémentation API La Poste (v2) |
| --- | --- | --- |
| Déposer un pli (PDF, destinataire, expéditeur, niveau de service, options AR) | Ajout au lot d'impression ; statut `déposé` saisi à la main avec la date et, pour un recommandé, le numéro figurant sur la preuve de dépôt | Appel API ; retour d'un identifiant d'envoi et d'un numéro de suivi ; statut `déposé` dès acceptation |
| Suivre un pli | Consultation manuelle, saisie du statut | Interrogation périodique ou webhook ; statuts normalisés vers le registre |
| Récupérer les preuves (dépôt, AR, retour) | Scan importé par l'utilisateur | Téléchargement automatique des PDF de preuve et archivage immuable sous le document |
| Estimer le coût | Grille tarifaire saisie dans les paramètres | Devis retourné par l'API avant validation |

**Offres La Poste identifiées** ([portail Okapi](https://developer.laposte.fr/), [offres API courrier](https://www.laposte.fr/entreprise-collectivites/vos-envois-facilites-avec-api), [Maileva](https://www.laposte.fr/entreprise-collectivites/maileva)) :

| Offre | Ce qu'elle couvre | Accès et coût | Usage dans l'app |
| --- | --- | --- | --- |
| API Lettre recommandée en ligne (LReL) | La Poste imprime, met sous pli, affranchit et distribue la lettre recommandée déposée via l'API, avec AR et preuves juridiques en ligne | Contrat professionnel, facturation à l'envoi | Mises en demeure, congés, régularisations contestées |
| API Courrier suivi (affranchissement) | Marques d'affranchissement de lettres suivies, facturées en fin de mois ; l'impression et la mise sous pli restent à ta charge | Contrat API Courrier suivi | Avis d'échéance et quittances papier, demandes d'attestation |
| Maileva (filiale La Poste) | Courrier simple et recommandé externalisés de bout en bout, webhooks de suivi, documents multi-destinataires | Compte Maileva, facturation à l'envoi | Alternative unique couvrant simple + recommandé ; à comparer sur le prix |
| API Suivi | Suivi d'un numéro de courrier suivi, Colissimo ou Chronopost | Clé gratuite après inscription (open data) | Mise à jour des statuts de plis déposés à la main, utilisable dès la v1 si l'inscription gratuite est acceptée |

- APP-POST-01 — Le contrat de l'adaptateur et la table de correspondance des statuts sont écrits en v1 ; l'implémentation API est un module séparé, désactivé par défaut, avec ses identifiants stockés chiffrés et jamais dans le dépôt de code.
- APP-POST-02 — Chaque pli déposé par API conserve la réponse brute du prestataire (identifiant, horodatage, coût) pour la comptabilité et les litiges.
- APP-POST-03 — Mode dégradé : si l'API est indisponible, le pli reste `préparé` et peut être basculé en implémentation manuelle sans perte ; l'inverse n'est pas possible après dépôt.
- APP-POST-04 — La lettre recommandée électronique (envoi 100 % dématérialisé, consentement préalable du destinataire particulier requis, art. L. 100 du Code des postes et des communications électroniques) reste hors périmètre ; seule la LRAR papier distribuée par le facteur est prévue.
- APP-POST-05 — Les coûts d'envoi par API sont enregistrés comme dépenses de la SCI (§ 11, exports ; § 10, tableau de bord) et rapprochés de la facture mensuelle du prestataire.

**Hors périmètre** : lettre recommandée électronique, SMS, autre prestataire postal que La Poste et ses filiales.

## 9. Veille juridique

La veille est un collecteur planifié de sources publiques gratuites qui produit deux choses : une donnée structurée (l'IRL, injectée dans la révision des loyers) et un fil d'alertes textuelles filtrées par mots-clés, que le propriétaire lit et qualifie ; l'app ne tranche jamais une question de droit.

### 9.1 Sources retenues

| Source | Accès | Usage | Fréquence |
| --- | --- | --- | --- |
| INSEE, série 001515333 (IRL métropole) | Page publique et API BDM (jeton gratuit) ; [série](https://www.insee.fr/fr/statistiques/serie/001515333) | Donnée structurée : trimestre, valeur, date de parution → table IRL de l'app | Hebdomadaire, publication attendue mi-janvier, avril, juillet, octobre ; dernière valeur connue T2 2026 = 148,37 |
| Légifrance via PISTE | [API gratuite après inscription](https://www.data.gouv.fr/dataservices/legifrance), licence ouverte 2.0, quotas | Suivi des modifications de la loi n° 89-462, du décret n° 87-713, du décret bail type n° 2015-587, du CCH (DPE, décence) | Quotidienne |
| service-public.fr | Flux RSS des fiches « Logement » et de l'actualité ; [fiche IRL](https://www.service-public.gouv.fr/particuliers/vosdroits/F13723) | Changements pratiques (préavis, dépôt de garantie, charges, encadrement) | Quotidienne |
| ANIL | Flux d'actualités publiques | Analyses et notes juridiques sur le locatif | Quotidienne |
| Journal officiel (Légifrance) | Sommaire quotidien | Décrets annuels (zones tendues, plafonnement de l'évolution des loyers) | Quotidienne |

L'inscription à PISTE est gratuite mais implique l'acceptation de CGU : à toi d'arbitrer si cela respecte ta règle « aucun accord avec un site partenaire » ; sans PISTE, les flux RSS et le JO suffisent pour le fil d'alertes, seule la détection fine des articles modifiés est perdue.

### 9.2 Chaîne de traitement

- APP-VJ-01 — Collecte planifiée, chaque source avec son connecteur, son horodatage de dernière lecture et une déduplication par URL et empreinte de contenu.
- APP-VJ-02 — Filtrage par dictionnaire de mots-clés éditable (bail, loyer, IRL, charges récupérables, dépôt de garantie, préavis, congé, DPE, décence, encadrement, zone tendue, loi de 1989, décret 87-713) avec score de pertinence ; seuls les éléments au-dessus du seuil créent une alerte.
- APP-VJ-03 — Résumé optionnel par un modèle de langage exécuté localement (aucune donnée locataire envoyée, uniquement le texte public) ; le résumé est marqué comme tel et accompagné du lien source.
- APP-VJ-04 — Chaque alerte est qualifiée par le propriétaire : `à lire`, `sans impact`, `impact gabarits` (ouvre une tâche de mise à jour de modèle, APP-DOC-08), `impact paramètres` (seuils, zone tendue, plafonds), `impact calendrier`.
- APP-VJ-05 — L'IRL ne passe jamais par le filtre textuel : la table est mise à jour depuis la donnée structurée, un écart entre deux sources (INSEE et service-public) bloque la mise à jour et crée une alerte.
- APP-VJ-06 — Journal de veille consultable par source et par période ; export des alertes qualifiées « impact » avec la date de prise en compte.

**Limites** : la veille signale, elle n'interprète pas ; une alerte « impact gabarits » doit être validée contre le texte consolidé avant modification d'un modèle ; aucune source payante (éditeurs juridiques) ni abonnement conventionné.

## 10. Tableaux de bord et statistiques

Deux tableaux de bord sont calculés depuis les seules données de l'app (référentiel, échéancier, paiements, relevés et factures, charges, documents, envois, veille) : un tableau global pour la SCI et l'immeuble, un tableau par locataire ; tout indicateur affiché est reconstructible depuis l'historique, aucune donnée externe (loyer de marché, statistiques nationales) n'y entre.

### 10.1 Principes communs

- APP-TB-01 — Périodes : mois, trimestre, année civile (exercice de la SCI), 12 mois glissants, depuis l'origine ; comparaison systématique avec la période précédente (N vs N-1) quand elle existe.
- APP-TB-02 — Filtres : lot, étage, type de bail, statut de location, locataire, catégorie de charge, canal d'envoi ; les filtres s'appliquent à tous les widgets du tableau en même temps.
- APP-TB-03 — Chaque indicateur porte sa définition, sa formule et sa source (survol ou panneau latéral) et ouvre au clic la liste des éléments qui le composent (échéances, paiements, relevés), pour vérifier un chiffre sans sortir du tableau.
- APP-TB-04 — Les agrégats sont précalculés chaque nuit et à chaque saisie qui les affecte (paiement, relevé, facture) ; les graphes sont rendus côté client depuis ces agrégats ; chaque widget s'exporte en PNG/SVG et en CSV, chaque tableau en PDF daté.
- APP-TB-05 — Accès : gérants et associés voient tout ; un opérateur voit le tableau global sans la répartition du résultat par associé ; le tableau par locataire n'est jamais exposé au locataire.
- APP-TB-06 — Personnalisation par utilisateur : ordre et masquage des widgets, seuils d'alerte (couleurs) sur les indicateurs à seuil ; les seuils par défaut sont ceux des sections précédentes (retard J+10, eau +30 %, écart facture 5 %, part meublée 8 %).
- APP-TB-07 — Un indicateur sans donnée suffisante (moins de 3 mois d'historique, aucun relevé) s'affiche « non calculable » avec la raison, jamais à zéro.

### 10.2 Tableau de bord global (SCI et immeuble)

| Domaine | Indicateurs | Graphes | Priorité |
| --- | --- | --- | --- |
| Occupation | Taux d'occupation (jours occupés / jours disponibles), lots vacants et jours de vacance, vacance financière (loyer HC théorique × jours vacants / 30), entrées et sorties sur la période, durée moyenne et médiane d'occupation, répartition des lots par type de bail, étage, nombre de pièces, classe DPE | Jauge d'occupation, courbe d'occupation sur 36 mois, frise des baux par lot (début, échéance, fenêtre de congé), barres entrées/sorties par année | v1 |
| Loyers et encaissements | Appelé, encaissé, reste dû par mois ; taux de recouvrement à J+10, J+30, J+60 ; impayés en cours (montant, nombre de lots, ancienneté) ; retard moyen et médian en jours ; loyer HC total annuel, loyer moyen au m², gain cumulé des révisions IRL ; dépôts de garantie détenus | Barres empilées appelé / encaissé / reste, courbe de recouvrement, balance âgée (0-30, 30-60, 60-90, > 90 jours), carte de chaleur lots × mois des retards, histogramme des jours de retard, courbe du loyer moyen au m² | v1 |
| Eau | Consommation mensuelle (m³), consommation journalière moyenne, m³ par lot occupé et par jour, écart relevé / facture, coût moyen du m³ (abonnement inclus), part estimée par lot selon la clé | Courbe mensuelle avec moyenne glissante 12 mois et bande d'alerte +30 %, barres relevé vs facturé par période, courbe du coût du m³ | v1 |
| Charges | Charges récupérables par nature et par exercice, provisions appelées vs réel par lot et au total, solde de régularisation par lot, part récupérable (récupérable / total des charges), évolution N vs N-1 par nature | Cascade provisions → réel → solde, barres par nature N vs N-1, barres d'écart par lot (positif/négatif), treemap des charges par nature | v1 |
| Résultat de la SCI (IR) | Recettes, charges déductibles par nature (lignes 2072), résultat foncier de l'exercice, quote-part par associé, encaissements et décaissements du mois, frais postaux | Cascade recettes → charges → résultat, courbe du cumul de l'exercice vs N-1, barres par associé | v1 (quote-parts : gérants et associés) |
| Conformité et calendrier | Lots par classe DPE et échéances d'interdiction (2028, 2034), diagnostics expirant sous 90 jours, attestations d'assurance manquantes ou expirées, révisions IRL non appliquées, régularisations en retard, baux à échéance sous 12 mois, tâches « à faire » par ancienneté | Barres par classe DPE, frise 12 mois des échéances, compteurs à seuil | v1 |
| Envois et documents | Envois par canal et par mois, coût postal mensuel (manuel ou API), recommandés en attente d'AR, taux de plis distribués, délai moyen dépôt → distribution, documents générés par type, délai moyen paiement validé → quittance envoyée | Barres empilées par canal, courbe de coût, compteurs | v2 |
| Veille | Alertes par source et par statut de qualification, délai moyen de qualification, versions de gabarits publiées suite à une alerte | Compteurs, barres par source | v2 |

### 10.3 Tableau de bord par locataire (une location)

| Bloc | Contenu | Graphes | Priorité |
| --- | --- | --- | --- |
| En-tête | Lot, type de bail, dates d'effet et d'échéance, fenêtre de congé bailleur, loyer HC, provision ou forfait, dépôt de garantie détenu, canal d'envoi, accord de quittance dématérialisée, assurance (assureur, échéance, statut), garant, co-titulaires | — | v1 |
| Solde et paiements | Solde courant (appelé − reçu), échéances avec statut et jours de retard, régularité (part des échéances soldées avant J+10), moyen de paiement habituel, paiements partiels, cumul versé depuis l'entrée | Barres mensuelles appelé / reçu, courbe du solde cumulé, carte de ponctualité (mois × années), histogramme des jours de retard | v1 |
| Loyer | Historique des révisions (date, indices, ancien et nouveau montant), loyer au m² comparé à la moyenne de l'immeuble, révision à venir et montant estimé dès l'IRL publié | Escalier du loyer dans le temps, point de comparaison au m² | v1 |
| Charges et eau | Provisions versées par exercice, part réelle estimée par la clé, soldes de régularisation passés, part d'eau estimée en m³ et en euros | Barres provisions vs réel par année, courbe de la part d'eau | v1 |
| Documents et envois | Documents par type avec version, envois avec canal et statut, recommandés et preuves, délai moyen paiement → quittance | Liste et compteurs | v1 |
| Suivi relationnel | Relances et mises en demeure envoyées, incidents déclarés, commentaires internes des associés, demandes du locataire enregistrées | Compteurs par type | v2 |
| Frise de la location | Entrée, état des lieux, avenants, révisions, régularisations, relances, préavis, sortie, restitution du dépôt | Frise chronologique à l'échelle, événements datés | v1 |
| Fin de bail (si préavis ou terminée) | Décompte de sortie, retenues justifiées, délai de restitution du dépôt (1 mois si l'état des lieux de sortie est conforme, 2 mois sinon, art. 22), régularisation finale | Cascade dépôt → retenues → restitué | v1 |

### 10.4 Définitions à figer dans le code

| Indicateur | Formule | Remarque |
| --- | --- | --- |
| Taux d'occupation | Σ jours occupés de tous les lots actifs / Σ jours de la période × nombre de lots actifs | Lots archivés exclus |
| Taux de recouvrement à J+n | Montant encaissé au plus tard n jours après l'échéance / montant appelé sur la période | Calculé à date figée pour que l'historique ne bouge pas |
| Retard d'une échéance | Date du paiement qui solde l'échéance − jour d'échéance ; non soldée = retard courant à la date du jour | Paiements partiels : date du dernier paiement |
| Vacance financière | Loyer HC du dernier bail du lot × jours vacants / 30,4 | Loyer théorique, pas une perte comptable |
| Consommation journalière | (index n − index n-1) / jours entre relevés | Remplacement de compteur : repart de l'index de pose |
| Part estimée d'un lot | Formule APP-EAU-03 appliquée à la période du tableau | Identique à celle de la régularisation |
| Régularité d'un locataire | Échéances soldées avant J+10 / échéances émises | Hors premier mois proratisé |
| Résultat foncier | Recettes encaissées − charges déductibles décaissées sur l'exercice | Comptabilité d'encaissement, cohérente avec la 2072 |

**Limites assumées.** Pas de comparaison au marché, pas de prévision (hors montant estimé de la prochaine révision), pas de score de solvabilité : un tableau ne contient que des faits reconstructibles depuis le journal, et tout chiffre affiché doit retomber au centime sur les listes qu'il résume.

## 11. Exigences non fonctionnelles

L'app tourne sur ton infrastructure, pour un seul utilisateur, avec des données de locataires qui relèvent du RGPD et des documents qui doivent rester lisibles et opposables pendant au moins dix ans.

| ID | Exigence | Détail |
| --- | --- | --- |
| APP-NF-01 | Hébergement | Auto-hébergé sur un serveur personnel ; aucune dépendance à un service tiers payant au-delà du SMTP et des sources publiques § 9, l'API La Poste restant un module optionnel (§ 8.3) |
| APP-NF-02 | Accès | Comptes nominatifs avec rôles (§ 3.2), mot de passe fort et second facteur (TOTP) obligatoire pour tous ; exposition sur Internet uniquement derrière VPN ou reverse proxy avec TLS ; verrouillage après échecs ; sessions expirées après inactivité |
| APP-NF-03 | Données personnelles | Minimisation (pas de copie de pièces d'identité au-delà de la durée du bail), registre des traitements de la SCI, purge des données d'un locataire parti après le délai de prescription (5 ans après la fin du bail, art. 7-1 de la loi de 1989 ; certitude moyenne sur le délai à retenir pour la purge, à confirmer) ; les associés n'ont accès aux données locataires que dans la limite de leur rôle |
| APP-NF-04 | Conservation des documents | PDF/A horodatés, immuables (APP-DOC-06), conservés au moins 10 ans ; sauvegarde quotidienne chiffrée hors du serveur, test de restauration trimestriel inscrit au calendrier |
| APP-NF-05 | Traçabilité | Journal applicatif de toute action modifiant un montant, un statut d'échéance, un document, un envoi ou un droit : utilisateur, horodatage, avant, après ; consultable par les gérants, exportable |
| APP-NF-06 | E-mail | SMTP authentifié sur un domaine de la SCI avec SPF, DKIM et DMARC ; pas de service d'e-mailing tiers |
| APP-NF-07 | Génération PDF | Moteur libre (HTML vers PDF) ; gabarits versionnés dans le dépôt de code ; rendu identique à l'écran et à l'impression |
| APP-NF-08 | Interface | Responsive, utilisable sur smartphone pour la saisie d'un relevé d'eau ou d'un paiement et pour l'état des lieux ; pas de mode hors ligne en v1 |
| APP-NF-09 | Exports | CSV des échéances, paiements, charges, dépenses (frais postaux compris) et flux par exercice de la SCI ; export 2072 avec répartition par associé (APP-SCI-04) ; export complet du compte (portabilité) |
| APP-NF-10 | Évolutivité | Modèle de données prêt pour un second immeuble, des sous-compteurs (APP-EAU-05), l'implémentation API de l'adaptateur postal (§ 8.3) et un éventuel espace locataire, sans migration lourde |
| APP-NF-11 | Tests | Jeux de tests sur les calculs sensibles : prorata, répartition eau, régularisation, forfait meublé, révision IRL, affectation des paiements, part des recettes meublées, contrôle des droits par rôle |
| APP-NF-12 | Secrets | Identifiants SMTP et clés API (La Poste, INSEE, PISTE) stockés chiffrés, rotation possible sans redéploiement, jamais dans le dépôt de code |

## 12. Traçabilité vers les specs BailFacile

Sur les douze domaines des [specs BailFacile](https://claude.ai/code/artifact/d8de0521-881c-41d0-b56f-7a2acaf60a09), cinq sont repris tels quels ou réduits, trois sont adaptés, quatre domaines nouveaux sont ajoutés et deux sont écartés.

| Domaine BailFacile | Décision | Où dans ce document | Ce qui change |
| --- | --- | --- | --- |
| § 2 Acteurs et rôles | Adapté | § 3.2 | Plusieurs comptes (gérant, associés, opérateur) ; pas d'espace locataire |
| § 3 Biens et tiers | Adapté | § 3, § 3.1 | Immeuble comme objet racine, tantièmes et DPE par lot, bailleur = SCI avec associés et parts |
| § 4 Documents contractuels | Réduit | § 4 | Location vide et meublée (option), inventaire du mobilier ; publipostage ajouté ; signature électronique retirée |
| § 5 État des lieux | Repris | APP-DOC-04 | Même logique entrée → sortie, inventaire intégré ; signature manuscrite |
| § 6 Gestion courante et automatisations | Adapté | § 5 et § 7 | Ajout de l'échéancier avec statut de paiement, absent chez BailFacile ; quittance conditionnée à la validation ; forfait meublé |
| § 7 Espace locataire | Écarté | — | Remplacé par le routage e-mail / papier (§ 8) |
| § 8 Mise en location | Écarté | — | Hors besoin |
| § 9 Finances | Étendu | § 10, § 6.3, APP-NF-09 | L'aperçu financier BailFacile devient un tableau de bord global (occupation, encaissements, eau, charges, résultat, conformité) et un tableau par locataire ; exports par exercice |
| § 10 Non fonctionnel | Adapté | § 11 | Auto-hébergement, rôles, 2FA, sauvegardes, RGPD, secrets |
| § 11 Exclusions | Repris avec une exception | § 1, § 8.3 | Mêmes exclusions, plus LRE et SMS ; l'envoi postal par La Poste, exclu chez BailFacile, est ici préparé derrière un adaptateur |
| Nouveau | Ajouté | § 6 | Relevés du compteur général, répartition, régularisation outillée |
| Nouveau | Ajouté | § 8 | Courrier papier, registre des envois, adaptateur postal |
| Nouveau | Ajouté | § 9 | Veille juridique et table IRL |
| Nouveau | Ajouté | § 7 | Calendrier immeuble (diagnostics, DPE, fins de bail, relevés, part du meublé) |
| Nouveau | Ajouté | § 3.1 | Fiche SCI, associés, surveillance fiscale du meublé |
| Nouveau | Ajouté | § 10.3 | Tableau de bord par locataire (solde, ponctualité, révisions, charges, frise) |

## 13. Points ouverts et décisions à prendre

Neuf décisions conditionnent le modèle de données, les gabarits ou le régime fiscal de la SCI et doivent être prises avant la première ligne de code ; les autres peuvent attendre la v2.

| # | Décision | Options | Impact |
| --- | --- | --- | --- |
| 1 | Clé de répartition de l'eau et des charges | Tantièmes (recommandé) · surface · nombre d'occupants | Clause de charges des baux, APP-EAU-03, APP-CHG-02 |
| 2 | Zone tendue de la commune | Oui / non, à vérifier dans le décret en vigueur | Préavis locataire, plafonnement du loyer à la relocation (§ 7) |
| 3 | Caractère familial de la SCI | Oui (baux vides de 3 ans) / non (6 ans) | APP-SCI-01, durée dans les gabarits de bail vide |
| 4 | Activer un jour l'option meublée | Ne pas meubler (situation actuelle, tout est loué vide) · meubler un lot en restant sous la tolérance de 10 % des recettes | APP-SCI-05 ; l'IS est écarté ; sans comptable, vérifier la tolérance sur le BOFiP avant tout premier bail meublé |
| 5 | Mode de charges d'un éventuel meublé | Provisions avec régularisation (homogène avec les lots vides) · forfait | APP-CHG-07, échéancier ; à trancher seulement si la décision 4 active l'option |
| 6 | Accord de quittance dématérialisée | Le demander à tous les locataires en place par avenant ou courrier | Routage des quittances (§ 8.1) |
| 7 | Rôles des associés | Associé lecture seule pour tous · opérateur pour un associé actif · nombre de gérants | § 3.2 |
| 8 | Offre La Poste pour la v2 | LReL + API Courrier suivi (deux contrats) · Maileva (un seul) · API Suivi gratuite seule dès la v1 | § 8.3, coût par pli, contrat |
| 9 | Utiliser l'API Légifrance (PISTE) | Oui (inscription, CGU) / non (RSS et JO seulement) | APP-VJ-01, finesse de la veille |
| 10 | Pièces conservées d'un locataire | Lesquelles, combien de temps | APP-NF-03 |
| 11 | Sous-compteurs d'eau | Rester au compteur général / programmer une installation | Active APP-EAU-05, modifie la clause de charges |
| 12 | Interface d'état des lieux et d'inventaire | Formulaire complet dès la v1 ou import d'un PDF signé | APP-DOC-04 |
| 13 | Résumé automatique de la veille | Modèle local, service distant, ou aucun | APP-VJ-03 |
| 14 | Catégories de l'export 2072 | Reprendre les rubriques officielles du formulaire de l'année ou un plan simplifié à mapper chaque année | APP-SCI-04, APP-NF-09 ; sans comptable, les rubriques officielles sont préférables |

**Hypothèses à confirmer sur les textes** (certitude élevée sauf mention) : bail vide de 6 ans pour un bailleur personne morale, 3 ans pour une SCI familiale (art. 10 et 13 loi de 1989) ; dépôt de garantie limité à un mois en vide (art. 22) et deux mois en meublé (art. 25-6) ; durée d'un an ou neuf mois étudiant en meublé (art. 25-7), préavis locataire d'un mois et congé bailleur de trois mois (art. 25-8), forfait de charges possible en meublé (art. 25-10), inventaire obligatoire (art. 25-5) et liste minimale du mobilier (décret n° 2015-981) ; quittance gratuite sur demande et transmission dématérialisée soumise à l'accord du locataire (art. 21) ; régularisation annuelle, justificatifs six mois, étalement sur douze mois si retard (art. 23) ; révision IRL perdue si non appliquée dans l'année (art. 17-1) ; charges récupérables listées par le décret n° 87-713 ; interdiction de louer les classes G depuis 2025, F en 2028, E en 2034 (loi Climat et Résilience) ; bascule à l'IS d'une SCI louant meublé au-delà de la tolérance de 10 % des recettes (BOI-IS-CHAMP-10-30, certitude moyenne sur le détail) ; délai de purge RGPD après départ du locataire (certitude moyenne, à caler sur la prescription de cinq ans).
