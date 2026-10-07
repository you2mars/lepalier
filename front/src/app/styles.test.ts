import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

// Préparation d'une refonte graphique (front/CLAUDE.md) : couleurs, tailles de texte, polices, espacements, rayons
// et ombres ne sont écrits qu'une fois, en variables du bloc :root de globals.css ; partout ailleurs, var(--…).
const SRC = join(__dirname, "..");
const GLOBALS = readFileSync(join(__dirname, "globals.css"), "utf8");

// déclarations « propriété: valeur » hors du bloc :root, commentaires retirés
function declarationsHorsRacine(css: string): { propriete: string; valeur: string }[] {
  const sansCommentaires = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const sansRacine = sansCommentaires.replace(/:root\s*\{[^}]*\}/, "");
  return [...sansRacine.matchAll(/([a-z-]+)\s*:\s*([^;{}]+);/g)].map(([, propriete, valeur]) => ({
    propriete: propriete!,
    valeur: valeur!.trim(),
  }));
}

const COULEUR = /#[0-9a-f]{3,8}\b|\b(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(/i;
const NOMS_COULEURS =
  /\b(white|black|red|green|blue|gray|grey|silver|orange|yellow|purple|pink|brown|navy|teal|maroon|olive|lime|aqua|fuchsia|beige|ivory|khaki|coral|salmon|gold|indigo|violet|tan|crimson)\b/i;
// valeurs toujours permises : mots-clés sans dimension
const MOTS_CLES = /^(0|auto|none|inherit|initial|unset|normal|transparent|currentcolor)( (0|auto))*$/i;
const AVEC_VARIABLE = /^((calc\()?\s*var\(--[a-z0-9-]+\)(\s*\*\s*-?[\d.]+)?\)?|0|auto)( ((calc\()?\s*var\(--[a-z0-9-]+\)(\s*\*\s*-?[\d.]+)?\)?|0|auto))*$/i;

const TYPOGRAPHIE = ["font-size", "font-family", "line-height", "font-weight"];
const ESPACEMENTS = [
  "margin",
  "margin-top",
  "margin-bottom",
  "margin-left",
  "margin-right",
  "padding",
  "padding-top",
  "padding-bottom",
  "padding-left",
  "padding-right",
  "gap",
  "row-gap",
  "column-gap",
];
const FORMES = ["border-radius", "box-shadow"];

describe("globals.css : valeurs de conception seulement dans :root", () => {
  const declarations = declarationsHorsRacine(GLOBALS);

  it("aucune couleur en dur (#…, rgb(), hsl(), nom de couleur) hors de :root", () => {
    const fautives = declarations.filter((d) => COULEUR.test(d.valeur) || NOMS_COULEURS.test(d.valeur));
    expect(fautives).toEqual([]);
  });

  it.each([
    ["typographie", TYPOGRAPHIE],
    ["espacements", ESPACEMENTS],
    ["rayons et ombres", FORMES],
  ])("%s : variables de :root (ou 0, auto, none…)", (_, proprietes) => {
    const fautives = declarations.filter(
      (d) => proprietes.includes(d.propriete) && !MOTS_CLES.test(d.valeur) && !AVEC_VARIABLE.test(d.valeur),
    );
    expect(fautives).toEqual([]);
  });

  it("toute variable utilisée est définie dans :root (une faute de frappe retomberait sans bruit sur la valeur par défaut)", () => {
    const racine = /:root\s*\{([^}]*)\}/.exec(GLOBALS)?.[1] ?? "";
    const definies = new Set([...racine.matchAll(/(--[a-z0-9-]+)\s*:/g)].map((m) => m[1]));
    const utilisees = new Set([...GLOBALS.matchAll(/var\((--[a-z0-9-]+)\)/g)].map((m) => m[1]));
    expect([...utilisees].filter((v) => !definies.has(v))).toEqual([]);
  });

  it("le contrôle repère bien une couleur, une taille et un rayon en dur", () => {
    const essai = declarationsHorsRacine(
      ":root { --a: #fff; } .x { color: #e8e6e3; font-size: 1.125rem; border-radius: 4px; padding: var(--espace); }",
    );
    expect(essai.filter((d) => COULEUR.test(d.valeur)).map((d) => d.propriete)).toEqual(["color"]);
    const tailles = essai.filter(
      (d) => [...TYPOGRAPHIE, ...FORMES, ...ESPACEMENTS].includes(d.propriete) && !AVEC_VARIABLE.test(d.valeur),
    );
    expect(tailles.map((d) => d.propriete)).toEqual(["font-size", "border-radius"]);
  });
});

describe("composants et écrans : aucun style propre", () => {
  function fichiers(dossier: string): string[] {
    return readdirSync(dossier, { withFileTypes: true }).flatMap((e) =>
      e.isDirectory() ? fichiers(join(dossier, e.name)) : [join(dossier, e.name)],
    );
  }
  const tous = fichiers(SRC);

  it("une seule feuille de style : src/app/globals.css", () => {
    const feuilles = tous.filter((f) => /\.(css|scss|sass|less)$/.test(f)).map((f) => relative(SRC, f));
    expect(feuilles).toEqual(["app/globals.css"]);
  });

  // classes de pure mise en page permises dans les écrans (src/app) ; tout le reste passe par un composant
  const MISE_EN_PAGE: string[] = [];

  it("écrans (src/app) : aucune classe visuelle, seulement des composants", () => {
    const ecrans = tous.filter((f) => f.startsWith(join(SRC, "app")) && f.endsWith(".tsx") && !f.endsWith(".test.tsx"));
    const fautives = ecrans.flatMap((f) =>
      [...readFileSync(f, "utf8").matchAll(/className=(?:"([^"]*)"|\{([^}]*)\})/g)]
        .flatMap(([, simple, expression]) => (simple ?? expression ?? "").match(/[a-z][a-z0-9-]*/g) ?? [])
        .filter((classe) => !MISE_EN_PAGE.includes(classe))
        .map((classe) => `${relative(SRC, f)} : ${classe}`),
    );
    expect(fautives).toEqual([]);
  });

  it("écrans (src/app) : formulaires par le composant Formulaire, jamais une balise <form> directe", () => {
    const fautifs = tous
      .filter((f) => f.startsWith(join(SRC, "app")) && f.endsWith(".tsx") && !f.endsWith(".test.tsx"))
      .filter((f) => /<form[\s>]/.test(readFileSync(f, "utf8")))
      .map((f) => relative(SRC, f));
    expect(fautifs).toEqual([]);
  });

  it("aucun style en ligne (style={…}) dans les composants ni les écrans", () => {
    const fautifs = tous
      .filter((f) => f.endsWith(".tsx") && !f.endsWith(".test.tsx"))
      .filter((f) => /\bstyle=\{/.test(readFileSync(f, "utf8")))
      .map((f) => relative(SRC, f));
    expect(fautifs).toEqual([]);
  });
});
