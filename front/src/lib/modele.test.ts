import { describe, expect, it } from "vitest";
import { remplir } from "./modele";

// Textes à trous de textes.ts : « Envoyer l'invitation à {nom} ? »
describe("remplir", () => {
  it("chaque {clé} remplacée par sa valeur, autant de fois qu'elle apparaît", () => {
    expect(remplir("Invitation envoyée à {nom} ({adresse}). {nom}", { nom: "Mme Durand", adresse: "a@b.fr" })).toBe(
      "Invitation envoyée à Mme Durand (a@b.fr). Mme Durand",
    );
  });

  it("valeur contenant des accolades ou un $ : recopiée telle quelle", () => {
    expect(remplir("à {nom} ?", { nom: "M. {x} $& $1" })).toBe("à M. {x} $& $1 ?");
  });

  it("clé absente : erreur (jamais un texte à trous affiché)", () => {
    expect(() => remplir("à {nom} ?", {})).toThrow("nom");
  });
});
