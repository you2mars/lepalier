import { describe, expect, it } from "vitest";
import { adresseConnexion, cheminDeRetour } from "./retour";

// Retour à la page demandée après une reconnexion : chemins internes de LePalier seulement (maquettes v3, § 0.3).
describe("cheminDeRetour", () => {
  it.each([
    ["/administration/utilisateurs", "/administration/utilisateurs"],
    ["/administration/utilisateurs?page=2", "/administration/utilisateurs?page=2"],
    ["/", "/"],
    ["/administration/utilisateurs/0192f3a4-5b6c-7d8e-9f01-234567890c00", "/administration/utilisateurs/0192f3a4-5b6c-7d8e-9f01-234567890c00"],
  ])("garde le chemin interne %s", (brut, attendu) => {
    expect(cheminDeRetour(brut)).toBe(attendu);
  });

  it.each([
    [null],
    [undefined],
    [""],
    ["administration"],
    ["//pirate.example"],
    ["//pirate.example/connexion"],
    ["/\\pirate.example"],
    ["\\\\pirate.example"],
    ["https://pirate.example/"],
    ["http:pirate.example"],
    ["javascript:alert(1)"],
    ["%2F%2Fpirate.example"],
    ["/%2F%2Fpirate.example"],
    ["%2f%2fpirate.example"],
    ["/%5Cpirate.example"],
    ["/%5cpirate.example"],
    ["%252F%252Fpirate.example"],
    ["/%252F%252Fpirate.example"],
    ["/%09/pirate.example"],
    ["/\t/pirate.example"],
    ["/%00"],
    ["/connexion"],
    ["/connexion/code"],
    ["/activation"],
    ["/reinitialisation?x=1"],
    ["/mot-de-passe-oublie"],
    ["/administration/%2e%2e/connexion"],
    ["/administration/../connexion"],
  ])("refuse %s et renvoie à l'accueil", (brut) => {
    expect(cheminDeRetour(brut)).toBe("/");
  });
});

// Adresse de l'écran Se connecter, avec le motif du bandeau d'arrivée et le chemin de retour contrôlé.
describe("adresseConnexion", () => {
  it.each([
    [null, null, "/connexion"],
    ["delai_depasse", null, "/connexion?motif=delai_depasse"],
    [null, "/administration/utilisateurs", "/connexion?retour=%2Fadministration%2Futilisateurs"],
    ["trop_de_codes", "/administration/utilisateurs", "/connexion?motif=trop_de_codes&retour=%2Fadministration%2Futilisateurs"],
    ["compte_suspendu", "//pirate.example", "/connexion?motif=compte_suspendu"],
    [null, "/", "/connexion"],
  ])("motif %s, retour %s : %s", (motif, retour, attendue) => {
    expect(adresseConnexion(motif, retour)).toBe(attendue);
  });
});
