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
        "Avant de commencer : installez sur votre téléphone l'application « Google Authenticator » (gratuite, dans l'App Store ou le Play Store). Si vous quittez cette page pour l'installer, rouvrez simplement le lien de l'e-mail : vous reprendrez ici.",
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
