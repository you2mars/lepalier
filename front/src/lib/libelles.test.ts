import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import identity from "@contrats/libelles/identity.json";
import { libelle, messageMotDePasse } from "./libelles";

const SRC = join(__dirname, "..");

function fichiersDuFront(dossier: string): string[] {
  return readdirSync(dossier).flatMap((nom) => {
    const chemin = join(dossier, nom);
    if (statSync(chemin).isDirectory()) return fichiersDuFront(chemin);
    return /\.(ts|tsx)$/.test(nom) && !/\.test\.tsx?$/.test(nom) ? [chemin] : [];
  });
}

describe("libellés d'identity (contracts/libelles/identity.json)", () => {
  it("lit le texte validé par sa clé « groupe.nom »", () => {
    expect(libelle("connexion.trop_d_essais")).toBe("Trop d'essais. Réessayez dans 15 minutes.");
    expect(libelle("statut.actif")).toBe("Accès actif");
  });

  it("donne le message de chaque motif de refus du mot de passe", () => {
    expect(messageMotDePasse("trop_court")).toBe(identity.mot_de_passe.trop_court);
  });

  it("aucun libellé validé n'est recopié dans le code du front : ils sont lus, jamais réécrits", () => {
    const textes = Object.values(identity).flatMap((groupe) => Object.values(groupe as Record<string, string>));
    const copies = fichiersDuFront(SRC)
      .filter((fichier) => !fichier.endsWith("libelles.ts"))
      .flatMap((fichier) => {
        const contenu = readFileSync(fichier, "utf8");
        return textes.filter((texte) => texte.length > 20 && contenu.includes(texte)).map((t) => `${fichier} : ${t}`);
      });
    expect(copies).toEqual([]);
  });
});
