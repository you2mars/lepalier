# Charte d'ergonomie et d'accessibilité

Cette charte a la même autorité que les specs : un écran non conforme n'est pas livrable. Elle s'applique aux écrans, formulaires, messages, e-mails et documents PDF. Les règles sont numérotées (UX-n) pour être citées dans les revues et les recettes.

## 1. Pour qui l'on conçoit

| Persona | Situation | Ce qu'il faut en retenir |
| --- | --- | --- |
| Le gérant (Youssef) | Technicien, utilise l'app chaque semaine, souvent sur mobile pour saisir un relevé ou un paiement | Vitesse de saisie, raccourcis, vue d'ensemble |
| L'associé peu à l'aise | 55–75 ans, consulte quelques fois par mois pour « voir où on en est », a peur de « casser quelque chose », lit sur tablette ou ordinateur, police agrandie | Lecture seule rassurante, vocabulaire courant, aucune action irréversible possible par erreur, chiffres expliqués |
| L'opérateur occasionnel | Un proche qui aide à saisir des relevés ou des paiements, formé en 10 minutes | Un écran = une tâche guidée, confirmation claire de ce qui a été enregistré |

Règle de conception : **chaque écran doit être compréhensible par l'associé peu à l'aise sans explication orale**. Si une fonction n'y arrive pas, elle est simplifiée, pas documentée.

## 2. Principes (UX-1 à UX-10)
- **UX-1 Une tâche par écran.** Un titre qui dit ce qu'on fait (« Enregistrer un paiement »), un seul bouton principal, le reste en secondaire ou en lien.
- **UX-2 Le langage du lexique.** Mots du quotidien (`docs/LEXIQUE.md`), jamais de jargon technique (« événement », « synchronisation », « token ») ni d'anglicisme.
- **UX-3 Rien ne se perd, rien ne surprend.** Toute action irréversible (envoyer, annuler une quittance, terminer un bail) passe par une confirmation qui récapitule ce qui va se passer, avec le montant, le destinataire et la date ; les brouillons sont conservés.
- **UX-4 Toujours dire ce qui s'est passé.** Après chaque action : message visible (« Paiement de 650,00 € enregistré pour M. Martin, novembre 2026 »), et le changement d'état visible à l'écran.
- **UX-5 Une erreur = quoi, pourquoi, que faire.** « Ce montant n'a pas été enregistré : il dépasse le reste à payer (120,00 €). Saisissez 120,00 € ou moins, ou enregistrez un trop-perçu. » Jamais de code, jamais de « erreur inconnue ».
- **UX-6 Les chiffres sont lisibles et expliqués.** Montants `1 234,56 €`, dates en toutes lettres dans les phrases, chaque indicateur de tableau de bord a sa définition au survol ou en dépliant (formule du § 10.4 de la spec fonctionnelle).
- **UX-7 Mobile pour saisir, grand écran pour comprendre.** Relevé d'eau, paiement, état des lieux : saisie à une main, champs numériques avec clavier adapté, photo en un geste. Tableaux de bord et documents : ordinateur ou tablette.
- **UX-8 Accessible par défaut.** Contraste ≥ 4,5:1, police ≥ 16 px (18 px pour les montants clés), cibles ≥ 44 px, focus visible, tout faisable au clavier, libellés associés aux champs, zoom 200 % sans perte, pas d'information portée par la couleur seule.
- **UX-9 Pas de surprise de navigation.** Menu stable à gauche (ordinateur) ou en bas (mobile), fil d'Ariane sur les pages profondes, bouton « Retour » qui revient vraiment en arrière, aucune fenêtre modale pour lire.
- **UX-10 Le papier compte autant que l'écran.** Les PDF remis aux locataires sont relus comme des écrans : hiérarchie claire, montants alignés, période et date d'édition visibles, numéro de document, aucune mention technique.

## 3. Règles d'écriture (UX-11 à UX-16)
- **UX-11** Titres à l'infinitif ou au nom (« Enregistrer un paiement », « Loyers de novembre 2026 ») ; boutons avec un verbe d'action court (« Enregistrer », « Envoyer la quittance »).
- **UX-12** Phrases courtes, voix active, vouvoiement, pas de point d'exclamation, pas d'humour.
- **UX-13** Dates relatives interdites quand elles créent un doute (« hier ») ; toujours la date complète à côté.
- **UX-14** Les statuts sont des mots, pas des couleurs ni des icônes seules (« En retard depuis 12 jours »).
- **UX-15** Les messages d'aide répondent à « pourquoi on me demande ça » en une phrase, placés sous le champ.
- **UX-16** Les e-mails aux locataires : objet explicite (« Quittance de loyer — novembre 2026 — 12 rue … »), texte de 5 lignes maximum, pièce jointe nommée lisiblement (`quittance-2026-11-appartement-12.pdf`).

## 4. Formulaires (UX-17 à UX-24)
- **UX-17** Une colonne, libellés au-dessus, champ par champ, longueur du champ proportionnelle à la valeur attendue.
- **UX-18** Valeurs par défaut intelligentes (mois en cours, dernier locataire sélectionné, date du jour) toujours modifiables et visibles.
- **UX-19** Validation à la sortie du champ, message sous le champ, jamais une liste d'erreurs en haut seule.
- **UX-20** Montants : saisie avec virgule ou point acceptée, affichage normalisé `650,00 €` dès la sortie du champ.
- **UX-21** Champs numériques avec `inputmode="decimal"`, dates avec sélecteur et saisie clavier, listes longues avec recherche.
- **UX-22** Double soumission impossible (bouton désactivé + clé d'idempotence) ; un formulaire long sauvegarde un brouillon.
- **UX-23** Aucun champ obligatoire sans raison affichée ; l'optionnel est marqué « (facultatif) », pas l'inverse.
- **UX-24** Après « Enregistrer », l'écran suivant montre ce qui vient d'être créé, avec un chemin évident vers l'action suivante (« Envoyer la quittance »).

## 5. Lecture, listes et tableaux de bord (UX-25 à UX-30)
- **UX-25** L'accueil est la liste « À faire » triée par urgence, chaque ligne commençant par un verbe et portant l'échéance (« Enregistrer le relevé d'eau — avant le 5 novembre »).
- **UX-26** Les listes affichent au plus 7 colonnes sur ordinateur, 3 informations par ligne sur mobile ; le reste au dépliage.
- **UX-27** Les états vides expliquent et proposent (« Aucun paiement enregistré ce mois-ci. Enregistrer un paiement »).
- **UX-28** Chaque graphe a un titre qui énonce la conclusion (« 18 appartements sur 20 ont payé novembre »), une légende en mots, et une table de données accessible.
- **UX-29** Les tableaux de bord se lisent de haut en bas par importance : d'abord ce qui demande une action, puis les totaux, puis les tendances.
- **UX-30** Le chargement est visible (squelette) et jamais bloquant ; un bloc indisponible dit « Information momentanément indisponible » sans faire disparaître les autres.

## 6. Documents PDF et impression (UX-31 à UX-34)
- **UX-31** Gabarit unique : en-tête SCI, titre du document, période, destinataire, corps, total en gras, pied avec numéro et date d'édition.
- **UX-32** Montants en colonne alignés à droite, séparateur de milliers, deux décimales, total répété en toutes lettres sur les quittances.
- **UX-33** Taille 11 pt minimum, marges ≥ 15 mm, zone d'adresse compatible fenêtre DL.
- **UX-34** Le texte légal obligatoire est présent mais placé après l'information utile, en corps 9 pt minimum.

## 7. Protocole de test utilisateur (obligatoire à chaque lot)
1. **Participants** : au moins un associé non technicien ; idéalement deux (un sur tablette, un sur ordinateur). Jamais le développeur.
2. **Tâches** : 3 à 5 tâches réalistes du lot, formulées sans vocabulaire de l'interface (« Vérifiez si l'appartement 12 a payé son loyer de novembre »).
3. **Déroulé** : l'observateur ne guide pas ; le participant pense à voix haute ; on note pour chaque tâche : réussie seule / réussie avec aide / échouée, le temps, les hésitations, les mots que le participant emploie (à verser au lexique).
4. **Questionnaire** : SUS (10 questions, échelle 1–5) en fin de séance.
5. **Critères d'acceptation** : ≥ 90 % des tâches réussies seules, aucune erreur de saisie non détectée par l'app, SUS ≥ 70, aucune tâche abandonnée. Un échec sur une tâche de saisie de montant ou d'envoi est bloquant.
6. **Compte rendu** : section « Test utilisateur » de `docs/RECETTE/lot-N.md` : participants (initiales), date, tâches, résultats, constats, décisions.

## 8. Checklist de sortie d'un écran (à cocher dans la revue UX)
- [ ] Titre = la tâche ; un seul bouton principal ; chemin de retour évident.
- [ ] Tous les mots sont dans le lexique ou y ont été ajoutés.
- [ ] Messages de succès et d'erreur rédigés (quoi / pourquoi / que faire) et testés.
- [ ] Confirmation récapitulative sur les actions irréversibles.
- [ ] Formats fr-FR des montants et dates ; définitions des indicateurs disponibles.
- [ ] États vide, chargement, erreur de service, droits insuffisants dessinés.
- [ ] Clavier seul, lecteur d'écran sur le parcours principal, zoom 200 %, mobile 360 px.
- [ ] Test Playwright du parcours ; ligne(s) de recette manuelle ; cas d'ergonomie dans la recette.

## 9. Design system minimal
- Typographie : système (`system-ui`), corps 16 px, interligne 1,5 ; titres 24/20/18 px.
- Couleurs : neutres pour le fond et le texte (contraste AA), une couleur d'action (boutons primaires, liens), trois couleurs d'état (succès, attention, erreur) toujours accompagnées d'un mot.
- Composants : bouton primaire / secondaire / lien, champ texte, montant, date, liste déroulante avec recherche, case à cocher, tableau responsive, carte « À faire », bandeau de message, boîte de confirmation récapitulative, squelette de chargement, état vide.
- Espacement : grille de 8 px ; largeur de lecture ≤ 72 caractères ; cibles tactiles 44 px.
- Icônes : jamais seules, toujours avec un libellé.
