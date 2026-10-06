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
  // repris de libs/commun (erreurs.py, identite.py) pour les cas sans réponse de l'API ; un test vérifie l'égalité
  commun: {
    erreurInattendue: "Une erreur inattendue est survenue. Réessayez dans quelques instants.",
    sessionExpiree: "Votre session a expiré ou n'est pas reconnue. Reconnectez-vous.",
    introuvable: "Cette page ou cette information n'existe pas.",
  },
  retourAccueil: "Retour à l'accueil",
} as const;
