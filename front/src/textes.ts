// Textes du front validés le 6 octobre 2026 (maquettes v3, N1 à N27), écrits une seule fois ici et vérifiés
// mot pour mot par textes.test.ts. Les libellés d'identity viennent de lib/libelles.ts, jamais d'ici.
import { libelle } from "@/lib/libelles";

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
    // confirmation à la création et au changement (décision du 6 octobre 2026)
    confirmation: "Confirmez le mot de passe",
    differents: "Les deux mots de passe ne sont pas identiques. Tapez le même dans les deux champs.",
    afficherConfirmationAccessible: "Afficher la confirmation du mot de passe",
    masquerConfirmationAccessible: "Masquer la confirmation du mot de passe",
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
    // revue UX du 8 octobre 2026 (M1) : consigne du mode code de secours
    consigneSecours: "Saisissez l'un des codes de secours que vous avez notés ou imprimés à l'activation de votre compte.",
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
    // revue UX du 8 octobre 2026 (B1) : lien déjà utilisé ou expiré, chemin vers Se connecter
    dejaActive:
      "Si vous avez déjà activé votre compte, ce lien ne sert plus : connectez-vous avec votre adresse e-mail et votre mot de passe.",
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
  // écrans connectés (maquettes v3, § 0.2) ; rôles en mots du lexique (Q5)
  cadre: {
    role: "Rôle :",
    seDeconnecter: "Se déconnecter",
    aFaire: "À faire",
    administration: "Administration",
    // noms pour les lecteurs d'écran des deux zones de navigation (A1, A2 du 7 octobre 2026)
    menuPrincipal: "Menu principal",
    filAriane: "Fil d'Ariane",
  },
  // rôles en mots, écrits dans contracts/libelles/identity.json (repris par l'e-mail d'invitation)
  roles: { gerant: libelle("role.gerant"), associe: libelle("role.associe"), operateur: libelle("role.operateur") },
  // une seule description par rôle (Q5), reprise telle quelle aux boutons radio, en confirmation et au changement de rôle
  descriptionsRoles: {
    associe:
      "consulte tout (appartements, baux, loyers, charges, documents, envois), exporte et commente ; ne modifie rien",
    operateur:
      "saisit les relevés d'eau, les paiements, les factures et les pièces, et prépare les quittances et les avis ; ni bail, ni envoi recommandé",
    gerant: "gère tout, y compris les utilisateurs",
  },
  // Administration › Utilisateurs (maquettes v3, écrans 6.1 à 6.4)
  utilisateurs: {
    liste: {
      titre: "Utilisateurs",
      inviter: "Inviter une personne",
      gererAcces: "Gérer l'accès",
      // complété « de {nom} » pour les lecteurs d'écran (M8)
      gererAccesDe: "de",
      colonnes: { nom: "Nom", adresse: "Adresse e-mail", role: "Rôle", statut: "Statut", actions: "Actions" },
    },
    // écran 6.2 (N22, B) ; textes à trous remplis par lib/modele.ts
    inviter: {
      titre: "Inviter une personne",
      filAriane: "Inviter",
      nomAffiche: "Nom affiché",
      aideNom: "Le nom que verront les autres utilisateurs. Par exemple : « Mme Durand ».",
      adresse: "Adresse e-mail",
      aideAdresse: "L'invitation sera envoyée à cette adresse.",
      role: "Rôle",
      optionRole: "{role} — {description}.",
      envoyer: "Envoyer l'invitation",
      annuler: "Annuler",
      // confirmation sans date (décision du 7 octobre 2026) : la date exacte vient d'identity, dans la fiche
      confirmation: {
        question: "Envoyer l'invitation à {nom} ?",
        adresse: "Adresse : {adresse}",
        role: "Rôle : {role} — {description}.",
        validite: "Le lien sera valable 7 jours.",
        modifier: "Modifier",
      },
      succes: "Invitation envoyée à {nom} ({adresse}). Le lien est valable 7 jours.",
    },
    // écran 6.4 (N24, A7, A8)
    role: {
      titre: "Changer le rôle de {nom}",
      filAriane: "Rôle",
      roleActuel: "(rôle actuel)",
      enregistrer: "Enregistrer",
      annuler: "Annuler",
      donnerGerant: {
        question: "Donner le rôle de gérant à {nom} ?",
        explication: "Ce compte pourra gérer tout LePalier, y compris inviter, suspendre et réinitialiser les utilisateurs.",
        bouton: "Donner le rôle de gérant",
      },
      quitterGerant: {
        question: "Quitter le rôle de gérant ?",
        explication: "Vous n'aurez plus accès à l'Administration. Un autre gérant pourra vous redonner ce rôle.",
        bouton: "Quitter le rôle de gérant",
        succes: "Votre rôle est maintenant {role}. L'Administration n'est plus accessible depuis ce compte.",
      },
      succes: "Rôle de {nom} changé : {nouveau} (auparavant {ancien}).",
      aucunChangement: "Aucun changement : {nom} a déjà le rôle {role}.",
    },
    // écran 6.3 (N23, A6, décision du 7 octobre 2026 pour sa propre fiche)
    fiche: {
      titre: "Accès de {nom}",
      adresse: "Adresse e-mail : {adresse}",
      role: "Rôle : {role}",
      changerRole: "Changer le rôle",
      statut: "Statut : {statut}",
      invitationValable: "Invitation envoyée le {envoi}, valable jusqu'au {fin}.",
      invitationExpiree:
        "Invitation envoyée le {envoi} ; le lien a expiré le {fin}. Pour en envoyer un nouveau, touchez « Renvoyer l'invitation ».",
      actions: "Actions",
      soiMeme:
        "Vous ne pouvez ni suspendre ni réinitialiser votre propre accès. Si c'est nécessaire, demandez-le à un autre gérant.",
      annuler: "Annuler",
      suspendre: {
        bouton: "Suspendre l'accès",
        question: "Suspendre l'accès de {nom} ?",
        explication:
          "Ce compte sera déconnecté dans les 10 secondes et ne pourra plus se connecter tant que vous n'aurez pas réactivé l'accès.",
        succes: "Accès de {nom} suspendu.",
      },
      reactiver: { bouton: "Réactiver l'accès", succes: "Accès de {nom} réactivé." },
      reinitialiser: {
        bouton: "Réinitialiser l'accès",
        question: "Réinitialiser l'accès de {nom} ?",
        explication:
          "Le mot de passe, les codes de secours et l'application d'authentification de ce compte ne fonctionneront plus. Un e-mail avec un nouveau lien, valable 7 jours, sera envoyé à {adresse}.",
        succes: "Accès de {nom} réinitialisé ; un e-mail lui a été envoyé.",
      },
      renvoyer: {
        bouton: "Renvoyer l'invitation",
        succes:
          "Invitation renvoyée à {nom} ({adresse}). Le nouveau lien est valable 7 jours ; l'ancien ne fonctionne plus.",
      },
      annulerInvitation: {
        bouton: "Annuler l'invitation",
        question: "Annuler l'invitation de {nom} ?",
        explication: "Le lien envoyé à {adresse} ne fonctionnera plus et cette personne disparaîtra de la liste.",
        garder: "Garder l'invitation",
        succes: "Invitation de {nom} annulée.",
      },
    },
  },
  // page d'administration ouverte par un associé ou un opérateur (maquettes v3, écran 7 ; R0-06)
  reservee: {
    titre: "Page réservée au gérant",
    reservee: "Cette page est réservée au gérant.",
    demandez: "Si vous avez besoin de cette information, demandez-la au gérant de la SCI.",
  },
  accueil: {
    titre: "À faire",
    videGestion:
      "Rien à faire pour le moment. Les paiements à enregistrer, les relevés d'eau et les envois à préparer apparaîtront ici, du plus urgent au moins urgent.",
    videAssocie:
      "Rien à faire pour le moment. Vous n'avez aucune saisie à faire dans LePalier : les informations importantes apparaîtront ici.",
    compteActive:
      "Votre compte est activé. Pour vous connecter la prochaine fois : votre adresse e-mail, votre mot de passe, puis le code de votre application.",
  },
  // bloc ou écran dont la source ne répond pas (UX-30)
  indisponible: "Information momentanément indisponible",
  // Mot de passe oublié (N26) et Choisir un nouveau mot de passe (N27)
  reinitialisation: {
    demande: {
      titre: "Mot de passe oublié",
      consigne: "Indiquez l'adresse e-mail de votre compte. Vous recevrez un lien pour choisir un nouveau mot de passe.",
      adresse: "Adresse e-mail",
      bouton: "Recevoir le lien",
      retour: "Retour à la connexion",
      // revue UX du 8 octobre 2026 (M5) : l'adresse saisie est rappelée, pour voir une faute de frappe
      adresseSaisie: "Adresse saisie :",
      autreAdresse: "Saisir une autre adresse",
    },
    choix: {
      titre: "Choisir un nouveau mot de passe",
      motDePasse: "Nouveau mot de passe",
      code: "Code de vérification",
      aideCode: "Le code à 6 chiffres affiché en ce moment par votre application d'authentification.",
      bouton: "Changer le mot de passe",
      // accès à /reinitialisation sans le lien de l'e-mail (revue UX du 8 octobre 2026) : cite l'objet de l'e-mail
      sansLien:
      "Pour choisir un nouveau mot de passe, ouvrez le lien de l'e-mail « [LePalier] Choisir un nouveau mot de passe ». Vous ne le trouvez pas ? Faites une nouvelle demande avec « Mot de passe oublié ».",
    },
  },
  // repris de libs/commun (erreurs.py, identite.py) pour les cas sans réponse de l'API ; un test vérifie l'égalité
  commun: {
    erreurInattendue: "Une erreur inattendue est survenue. Réessayez dans quelques instants.",
    sessionExpiree: "Votre session a expiré ou n'est pas reconnue. Reconnectez-vous.",
    introuvable: "Cette page ou cette information n'existe pas.",
  },
  retourAccueil: "Retour à l'accueil",
} as const;
