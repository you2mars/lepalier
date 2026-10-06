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

  it("messages de commun repris quand aucune réponse de l'API n'est disponible : identiques à libs/commun", () => {
    const racine = join(__dirname, "..", "..", "libs", "commun", "src", "commun");
    const constante = (fichier: string, nom: string) =>
      new RegExp(`${nom} = "([^"]+)"`).exec(readFileSync(join(racine, fichier), "utf8"))?.[1];
    expect(TEXTES.commun.erreurInattendue).toBe(constante("erreurs.py", "MESSAGE_INTERNE"));
    expect(TEXTES.commun.sessionExpiree).toBe(constante("identite.py", "MESSAGE_NON_AUTHENTIFIE"));
  });
});
