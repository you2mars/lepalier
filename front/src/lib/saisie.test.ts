import { describe, expect, it } from "vitest";
import { emailValide, erreurLongueurMotDePasse, nomAfficheValide } from "./saisie";
import { messageMotDePasse } from "./libelles";

// Contrôles faits à la sortie du champ, mêmes règles qu'identity (engines/nom_affiche.py, engines/mot_de_passe.py) ;
// identity reste juge à l'envoi final.
describe("nomAfficheValide", () => {
  it.each([["Mme Durand"], ["  M. Martin  "], ["a"], ["é".repeat(60)], ["Jean-Luc O'Neil"]])("accepte %j", (nom) => {
    expect(nomAfficheValide(nom)).toBe(true);
  });

  it.each([
    [""],
    ["   "],
    ["x".repeat(61)],
    ["marie@exemple.fr"],
    ["Mme\u0000Durand"],
    ["Mme\u0085Durand"],
    ["Mme\u2028Durand"],
    ["Mme\u202eDurand"],
    ["Mme\u2066Durand"],
  ])("refuse %j", (nom) => {
    expect(nomAfficheValide(nom)).toBe(false);
  });

  it("espaces ordinaires autour retirés avant la mesure : 60 caractères utiles acceptés", () => {
    expect(nomAfficheValide(`  ${"x".repeat(60)}  `)).toBe(true);
  });
});

describe("erreurLongueurMotDePasse", () => {
  it.each([
    ["le chat dor", "trop_court"],
    ["  le chat dor  ", "trop_court"],
    ["le   chat dor ", "trop_court"],
    ["x".repeat(129), "trop_long"],
  ] as const)("%j : %s", (mot, motif) => {
    expect(erreurLongueurMotDePasse(mot)).toBe(messageMotDePasse(motif));
  });

  it.each([["le chat dort sur le toit"], ["x".repeat(128)], ["le chat dort "]])("%j : accepté", (mot) => {
    expect(erreurLongueurMotDePasse(mot)).toBeUndefined();
  });

  it("caractères hors du plan de base comptés un par un, comme identity", () => {
    expect(erreurLongueurMotDePasse("😀".repeat(12))).toBeUndefined();
    expect(erreurLongueurMotDePasse("😀".repeat(11))).toBe(messageMotDePasse("trop_court"));
  });
});

// Même règle qu'identity (api/saisie.py) : caractères ASCII imprimables, une « @ », un point dans le domaine ;
// espaces ordinaires autour tolérés.
describe("emailValide", () => {
  it.each([["marie.durand@exemple.fr"], ["  paul+essai@exemple.co.uk "], ["A.B@exemple.fr"]])("accepte %j", (adresse) => {
    expect(emailValide(adresse)).toBe(true);
  });

  it.each([[""], ["marie"], ["marie@exemple"], ["marie@@exemple.fr"], ["mar ie@exemple.fr"], ["marié@exemple.fr"], ["marie@exemple.fr\n"], [`${"a".repeat(250)}@x.fr`]])(
    "refuse %j",
    (adresse) => {
      expect(emailValide(adresse)).toBe(false);
    },
  );
});
