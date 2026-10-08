# LePalier — maquettes textuelles du lot 0 (étape 7, front)

Version 3 du 6 octobre 2026 : revue UX appliquée (B1 à B4, M1 à M14), décisions de Youssef intégrées (Q1 à Q10),
textes N1 à N27 validés sous réserve des corrections de la version 3. Constats mineurs reportés au journal du lot.
Sources : `docs/UX_CHARTE.md`, `front/CLAUDE.md`, `contracts/libelles/identity.json`, messages de `libs/commun`,
`docs/LEXIQUE.md`, recette `docs/RECETTE/lot-0.md`, ADR 0006.

Conventions :
- `[libellé : groupe.cle]` : texte déjà validé, lu dans `contracts/libelles/identity.json`, jamais recopié.
- `[commun]` : message déjà validé de `libs/commun` (401, 403, 422, 500).
- `[recette R0-xx]` : texte imposé par une ligne de recette validée.
- **⟦NOUVEAU⟧** : texte nouveau, à valider (liste complète en fin de fichier).
- **⟦API⟧** : s'appuie sur un ajout à identity décidé le 6 octobre 2026 (Q1, Q6, Q7), écrit et testé avant le front.
- Gabarits en largeur ordinateur ; la version mobile (360 px) est décrite sous chaque écran quand elle diffère.

---

## 0. Cadre commun à tous les écrans

### 0.1 Écrans hors connexion (Se connecter, Code, Activer, Mot de passe oublié, Nouveau mot de passe)
```
┌──────────────────────────────────────────────┐
│  LePalier                                    │   ← nom de l'application, jamais de logo seul
├──────────────────────────────────────────────┤
│  [bandeau de message, s'il y en a un]        │   ← role="status" (succès) ou role="alert" (erreur)
│  Titre de l'écran (24 px, h1)                │
│  …formulaire, une colonne, ≤ 72 caractères…  │
└──────────────────────────────────────────────┘
```
Pas de menu. Largeur de lecture limitée (≈ 28 rem), centrée ; même gabarit sur mobile, marges de 16 px.

### 0.2 Écrans connectés (Accueil, Administration, page réservée au gérant)
Ordinateur (UX-9, menu stable à gauche) :
```
┌───────────────┬────────────────────────────────────────────────────┐
│ LePalier      │  M. Martin · Rôle : Gérant      [ Se déconnecter ] │
│               ├────────────────────────────────────────────────────┤
│ ▸ À faire     │  [fil d'Ariane sur les pages profondes]            │
│ ▸ Administra- │  [bandeau de message]                               │
│   tion        │  Titre (h1)                                         │
│   (gérant)    │  contenu                                            │
└───────────────┴────────────────────────────────────────────────────┘
```
Mobile, et toute largeur utile inférieure à 48 rem (zoom 200 % sur un écran de 1 280 px compris) (M11) :
```
┌──────────────────────────────┐
│ LePalier     [Se déconnecter]│   ← ligne 1 : jamais coupée, bouton ≥ 44 px
│ M. Martin · Rôle : Gérant    │   ← ligne 2 : retour à la ligne permis, nom jamais tronqué (60 caractères)
├──────────────────────────────┤
│ contenu                      │
├──────────────────────────────┤
│ [▣ À faire] [⚙ Administration]│   ← « Administration » seulement pour le gérant ; icône toujours avec libellé
└──────────────────────────────┘
```
- Nom affiché et rôle toujours visibles (R0-03) ; rôle en mots du lexique : « Gérant », « Associé », « Opérateur »,
  précédé de « Rôle : » (neutre quel que soit le nom).
- « Administration » mène directement à la liste des utilisateurs (seule page d'administration au lot 0).
- Bouton « Se déconnecter » (R0-03) : bouton secondaire ; après la déconnexion, écran Se connecter avec le bandeau
  **⟦NOUVEAU⟧** « Déconnexion effectuée. » (Q4).
- Bouton « Retour » du navigateur après déconnexion : aucune page protégée ne s'affiche (R0-08) ; pages connectées
  servies sans cache (`Cache-Control: no-store`).

### 0.3 Messages et états communs (UX-4, UX-5, UX-27, UX-30)
- Bandeau en haut du contenu, avec un mot d'état et non une couleur seule, en gras sur sa propre ligne au-dessus du
  message **⟦NOUVEAU⟧** : « Fait » (résultat d'une action), « Attention » (session expirée, essais trop nombreux,
  accès suspendu, codes perdus), « Erreur » (panne). Succès : `role="status"` ; le reste : `role="alert"`.
- Erreur d'un champ : message sous le champ, lié par `aria-describedby`, focus sur le premier champ en erreur ;
  jamais une liste d'erreurs en haut seule (UX-19). Le message général [commun] « Certaines informations sont
  incorrectes. Corrigez les champs signalés. » accompagne les erreurs de champ quand il y en a plusieurs.
- Session expirée ou non reconnue (401 en cours de navigation) : le front appelle `GET /api/identity/auth/etat-session`
  ⟦API⟧ (Q1), qui répond « accès suspendu » ou, dans tous les autres cas, « session expirée ». Retour à Se connecter
  avec le bandeau « Attention » + [libellé : connexion.compte_suspendu] ou [commun] « Votre session a expiré ou n'est
  pas reconnue. Reconnectez-vous. »
- Retour à la page demandée : Se connecter reçoit `?retour=<chemin>` ; après la connexion complète (code accepté),
  le navigateur revient à ce chemin. Seuls les chemins internes de LePalier sont acceptés : le chemin commence par
  un seul « / » ; tout chemin commençant par « // » ou « /\ », toute adresse avec un schéma (`https:`,
  `javascript:`…) ou un hôte, et tout chemin vers `/connexion`, `/activation` ou `/reinitialisation` est ignoré
  (retour à l'accueil). Test dédié (vitest sur la fonction de contrôle, Playwright sur le parcours).
- Erreur inattendue (500) : bandeau « Erreur » + [commun] « Une erreur inattendue est survenue. Réessayez dans
  quelques instants. »
- Trop de demandes (429 de nginx) : « Trop de demandes en peu de temps. Patientez une minute, puis réessayez. »
  (validé au bloc C de l'étape 5).
- Bloc indisponible : « Information momentanément indisponible » (UX-30), les autres blocs restent.
- Chargement : squelette gris à la place du contenu ; bouton d'envoi désactivé pendant l'envoi, avec le texte
  **⟦NOUVEAU⟧** « Envoi en cours… » (UX-22).
- Écritures de l'administration : clé d'idempotence générée par le formulaire (UX-22). Messages possibles :
  [libellé : idempotence.cle_manquante], [libellé : idempotence.requete_en_cours], [libellé : idempotence.cle_reutilisee].

### 0.4 Champs (front/CLAUDE.md, UX-17 à UX-23)
- Libellé au-dessus du champ, aide en une phrase sous le champ (UX-15), « (facultatif) » sur l'optionnel.
- Adresse e-mail : `type="email"`, `autocomplete="username"`, `inputmode="email"`, `autocapitalize="none"`,
  `autocorrect="off"`, `spellcheck="false"`.
- Mot de passe : bouton texte « Afficher » / « Masquer » **⟦NOUVEAU⟧** (44 px), nom accessible « Afficher le mot de
  passe » / « Masquer le mot de passe », `aria-pressed` ; mêmes attributs anti-correcteur en mode texte ;
  `autocomplete="current-password"` à la connexion, `"new-password"` à l'activation et au nouveau mot de passe ;
  ~~pas de champ « confirmer »~~ remplacé (décision du 6 octobre 2026) : second champ « Confirmez le mot de passe », avec son propre bouton « Afficher » (noms accessibles « Afficher / Masquer la confirmation du mot de passe »), à l'activation et au nouveau mot de passe ; écart : « Les deux mots de passe ne sont pas identiques. Tapez le même dans les deux champs. » sous le second champ.
- Code de vérification : un seul champ, `inputmode="numeric"`, `autocomplete="one-time-code"`, jamais 6 cases ;
  espaces et tiret tolérés.
- Code de secours : `inputmode="text"`, `autocapitalize="characters"`, `autocomplete="off"` ; minuscules, espaces et
  tirets tolérés (identity normalise déjà la saisie).

### 0.5 Accessibilité et navigation (UX-8, R0-21, R0-22) (M12)
- `lang="fr"` ; `<title>` de l'onglet = « {titre de l'écran} — LePalier » ; un seul `h1` par écran.
- À chaque changement d'écran (ou d'étape à l'écran 3), le focus va sur le `h1`.
- Écrans connectés : lien d'évitement « Aller au contenu » **⟦NOUVEAU⟧**, premier élément focalisable.
- Boîtes de confirmation : focus piégé dans la boîte, placé d'abord sur « Annuler » ; Échap = « Annuler » ; à la
  fermeture, le focus revient au bouton qui l'a ouverte. Boutons de la boîte avec un verbe explicite, jamais
  « OK » ni « Continuer ».
- Copie dans le presse-papiers : confirmation dans une zone `role="status"` (« Clé copiée. » **⟦NOUVEAU⟧**).
- Clé TOTP affichée par groupes de 4, lue groupe par groupe (`aria-label` avec espaces).

---

## 1. Se connecter — `/connexion` (public)

```
LePalier

[bandeau éventuel : déconnexion, session expirée, mot de passe changé, accès suspendu, compte activé]

Se connecter

Adresse e-mail
┌──────────────────────────────────────┐
│ marie.durand@exemple.fr              │
└──────────────────────────────────────┘

Mot de passe
┌──────────────────────────────┐ [Afficher]
│ ••••••••••••••••             │
└──────────────────────────────┘
  ↳ [message d'erreur ici]

[        Se connecter        ]          ← seul bouton principal (R0-01)

Mot de passe oublié                     ← lien vers l'écran 8 (terme du libellé connexion.identifiants_incorrects)
```
- Titre et bouton : « Se connecter » (R0-01).
- Envoi : `POST /api/identity/auth/connexion`.
  - 200 → écran 2 (Code de vérification).
  - 401 → sous le champ Mot de passe : [libellé : connexion.identifiants_incorrects] ; le mot de passe est vidé,
    l'adresse est gardée (R0-24). Le message ne dit jamais si le compte existe.
  - 429 d'identity → bandeau « Attention » + [libellé : connexion.trop_d_essais] (R0-10) ; 429 de nginx → 0.3.
- Bandeaux d'arrivée possibles :
  - après déconnexion : « Fait » + « Déconnexion effectuée. » **⟦NOUVEAU⟧** ;
  - session expirée : « Attention » + [commun] 401 ;
  - après un changement de mot de passe : « Fait » + **⟦NOUVEAU⟧** « Votre mot de passe a été changé. Connectez-vous
    avec le nouveau mot de passe. » (note de l'étape 7 du plan) ;
  - accès suspendu : « Attention » + [libellé : connexion.compte_suspendu] (R0-07), dès le premier 401 après la
    suspension, grâce à `etat-session` **⟦API⟧** (Q1).
- Mobile : identique, champs pleine largeur ; le gestionnaire de mots de passe propose l'enregistrement et le
  remplissage (R0-27) grâce aux attributs `autocomplete`.
- Clavier : Adresse e-mail → Mot de passe → Afficher → Se connecter → Mot de passe oublié ; Entrée envoie.
- Recette : R0-01, R0-02, R0-07, R0-10, R0-21 à R0-27. Test e2e : connexion réussie, mot de passe faux, verrou.

## 2. Code de vérification — `/connexion/code` (pré-session `lp_pre`, 5 minutes)

```
LePalier

Code de vérification

Ouvrez votre application d'authentification et saisissez le code      ← ⟦NOUVEAU⟧
à 6 chiffres affiché pour LePalier.

Code à 6 chiffres
┌──────────────┐
│ 123 456      │
└──────────────┘
  Le code change toutes les 30 secondes : saisissez celui affiché     ← ⟦NOUVEAU⟧ (aide, M4)
  en ce moment.
  ↳ [message d'erreur ici]
  Utiliser un code de secours            ← lien ⟦NOUVEAU⟧, placé juste sous le champ et sous l'erreur (M4)

[        Se connecter        ]          ← même verbe qu'à l'écran 1 : l'action termine la connexion

Recommencer la connexion               ← lien ⟦NOUVEAU⟧ : retour à l'écran 1

Vous n'avez plus votre téléphone ni vos codes de secours ?            ← ⟦NOUVEAU⟧ (B3, texte simple)
Demandez au gérant de la SCI de réinitialiser votre accès.
```
Mode code de secours : la consigne devient « Saisissez l'un des codes de secours que vous avez notés ou imprimés à l'activation de votre compte. » (revue UX M1, 8 octobre 2026).
Mode code de secours (après le lien) :
```
Code de secours
┌──────────────────────┐
│ ABCD-EFGH-JKMN       │
└──────────────────────┘
  Chaque code de secours ne sert qu'une fois.                          ← ⟦NOUVEAU⟧ (aide)
  Utiliser le code de l'application      ← lien ⟦NOUVEAU⟧ (retour au mode normal)
```
- Titre : « Code de vérification » (R0-02). Le champ du mode normal ouvre un clavier numérique : le lien vers le
  mode code de secours est donc placé au plus près du champ et de l'erreur, car [libellé : code.incorrect] mentionne
  les codes de secours (M4).
- Envoi : `POST /api/identity/auth/code`.
  - 200 → page demandée avant la reconnexion (`?retour=`, contrôlé : voir 0.3), sinon Accueil (écran 5).
  - 401 `code_incorrect` → sous le champ : [libellé : code.incorrect] ; champ vidé, focus dessus.
  - 401 `delai_depasse` → écran 1, bandeau « Attention » + [libellé : code.delai_depasse].
  - 401 `trop_de_codes` → écran 1, bandeau « Attention » + [libellé : code.trop_de_codes].
  - 403 `compte_suspendu` → écran 1, bandeau « Attention » + [libellé : connexion.compte_suspendu].
  - 429 → [libellé : connexion.trop_d_essais].
- Accès direct sans pré-session : retour à l'écran 1, sans message.
- Recette : R0-02, R0-03, R0-14, R0-20. Test e2e : code juste, code faux, code de secours.

## 3. Activer mon compte — `/activation#<jeton>` (lien d'invitation, public) — trois étapes (M1)

Le jeton est lu après `#` en JavaScript, puis retiré de l'adresse affichée (`history.replaceState`) ; il est
envoyé en POST à `/api/identity/auth/activation/debut` (au chargement) puis `/fin` (à la dernière étape).
Les trois étapes restent sur la même adresse et dans la mémoire de la page (rien n'est stocké ailleurs) ; le
`h1` reste « Activer mon compte », l'étape est annoncée en texte et reçoit le focus.

### En-tête commun aux trois étapes
```
LePalier

Activer mon compte

Avant de commencer : installez sur votre téléphone l'application       ← ⟦NOUVEAU⟧ (B1, bloc encadré, visible
« Google Authenticator » (gratuite, dans l'App Store ou le Play Store).    aux trois étapes)
Si vous quittez cette page pour l'installer, rouvrez simplement le lien
de l'e-mail : vous reprendrez ici.
  ▸ Autres applications possibles        ← dépliable ⟦NOUVEAU⟧ : Microsoft Authenticator, FreeOTP

Votre adresse de connexion : marie.durand@exemple.fr                    ← ⟦NOUVEAU⟧ ⟦API⟧ (M2, Q6) ; champ en
                                                                           lecture seule, autocomplete="username"
Étape 1 sur 3 : votre nom                                               ← ⟦NOUVEAU⟧
```
L'adresse vient de la réponse de `activation/debut` **⟦API⟧** (Q6).

### Étape 1 sur 3 : votre nom
```
Nom affiché
┌────────────────────────────┐
│ Mme Durand                 │       ← pré-rempli avec le nom donné par le gérant, modifiable (ADR 0006)
└────────────────────────────┘
  Le nom que verront les autres utilisateurs de LePalier.            ← ⟦NOUVEAU⟧ (aide)
  ↳ [libellé : nom_affiche.invalide], vérifié à la sortie du champ (60 caractères, pas de « @ »)

[ Continuer ]                                                        ← ⟦NOUVEAU⟧
```
### Étape 2 sur 3 : votre mot de passe
```
Mot de passe
┌──────────────────────────────┐ [Afficher]
│                              │       ← autocomplete="new-password"
└──────────────────────────────┘
  Au moins 12 caractères. Une phrase de plusieurs mots est plus       ← ⟦NOUVEAU⟧ (aide, M13)
  facile à retenir, par exemple « le chat dort sur le toit ».
  Touchez « Afficher » pour vérifier ce que vous avez tapé.            ← mot de passe masqué par défaut (Q9) ;
                                                                         point à observer au test utilisateur
  ↳ longueur (12 à 128) vérifiée à la sortie du champ ; les autres motifs, par le serveur à l'envoi final

Confirmez le mot de passe                                            ← décision du 6 octobre 2026
┌──────────────────────────────┐ [Afficher]
│                              │       ← autocomplete="new-password"
└──────────────────────────────┘
  ↳ « Les deux mots de passe ne sont pas identiques. Tapez le même dans les deux champs. » (sortie du champ et
    « Continuer » ; curseur dans ce champ) ; après un 422 du serveur, les deux champs sont vidés

[ Continuer ]                 Étape précédente                        ← ⟦NOUVEAU⟧ (lien)
```
### Étape 3 sur 3 : votre application d'authentification
```
Ajoutez LePalier à votre application d'authentification :              ← ⟦NOUVEAU⟧
  • sur ce téléphone : touchez « Ajouter à mon application » ;
  • sur un ordinateur ou une tablette : scannez ce code avec votre téléphone.

  [ Ajouter à mon application ]       ← lien otpauth:// (bouton secondaire, en premier sur un téléphone) ⟦NOUVEAU⟧
  Si rien ne s'ouvre, l'application n'est pas encore installée :      ← ⟦NOUVEAU⟧ (B1)
  installez-la, ou saisissez la clé ci-dessous.

  ┌───────────┐
  │  QR code  │    alt : « Code à scanner pour ajouter LePalier à votre application d'authentification »  ⟦NOUVEAU⟧
  └───────────┘

  Le code ne se scanne pas ? Saisissez cette clé dans l'application :  ← ⟦NOUVEAU⟧
  ABCD EFGH IJKL MNOP QRST UVWX YZ23 4567    [Copier la clé] ⟦NOUVEAU⟧

Code à 6 chiffres affiché par l'application                           ← ⟦NOUVEAU⟧ (libellé du champ)
┌──────────────┐
│              │
└──────────────┘
  ↳ [message d'erreur ici]

[        Activer mon compte        ]          Étape précédente          ← bouton principal ⟦NOUVEAU⟧
```
- Chargement : `activation/debut` donne le QR, le nom affiché et l'adresse (⟦API⟧, Q6) ; tant que le lien est valable,
  le même secret revient à chaque rechargement (ADR 0006) : la reprise après l'installation fonctionne (B1).
- Lien expiré, utilisé ou inconnu (410) : la page ne montre que le titre et [libellé : invitation.lien_invalide], puis « Si vous avez déjà activé votre compte, ce lien ne sert plus : connectez-vous avec votre adresse e-mail et votre mot de passe. » et le bouton « Se connecter » (revue UX B1, 8 octobre 2026) ; sans lien, le bouton « Se connecter » aussi.
- Envoi final : `POST /api/identity/auth/activation/fin`.
  - 422 nom → retour à l'étape 1, message sous le champ : [libellé : nom_affiche.invalide], focus dessus.
  - 422 mot de passe → retour à l'étape 2, message sous le champ : [libellé : mot_de_passe.<motif>], focus dessus.
  - 400 code → reste à l'étape 3 : [libellé : activation.code_incorrect].
  - 410 → état « lien invalide » ci-dessus.
  - 200 → écran 4 (Codes de secours) ; la session complète est déjà ouverte.
- Recette : R0-04 (lien), R0-05, R0-20. Test e2e : activation complète, reprise après rechargement à l'étape 3,
  lien expiré, mot de passe refusé (retour à l'étape 2).

## 4. Codes de secours — `/activation/codes` (juste après l'activation)

```
LePalier

Vos codes de secours

Si vous perdez votre téléphone, ces codes vous permettront de          ← ⟦NOUVEAU⟧ (M3)
vous connecter. Chaque code ne sert qu'une fois.
Recopiez-les sur une feuille ou imprimez-les, puis rangez-les avec
vos papiers importants. Ils ne seront plus jamais affichés.

Ne fermez pas cette page avant d'avoir noté vos codes.                ← ⟦NOUVEAU⟧ (M3, ligne visible en permanence)

  1. ABCD-EFGH-JKMN        6. …
  2. …                     7. …
  3. …                     8. …
  4. …                     9. …
  5. …                    10. …          ← police à chasse fixe, 18 px

[Imprimer]                               ← bouton secondaire ⟦NOUVEAU⟧ (« Copier les codes » retiré, M3)

☐ J'ai noté mes codes                    ← case obligatoire (ADR 0006)
  ↳ [message si on continue sans cocher]

[      Continuer vers l'accueil      ]   ← bouton principal ⟦NOUVEAU⟧
```
- Si la case n'est pas cochée (sous la case) : **⟦NOUVEAU⟧** « Cochez cette case une fois vos codes notés : ils ne
  seront plus affichés. » Le bouton reste actif ; le contrôle se fait au clic.
- Les codes ne vivent qu'en mémoire de la page. Si la page est rechargée quand même, les codes sont perdus : bandeau
  « Attention » + **⟦NOUVEAU⟧** « Vos codes de secours ne peuvent plus être affichés. Si vous ne les avez pas notés,
  demandez au gérant de réinitialiser votre accès. », puis passage à l'accueil.
- Impression : feuille sobre (UX-10) : « LePalier », titre, nom affiché, date d'édition, les 10 codes.
- À l'arrivée sur l'accueil, bandeau « Fait » + **⟦NOUVEAU⟧** « Votre compte est activé. Pour vous connecter la
  prochaine fois : votre adresse e-mail, votre mot de passe, puis le code de votre application. » (M2).
- Recette : R0-05. Test e2e : case non cochée refusée, codes absents après rechargement.

## 5. Accueil « À faire » — `/` (connecté, tous les rôles)

```
(cadre 0.2)

À faire

┌──────────────────────────────────────────────────────────────┐
│  [état vide selon le rôle]                                   │
└──────────────────────────────────────────────────────────────┘
```
État vide selon le rôle (UX-27, M9) **⟦NOUVEAU⟧** :
- Gérant et opérateur : « Rien à faire pour le moment. Les paiements à enregistrer, les relevés d'eau et les envois à
  préparer apparaîtront ici, du plus urgent au moins urgent. »
- Associé : « Rien à faire pour le moment. Vous n'avez aucune saisie à faire dans LePalier : les informations
  importantes apparaîtront ici. »
- Au lot 0, la liste est toujours vide ; pas de bouton principal (aucune action inventée).
- Chargement : squelette de 3 cartes ; erreur : « Information momentanément indisponible » (UX-30).
- Recette : R0-03. Test e2e : arrivée après connexion, nom affiché visible, déconnexion.

## 6. Administration → Utilisateurs (gérant)

### 6.1 Liste — `/administration/utilisateurs`
```
(cadre 0.2)
Administration › Utilisateurs            ← « Administration » en texte, pas un lien vers une page vide

Utilisateurs

[ Inviter une personne ]                 ← bouton principal (Q2, R0-04 reformulée)

┌──────────────┬───────────────────────────┬──────────┬─────────────────────┬────────────────┐
│ Nom          │ Adresse e-mail            │ Rôle     │ Statut              │                │
├──────────────┼───────────────────────────┼──────────┼─────────────────────┼────────────────┤
│ M. Martin    │ gerant@exemple.fr         │ Gérant   │ Accès actif         │ [Gérer l'accès]│
│ Mme Durand   │ marie.durand@exemple.fr   │ Associé  │ Invitation envoyée  │ [Gérer l'accès]│
│ M. Petit     │ paul.petit@exemple.fr     │ Opérateur│ Invitation expirée  │ [Gérer l'accès]│
└──────────────┴───────────────────────────┴──────────┴─────────────────────┴────────────────┘
```
- « Gérer l'accès » **⟦NOUVEAU⟧**, complété pour les lecteurs d'écran d'un texte masqué « de {nom} » (M8).
- Noms pour les lecteurs d'écran (A1 à A3, 7 octobre 2026) : menu « Menu principal », fil d'Ariane « Fil d'Ariane »,
  en-tête masqué de la colonne des boutons « Actions ».
- Statut : `statut_libelle` renvoyé par identity, jamais une couleur seule (UX-14) ; tri par nom.
- Mobile : une carte par personne (nom, rôle, statut) ; toute la carte est le lien vers la fiche (M8).
- Chargement : squelette ; erreur : « Information momentanément indisponible ».

### 6.2 Inviter — `/administration/utilisateurs/inviter`
```
Administration › Utilisateurs › Inviter

Inviter une personne                                               ← ⟦NOUVEAU⟧ (titre)

Nom affiché                                                        ← d'abord qui l'on invite (mineur n° 6)
┌────────────────────────────┐
└────────────────────────────┘
  Le nom que verront les autres utilisateurs. Par exemple : « Mme Durand ».   ← ⟦NOUVEAU⟧

Adresse e-mail
┌──────────────────────────────────────┐
└──────────────────────────────────────┘
  L'invitation sera envoyée à cette adresse.                       ← ⟦NOUVEAU⟧

Rôle
(•) Associé — consulte tout (appartements, baux, loyers, charges, documents, envois), exporte et commente ;
    ne modifie rien.                                                  ← Q5 : contenu du § 3.2, mots du lexique
( ) Opérateur — saisit les relevés d'eau, les paiements, les factures et les pièces, et prépare les quittances
    et les avis ; ni bail, ni envoi recommandé.
( ) Gérant — gère tout, y compris les utilisateurs.

[ Envoyer l'invitation ]   [ Annuler ]                             ← ⟦NOUVEAU⟧ ; « Annuler » (lexique), bouton secondaire
```
- Rôle « Associé » coché par défaut (UX-18).
- Chaque rôle a une seule description (Q5), écrite une fois dans `front/src/textes.ts` et reprise telle quelle aux
  boutons radio, dans la confirmation 6.2 et à l'écran 6.4 (7 octobre 2026).
- Confirmation récapitulative avant l'envoi (UX-3, B2) **⟦NOUVEAU⟧** :
  « Envoyer l'invitation à Mme Durand ?
    Adresse : marie.durand@exemple.fr        ← en grand, sans coupure au milieu
    Rôle : Associé — consulte tout (appartements, baux, loyers, charges, documents, envois), exporte et
    commente ; ne modifie rien.          ← description unique du rôle, la même qu'aux boutons radio (7 octobre 2026)
    Le lien sera valable 7 jours. »      ← sans date : la date exacte vient d'identity, dans la fiche 6.3
  Boutons : [Envoyer l'invitation] [Modifier].
- Erreurs sous les champs : [libellé : utilisateurs.email_invalide], [libellé : utilisateurs.email_deja_utilise],
  [libellé : nom_affiche.invalide].
- Succès : retour à la liste, nouvelle ligne visible, bandeau « Fait » + **⟦NOUVEAU⟧** « Invitation envoyée à
  Mme Durand (marie.durand@exemple.fr). Le lien est valable 7 jours. » (UX-4, UX-24).

### 6.3 Gérer l'accès d'une personne — `/administration/utilisateurs/<id>`
```
Administration › Utilisateurs › Mme Durand

Accès de Mme Durand                                                ← ⟦NOUVEAU⟧

Adresse e-mail : marie.durand@exemple.fr
Rôle : Associé                           [Changer le rôle]         ← ⟦NOUVEAU⟧ → écran 6.4
Statut : Invitation envoyée
Invitation envoyée le samedi 3 octobre 2026, valable jusqu'au samedi 10 octobre 2026.   ← ⟦NOUVEAU⟧ ⟦API⟧ (Q6),
  (invitation expirée : « Invitation envoyée le {date} ; le lien a expiré le {date}. Pour en envoyer un nouveau,
  touchez « Renvoyer l'invitation ». », 7 octobre 2026)
                                                                      compte invité seulement ; date en toutes lettres

Actions                                                            ← ⟦NOUVEAU⟧
[ Suspendre l'accès ]          ← si actif, jamais sur sa propre fiche               ⟦NOUVEAU⟧
[ Réactiver l'accès ]          ← si suspendu                                         ⟦NOUVEAU⟧
[ Réinitialiser l'accès ]      ← si actif seulement (M6), jamais sur sa propre fiche ⟦NOUVEAU⟧
Sur sa propre fiche, à la place de ces deux actions (7 octobre 2026) : « Vous ne pouvez ni suspendre ni réinitialiser
votre propre accès. Si c'est nécessaire, demandez-le à un autre gérant. »
[ Renvoyer l'invitation ]      ← si invité                                           ⟦NOUVEAU⟧
[ Annuler l'invitation ]       ← si invité ⟦NOUVEAU⟧ ⟦API⟧ (B2, Q7) ; refus possible :
                                  [libellé : invitation.annulation_impossible] (à valider)
```
Actions en boutons secondaires ; confirmations récapitulatives (UX-3), au neutre (M5) **⟦NOUVEAU⟧** :
- Suspendre : « Suspendre l'accès de Mme Durand ? Ce compte sera déconnecté dans les 10 secondes et ne pourra plus se
  connecter tant que vous n'aurez pas réactivé l'accès. » — [Suspendre l'accès] [Annuler].
- Réinitialiser : « Réinitialiser l'accès de Mme Durand ? Le mot de passe, les codes de secours et l'application
  d'authentification de ce compte ne fonctionneront plus. Un e-mail avec un nouveau lien, valable 7 jours, sera
  envoyé à marie.durand@exemple.fr. » (sans date, décision du 7 octobre 2026 : la date exacte vient d'identity
  dans la fiche relue) — [Réinitialiser l'accès] [Annuler].
- Annuler l'invitation : « Annuler l'invitation de Mme Durand ? Le lien envoyé à marie.durand@exemple.fr ne
  fonctionnera plus et cette personne disparaîtra de la liste. » — [Annuler l'invitation] [Garder l'invitation].
- Réactiver, renvoyer l'invitation : sans confirmation (réversibles, sans effet pour un tiers).
- Messages de succès (bandeau « Fait ») **⟦NOUVEAU⟧** : « Accès de Mme Durand suspendu. », « Accès de Mme Durand
  réactivé. », « Invitation renvoyée à Mme Durand (marie.durand@exemple.fr). Le nouveau lien est valable 7 jours ;
  l'ancien ne fonctionne plus. », « Accès de Mme Durand réinitialisé ; un e-mail lui a été envoyé. »,
  « Invitation de Mme Durand annulée. »
- Refus possibles (bandeau « Attention ») : [libellé : utilisateurs.dernier_gerant], [libellé : utilisateurs.se_suspendre],
  [libellé : utilisateurs.son_propre_acces], [libellé : utilisateurs.compte_non_active],
  [libellé : utilisateurs.acces_suspendu], [libellé : invitation.deja_activee].
- Une invitation annulée disparaît de la liste (statut `annule`, jamais affiché) ; la même adresse peut être
  invitée de nouveau (Q7, migration 0006).

### 6.4 Changer le rôle — `/administration/utilisateurs/<id>/role` (M7)
```
Administration › Utilisateurs › Mme Durand › Rôle

Changer le rôle de Mme Durand                                      ← ⟦NOUVEAU⟧

(•) Associé — consulte tout (appartements, baux, loyers, charges, documents, envois), exporte et commente ;
    ne modifie rien. (rôle actuel)                                    ← ⟦NOUVEAU⟧ « (rôle actuel) »
( ) Opérateur — saisit les relevés d'eau, les paiements, les factures et les pièces, et prépare les quittances
    et les avis ; ni bail, ni envoi recommandé.
( ) Gérant — gère tout, y compris les utilisateurs.

[ Enregistrer ]   [ Annuler ]                                      ← lexique
```
Confirmations **⟦NOUVEAU⟧** :
- Donner le rôle de gérant à une autre personne : « Donner le rôle de gérant à Mme Durand ? Ce compte pourra gérer
  tout LePalier, y compris inviter, suspendre et réinitialiser les utilisateurs. » — [Donner le rôle de gérant]
  [Annuler].
- Quitter soi-même le rôle de gérant (obligatoire, note de l'étape 7 du plan) : « Quitter le rôle de gérant ? Vous
  n'aurez plus accès à l'Administration. Un autre gérant pourra vous redonner ce rôle. » — [Quitter le rôle de
  gérant] [Annuler]. Après l'action : accueil, bandeau « Fait » + « Votre rôle est maintenant {rôle} (A8 : Associé
  ou Opérateur, 7 octobre 2026).
  L'Administration n'est plus accessible depuis ce compte. »
- « Enregistrer » sans changement (A7, 7 octobre 2026) : retour à la fiche, bandeau « Fait » + « Aucun changement :
  Mme Durand a déjà le rôle Associé. »
- Autres changements : sans confirmation. Succès : « Rôle de Mme Durand changé : Opérateur (auparavant Associé). »
- Refus : [libellé : utilisateurs.dernier_gerant].
- Recette : R0-04, R0-07. Test e2e : invitation (confirmation comprise), suspension, dernier gérant, changement de
  son propre rôle.

## 7. Page réservée au gérant — toute page d'administration ouverte par un associé ou un opérateur

```
(cadre 0.2)

Page réservée au gérant                                            ← ⟦NOUVEAU⟧ (titre)

Cette page est réservée au gérant.                                  ← [recette R0-06]
Si vous avez besoin de cette information, demandez-la au gérant     ← ⟦NOUVEAU⟧
de la SCI.

[ Retour à l'accueil ]                                              ← ⟦NOUVEAU⟧ (bouton principal, Q3)
```
- Déclenchée par le 403 de l'API (TEC-API-01) ; jamais de page blanche (R0-06).
- Recette : R0-06. Test e2e : associé sur `/administration/utilisateurs`.

## 8. Mot de passe oublié — `/mot-de-passe-oublie` (public)

```
LePalier

Mot de passe oublié

Indiquez l'adresse e-mail de votre compte. Vous recevrez un lien      ← ⟦NOUVEAU⟧
pour choisir un nouveau mot de passe.

Adresse e-mail
┌──────────────────────────────────────┐
└──────────────────────────────────────┘

[        Recevoir le lien        ]                                   ← ⟦NOUVEAU⟧

Retour à la connexion                                                ← ⟦NOUVEAU⟧ (lien)
```
- Après l'envoi (toujours 202) : le formulaire disparaît, « Adresse saisie : {adresse} » et le lien-bouton « Saisir une autre adresse », qui rouvre le formulaire avec l'adresse (revue UX M5, 8 octobre 2026) ; le bandeau affiche [libellé : reinitialisation.demande_envoyee]
  et le lien « Retour à la connexion » reste. Même affichage que le compte existe ou non (ADR 0006).
- 429 de nginx : bandeau 0.3.
- Test e2e : demande, e-mail reçu dans Mailpit.

## 9. Choisir un nouveau mot de passe — `/reinitialisation#<jeton>` (lien de l'e-mail, public)

Décision du 6 octobre 2026 : second champ « Confirmez le mot de passe » sous « Nouveau mot de passe », comme à l'activation (étape 2) ; même vérification, mêmes textes ; après un 422, les deux champs sont vidés.

Jeton lu après `#` et envoyé en POST à `/api/identity/auth/reinitialisation/fin` ; il reste dans l'adresse jusqu'à la réussite (décision du 8 octobre 2026, comme à l'activation : un rechargement garde le lien), puis il en est retiré. Sans jeton (accès à `/reinitialisation` sans le lien) : « Pour choisir un nouveau mot de passe, ouvrez le lien de l'e-mail « [LePalier] Choisir un nouveau mot de passe ». Vous ne le trouvez pas ? Faites une nouvelle demande avec « Mot de passe oublié ». » et le lien « Mot de passe oublié » (revue UX du 8 octobre 2026 ; objet de l'e-mail vérifié par un test).
```
LePalier

Choisir un nouveau mot de passe

Nouveau mot de passe
┌──────────────────────────────┐ [Afficher]
│                              │       ← autocomplete="new-password"
└──────────────────────────────┘
  Au moins 12 caractères. Une phrase de plusieurs mots est plus       ← ⟦NOUVEAU⟧ (même aide qu'à l'écran 3)
  facile à retenir. Touchez « Afficher » pour vérifier ce que vous avez tapé.

Code de vérification
┌──────────────┐
└──────────────┘
  Le code à 6 chiffres affiché en ce moment par votre application      ← ⟦NOUVEAU⟧ (aide du mode normal, M4)
  d'authentification.
  ↳ [message d'erreur ici]
  Utiliser un code de secours            ← même bascule qu'à l'écran 2 ; en mode secours, aide « Chaque code de
                                            secours ne sert qu'une fois. »

[     Changer le mot de passe     ]                                   ← ⟦NOUVEAU⟧

Vous n'avez plus votre téléphone ni vos codes de secours ?            ← ⟦NOUVEAU⟧ (B3, même texte qu'à l'écran 2)
Demandez au gérant de la SCI de réinitialiser votre accès.
```
- 204 → écran 1 avec le bandeau « Fait » + « Votre mot de passe a été changé. Connectez-vous avec le nouveau mot de
  passe. » **⟦NOUVEAU⟧**.
- 422 → sous Nouveau mot de passe : [libellé : mot_de_passe.<motif>], focus dessus ; le code est vidé, car il aura
  souvent changé avant le nouvel envoi (un mot de passe refusé ne consomme pourtant pas le code : comportement testé dans identity).
- 400 → sous le code : [libellé : code.incorrect] ; le mot de passe est gardé, seul le code est vidé ; au 5e code
  faux, la page montre seulement [libellé : reinitialisation.trop_de_codes].
- 410 (lien expiré, utilisé ou compte suspendu) : la page montre seulement [libellé : reinitialisation.lien_invalide],
  avec un lien « Mot de passe oublié ».
- 429 d'identity (verrou par compte et adresse) : [libellé : connexion.trop_d_essais].
- Test e2e : changement réussi, lien expiré, code faux.

---

## Textes nouveaux à valider (⟦NOUVEAU⟧)

| # | Écran | Texte |
| --- | --- | --- |
| N1 | 0.3 | Mots d'état des bandeaux, en gras sur leur ligne : « Fait », « Attention », « Erreur » |
| N2 | 0.3 | « Envoi en cours… » (bouton pendant l'envoi) |
| N3 | 0.4 | « Afficher » / « Masquer » ; noms accessibles « Afficher le mot de passe » / « Masquer le mot de passe » |
| N4 | 0.2, 1 | « Déconnexion effectuée. » |
| N5 | 0.5 | « Aller au contenu », « Clé copiée. » |
| N6 | 1, 9 | « Votre mot de passe a été changé. Connectez-vous avec le nouveau mot de passe. » |
| N7 | 2 | « Ouvrez votre application d'authentification et saisissez le code à 6 chiffres affiché pour LePalier. » |
| N8 | 2 | « Code à 6 chiffres », « Le code change toutes les 30 secondes : saisissez celui affiché en ce moment. » |
| N9 | 2, 9 | « Utiliser un code de secours » / « Utiliser le code de l'application » / « Recommencer la connexion » ; « Code de secours », « Chaque code de secours ne sert qu'une fois. » |
| N10 | 2, 9 | « Vous n'avez plus votre téléphone ni vos codes de secours ? Demandez au gérant de la SCI de réinitialiser votre accès. » |
| N11 | 3 | Bloc « Avant de commencer… » (application recommandée et reprise), « Autres applications possibles » |
| N12 | 3 | « Votre adresse de connexion : {adresse} » (⟦API⟧) ; « Étape {n} sur 3 : votre nom / votre mot de passe / votre application d'authentification » ; « Continuer », « Étape précédente », « Activer mon compte » |
| N13 | 3, 6.2 | Aide du nom affiché : « Le nom que verront les autres utilisateurs de LePalier. » / « … Par exemple : « Mme Durand ». » |
| N14 | 3, 9 | Aide du mot de passe : « Au moins 12 caractères. Une phrase de plusieurs mots est plus facile à retenir, par exemple « le chat dort sur le toit ». Touchez « Afficher » pour vérifier ce que vous avez tapé. » |
| N15 | 3 | Consigne de l'étape 3, « Ajouter à mon application », « Si rien ne s'ouvre… », alt du QR, « Le code ne se scanne pas ? Saisissez cette clé dans l'application : », « Copier la clé », « Code à 6 chiffres affiché par l'application » |
| N16 | 4 | Titre « Vos codes de secours », consigne (4 lignes), « Ne fermez pas cette page avant d'avoir noté vos codes. » |
| N17 | 4 | « Imprimer », « J'ai noté mes codes » (ADR 0006), « Continuer vers l'accueil », « Cochez cette case une fois vos codes notés : ils ne seront plus affichés. » |
| N18 | 4 | « Vos codes de secours ne peuvent plus être affichés. Si vous ne les avez pas notés, demandez au gérant de réinitialiser votre accès. » |
| N19 | 4 → 5 | « Votre compte est activé. Pour vous connecter la prochaine fois : votre adresse e-mail, votre mot de passe, puis le code de votre application. » |
| N20 | 5 | États vides selon le rôle (gérant et opérateur ; associé) |
| N21 | 6.1 | « Inviter une personne », « Gérer l'accès » (+ « de {nom} » pour les lecteurs d'écran) |
| N22 | 6.2 | Aide de l'adresse, descriptions des trois rôles, « Envoyer l'invitation », confirmation récapitulative, « Modifier », message de succès |
| N23 | 6.3 | « Accès de {nom} », « Actions », libellés des 5 actions, 3 confirmations, « Garder l'invitation », 5 messages de succès |
| N24 | 6.4 | « Changer le rôle de {nom} », « (rôle actuel) », 2 confirmations, « Donner le rôle de gérant », « Quitter le rôle de gérant », 2 messages de succès |
| N25 | 7 | « Page réservée au gérant », « Si vous avez besoin de cette information, demandez-la au gérant de la SCI. », « Retour à l'accueil » |
| N26 | 8 | Consigne, « Recevoir le lien », « Retour à la connexion » |
| N27 | 9 | « Choisir un nouveau mot de passe », aide du code, « Changer le mot de passe » |

## Décisions du 6 octobre 2026

- **Q1** : option (a), route `GET /auth/etat-session` d'identity ; seul « accès suspendu » est distingué, tout le
  reste reçoit la réponse « session expirée ».
- **Q2** : « Inviter une personne » ; R0-04 reformulée.  **Q3** : « Retour à l'accueil ».  **Q4** : « Déconnexion
  effectuée. ».
- **Q6** : adresse dans `activation/debut` ; dates d'envoi et de fin de validité de l'invitation dans la fiche.
- **Q7** : action « Annuler l'invitation », statut `annule` (migration 0006), adresse réutilisable.
- **Q8** : termes et règle « compte / accès » ajoutés au lexique.
- **Q9** : mot de passe masqué par défaut, bouton « Afficher » et aide actuelle ; point à observer au test utilisateur.
- **Q10** : Google Authenticator seule nommée, les autres dans le dépliant.
- Corrections : « Vous avez 5 minutes. » retiré (écran 2) ; retour à la page demandée après une reconnexion,
  chemins internes seulement (0.3) ; « Nom affiché » avant « Adresse e-mail » (6.2).

- **Q5** : descriptions des rôles : contenu du § 3.2 de la spécification fonctionnelle, mots du lexique (règle
  ajoutée au lexique : « À l'écran, le contenu vient de la spec, les mots viennent du lexique. »).

## Constats mineurs de la revue (rappel ; reportés au journal du lot le 6 octobre 2026)

1. Bandeaux : préfixe en gras sur sa ligne pour éviter « Erreur : Une erreur… » (appliqué en 0.3, reste à vérifier à l'écran).
2. `connexion.trop_d_essais` : afficher l'heure à côté du délai relatif (« vers 14 h 35 ») — texte validé inchangé.
3. Écran 2 : tolérance des minuscules, espaces et tirets dans les codes de secours (déjà assurée par identity).
4. Écran 4 : ajouter sur la feuille imprimée « Chaque code ne sert qu'une fois : barrez-le après usage ».
5. Écran 6.1 : « Administration » du menu mène directement à Utilisateurs (repris en 0.2).
6. Écran 6.2 : « Nom affiché » avant « Adresse e-mail » (on dit d'abord qui l'on invite).
7. Écran 6.2 : succès « …Elle part dans quelques instants » si l'envoi est en attente (accord à revoir).
8. Écran 6.3 : afficher la date d'envoi et la fin de validité de l'invitation (lié à Q6).
9. Écran 7 : titre et première phrase redondants (phrase imposée par R0-06, acceptable).
10. Écran 8 : rappeler l'adresse saisie sous le bandeau après l'envoi.
11. Écran 9 : champ `username` caché ou en lecture seule pour le gestionnaire de mots de passe (lié à Q6).
12. Cadre 0.2 : menu du bas à une seule entrée pour l'associé et l'opérateur, gardé pour la stabilité.
13. Cadre 0.2 : « Rôle : Associé » plutôt que « Mme Durand · Associé » (appliqué).
14. Écran 5 : « Liste à jour au mardi 6 octobre 2026 » sous le titre.
15. Écran 6.2 : « Annuler » en bouton secondaire de 44 px (appliqué).

## Checklist de sortie (§ 8), après correctifs

| Case | État |
| --- | --- |
| Titre = la tâche ; un seul bouton principal ; chemin de retour évident | Couvert (étapes et « Étape précédente » à l'écran 3, retour à l'accueil après le changement de son propre rôle) |
| Tous les mots sont dans le lexique ou y ont été ajoutés | Non couvert : ajouts proposés en Q8 |
| Messages de succès et d'erreur rédigés et testés | Rédigés (N1 à N27) ; R0-07 dépend de Q1 ; « testés » : à l'étape de code (Playwright) |
| Confirmation récapitulative sur les actions irréversibles | Couvert (invitation, suspension, réinitialisation, annulation, rôle de gérant) ; annulation d'invitation dépend de Q7 |
| Formats fr-FR des montants et dates ; définitions des indicateurs | Dates en toutes lettres (confirmations) ; pas de montant ni d'indicateur au lot 0 |
| États vide, chargement, erreur de service, droits insuffisants dessinés | Couvert |
| Clavier seul, lecteur d'écran, zoom 200 %, mobile 360 px | Spécifié (0.2, 0.5) ; vérifiable seulement sur le code (R0-20 à R0-25) |
| Test Playwright du parcours ; recette manuelle ; cas d'ergonomie dans la recette | Tests e2e listés par écran ; lignes de recette à ajouter : annulation d'invitation, changement de rôle, zoom sur les écrans connectés |

## Test utilisateur proposé (protocole § 7, un associé, tablette et téléphone personnels)

1. **Activer son compte** : « Youssef vous a envoyé hier un message pour que vous puissiez suivre la gestion de
   l'immeuble. Faites ce qu'il faut pour pouvoir y entrer, et prenez vos précautions pour le jour où vous n'auriez
   plus votre téléphone. » — Réussite : compte activé, codes recopiés ou imprimés. À observer : installation de
   l'application et retour à la page, compréhension des codes de secours, temps total (< 10 minutes).
2. **Revenir le lendemain** : « Nous sommes le lendemain. Retournez voir s'il y a quelque chose que vous devez faire
   en ce moment pour l'immeuble, puis faites en sorte que la prochaine personne qui prendra cette tablette ne puisse
   pas y entrer à votre place. » — Réussite : connexion complète, état vide compris, déconnexion.
3. **Une page réservée, puis un oubli** : « Vous voulez savoir qui d'autre peut utiliser cet outil. Essayez. Ensuite,
   imaginez que vous avez oublié votre mot de passe : faites le nécessaire pour en avoir un nouveau. » — Réussite :
   page réservée comprise sans inquiétude, nouveau mot de passe obtenu, reconnexion.

Critères (§ 7.5) : ≥ 90 % des tâches réussies seules, aucune abandonnée, SUS ≥ 70 ; un échec sur les codes de secours
(tâche 1) ou sur le nouveau mot de passe (tâche 3) est bloquant.
