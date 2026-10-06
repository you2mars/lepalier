// Textes du front validés le 6 octobre 2026 (maquettes v3, N1 à N27), écrits une seule fois ici et vérifiés
// mot pour mot par textes.test.ts. Les libellés d'identity viennent de lib/libelles.ts, jamais d'ici.
export const TEXTES = {
  application: "LePalier",
  etats: { fait: "Fait", attention: "Attention", erreur: "Erreur" },
  envoiEnCours: "Envoi en cours…",
  allerAuContenu: "Aller au contenu",
  motDePasse: {
    afficher: "Afficher",
    masquer: "Masquer",
    afficherAccessible: "Afficher le mot de passe",
    masquerAccessible: "Masquer le mot de passe",
  },
  connexion: {
    titre: "Se connecter",
    adresse: "Adresse e-mail",
    motDePasse: "Mot de passe",
    bouton: "Se connecter",
    oublie: "Mot de passe oublié",
    deconnexionEffectuee: "Déconnexion effectuée.",
    motDePasseChange: "Votre mot de passe a été changé. Connectez-vous avec le nouveau mot de passe.",
  },
  code: {
    titre: "Code de vérification",
    consigne: "Ouvrez votre application d'authentification et saisissez le code à 6 chiffres affiché pour LePalier.",
    libelle: "Code à 6 chiffres",
    aide: "Le code change toutes les 30 secondes : saisissez celui affiché en ce moment.",
    libelleSecours: "Code de secours",
    aideSecours: "Chaque code de secours ne sert qu'une fois.",
    utiliserSecours: "Utiliser un code de secours",
    utiliserApplication: "Utiliser le code de l'application",
    recommencer: "Recommencer la connexion",
    sansTelephone:
      "Vous n'avez plus votre téléphone ni vos codes de secours ? Demandez au gérant de la SCI de réinitialiser votre accès.",
  },
  activation: {
    titre: "Activer mon compte",
    avantDeCommencer:
      "Avant de commencer : installez sur votre téléphone l'application « Google Authenticator » (gratuite, dans l'App Store ou le Play Store). Si vous quittez cette page pour l'installer, revenez-y ensuite : vous recommencerez au début, votre nom sera déjà rempli.",
    autresApplications: "Autres applications possibles",
    autresApplicationsListe: ["Microsoft Authenticator", "FreeOTP"],
    adresseDeConnexion: "Votre adresse de connexion :",
    etapes: [
      "Étape 1 sur 3 : votre nom",
      "Étape 2 sur 3 : votre mot de passe",
      "Étape 3 sur 3 : votre application d'authentification",
    ],
    continuer: "Continuer",
    etapePrecedente: "Étape précédente",
    bouton: "Activer mon compte",
    nomAffiche: "Nom affiché",
    aideNom: "Le nom que verront les autres utilisateurs de LePalier.",
    motDePasse: "Mot de passe",
    aideMotDePasse:
      "Au moins 12 caractères. Une phrase de plusieurs mots est plus facile à retenir, par exemple « le chat dort sur le toit ». Touchez « Afficher » pour vérifier ce que vous avez tapé.",
    consigneApplication: "Ajoutez LePalier à votre application d'authentification :",
    consigneTelephone: "sur ce téléphone : touchez « Ajouter à mon application » ;",
    consigneOrdinateur: "sur un ordinateur ou une tablette : scannez ce code avec votre téléphone.",
    ajouter: "Ajouter à mon application",
    rienNeSouvre:
      "Si rien ne s'ouvre, l'application n'est pas encore installée : installez-la, ou saisissez la clé ci-dessous.",
    altQr: "Code à scanner pour ajouter LePalier à votre application d'authentification",
    cleManuelle: "Le code ne se scanne pas ? Saisissez cette clé dans l'application :",
    copierCle: "Copier la clé",
    cleCopiee: "Clé copiée.",
    libelleCode: "Code à 6 chiffres affiché par l'application",
    // accès à /activation sans le lien de l'e-mail (décision du 6 octobre 2026) ; « lien invalide » reste au 410
    sansLien: "Pour activer votre compte, ouvrez le lien reçu dans l'e-mail d'invitation.",
  },
  codes: {
    titre: "Vos codes de secours",
    consigne: [
      "Si vous perdez votre téléphone, ces codes vous permettront de vous connecter. Chaque code ne sert qu'une fois.",
      "Recopiez-les sur une feuille ou imprimez-les, puis rangez-les avec vos papiers importants. Ils ne seront plus jamais affichés.",
    ],
    neFermezPas: "Ne fermez pas cette page avant d'avoir noté vos codes.",
    imprimer: "Imprimer",
    caseNotes: "J'ai noté mes codes",
    continuer: "Continuer vers l'accueil",
    caseNonCochee: "Cochez cette case une fois vos codes notés : ils ne seront plus affichés.",
    perdus:
      "Vos codes de secours ne peuvent plus être affichés. Si vous ne les avez pas notés, demandez au gérant de réinitialiser votre accès.",
    // feuille imprimée
    barrezApresUsage: "Chaque code ne sert qu'une fois : barrez-le après usage.",
    imprimeLe: "Imprimé le",
  },
  // repris de libs/commun (erreurs.py, identite.py) pour les cas sans réponse de l'API ; un test vérifie l'égalité
  commun: {
    erreurInattendue: "Une erreur inattendue est survenue. Réessayez dans quelques instants.",
    sessionExpiree: "Votre session a expiré ou n'est pas reconnue. Reconnectez-vous.",
    introuvable: "Cette page ou cette information n'existe pas.",
  },
  retourAccueil: "Retour à l'accueil",
} as const;
