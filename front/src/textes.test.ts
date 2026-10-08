import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { TEXTES } from "./textes";

// Textes du front validés le 6 octobre 2026 (maquettes v3, N1 à N27), vérifiés mot pour mot.
describe("textes du front", () => {
  it("cadre commun", () => {
    expect(TEXTES.application).toBe("LePalier");
    expect(TEXTES.etats).toEqual({ fait: "Fait", attention: "Attention", erreur: "Erreur" });
    expect(TEXTES.envoiEnCours).toBe("Envoi en cours…");
    expect(TEXTES.allerAuContenu).toBe("Aller au contenu");
    expect(TEXTES.retourAccueil).toBe("Retour à l'accueil");
    expect(TEXTES.motDePasse).toEqual({
      afficher: "Afficher",
      masquer: "Masquer",
      afficherAccessible: "Afficher le mot de passe",
      masquerAccessible: "Masquer le mot de passe",
      // confirmation à la création et au changement (décision du 6 octobre 2026), soumis à validation
      confirmation: "Confirmez le mot de passe",
      differents: "Les deux mots de passe ne sont pas identiques. Tapez le même dans les deux champs.",
      afficherConfirmationAccessible: "Afficher la confirmation du mot de passe",
      masquerConfirmationAccessible: "Masquer la confirmation du mot de passe",
    });
  });

  it("écran Se connecter", () => {
    expect(TEXTES.connexion).toEqual({
      titre: "Se connecter",
      adresse: "Adresse e-mail",
      motDePasse: "Mot de passe",
      bouton: "Se connecter",
      oublie: "Mot de passe oublié",
      deconnexionEffectuee: "Déconnexion effectuée.",
      motDePasseChange: "Votre mot de passe a été changé. Connectez-vous avec le nouveau mot de passe.",
    });
  });

  it("écran Code de vérification (N7 à N10)", () => {
    expect(TEXTES.code).toEqual({
      titre: "Code de vérification",
      consigne:
        "Ouvrez votre application d'authentification et saisissez le code à 6 chiffres affiché pour LePalier.",
      libelle: "Code à 6 chiffres",
      aide: "Le code change toutes les 30 secondes : saisissez celui affiché en ce moment.",
      libelleSecours: "Code de secours",
      aideSecours: "Chaque code de secours ne sert qu'une fois.",
      utiliserSecours: "Utiliser un code de secours",
      utiliserApplication: "Utiliser le code de l'application",
      recommencer: "Recommencer la connexion",
      sansTelephone:
        "Vous n'avez plus votre téléphone ni vos codes de secours ? Demandez au gérant de la SCI de réinitialiser votre accès.",
    });
  });

  it("écran Activer mon compte (N5, N11 à N15)", () => {
    expect(TEXTES.activation).toEqual({
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
      sansLien: "Pour activer votre compte, ouvrez le lien reçu dans l'e-mail d'invitation.",
    });
  });

  it("écran Codes de secours (N16 à N18 ; feuille imprimée : constat mineur n° 4)", () => {
    expect(TEXTES.codes).toEqual({
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
      barrezApresUsage: "Chaque code ne sert qu'une fois : barrez-le après usage.",
      imprimeLe: "Imprimé le",
    });
  });

  it("cadre connecté et accueil (N4, N19, N20, Q5 ; UX-30)", () => {
    expect(TEXTES.cadre).toEqual({
      role: "Rôle :",
      seDeconnecter: "Se déconnecter",
      aFaire: "À faire",
      administration: "Administration",
      menuPrincipal: "Menu principal",
      filAriane: "Fil d'Ariane",
    });
    expect(TEXTES.roles).toEqual({ gerant: "Gérant", associe: "Associé", operateur: "Opérateur" });
    // une seule description par rôle (Q5), reprise telle quelle partout (décision du 7 octobre 2026)
    expect(TEXTES.descriptionsRoles).toEqual({
      associe:
        "consulte tout (appartements, baux, loyers, charges, documents, envois), exporte et commente ; ne modifie rien",
      operateur:
        "saisit les relevés d'eau, les paiements, les factures et les pièces, et prépare les quittances et les avis ; ni bail, ni envoi recommandé",
      gerant: "gère tout, y compris les utilisateurs",
    });
    expect(TEXTES.accueil).toEqual({
      titre: "À faire",
      videGestion:
        "Rien à faire pour le moment. Les paiements à enregistrer, les relevés d'eau et les envois à préparer apparaîtront ici, du plus urgent au moins urgent.",
      videAssocie:
        "Rien à faire pour le moment. Vous n'avez aucune saisie à faire dans LePalier : les informations importantes apparaîtront ici.",
      compteActive:
        "Votre compte est activé. Pour vous connecter la prochaine fois : votre adresse e-mail, votre mot de passe, puis le code de votre application.",
    });
    expect(TEXTES.indisponible).toBe("Information momentanément indisponible");
  });

  it("administration : liste des utilisateurs (N21, B) et page réservée au gérant (N25, R0-06)", () => {
    expect(TEXTES.utilisateurs.liste).toEqual({
      titre: "Utilisateurs",
      inviter: "Inviter une personne",
      gererAcces: "Gérer l'accès",
      gererAccesDe: "de",
      colonnes: { nom: "Nom", adresse: "Adresse e-mail", role: "Rôle", statut: "Statut", actions: "Actions" },
    });
    expect(TEXTES.utilisateurs.inviter).toEqual({
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
      confirmation: {
        question: "Envoyer l'invitation à {nom} ?",
        adresse: "Adresse : {adresse}",
        role: "Rôle : {role} — {description}.",
        validite: "Le lien sera valable 7 jours.",
        modifier: "Modifier",
      },
      succes: "Invitation envoyée à {nom} ({adresse}). Le lien est valable 7 jours.",
    });
    expect(TEXTES.utilisateurs.fiche).toEqual({
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
    });
    expect(TEXTES.utilisateurs.role).toEqual({
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
    });
    expect(TEXTES.reservee).toEqual({
      titre: "Page réservée au gérant",
      reservee: "Cette page est réservée au gérant.",
      demandez: "Si vous avez besoin de cette information, demandez-la au gérant de la SCI.",
    });
  });

  it("messages de commun repris quand aucune réponse de l'API n'est disponible : identiques à libs/commun", () => {
    const racine = join(__dirname, "..", "..", "libs", "commun", "src", "commun");
    const constante = (fichier: string, nom: string) =>
      new RegExp(`${nom} = "([^"]+)"`).exec(readFileSync(join(racine, fichier), "utf8"))?.[1];
    expect(TEXTES.commun.erreurInattendue).toBe(constante("erreurs.py", "MESSAGE_INTERNE"));
    expect(TEXTES.commun.sessionExpiree).toBe(constante("identite.py", "MESSAGE_NON_AUTHENTIFIE"));
    const erreurs = readFileSync(join(racine, "erreurs.py"), "utf8");
    expect(/404: \("not_found", "([^"]+)"\)/.exec(erreurs)?.[1]).toBe(TEXTES.commun.introuvable);
  });
});
