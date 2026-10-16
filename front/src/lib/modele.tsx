import { Fragment, type ReactNode } from "react";

// Textes à trous de textes.ts (« Envoyer l'invitation à {nom} ? ») : chaque {clé} remplacée par sa valeur, recopiée
// telle quelle ; une clé sans valeur est une erreur, jamais un texte à trous affiché.
export function remplir(modele: string, valeurs: Record<string, string>): string {
  return modele.replace(/\{([a-z]+)\}/g, (_, cle: string) => {
    const valeur = valeurs[cle];
    if (valeur === undefined) throw new Error(`valeur manquante pour {${cle}}`);
    return valeur;
  });
}

// Même texte à trous, avec des valeurs qui sont des éléments (adresse e-mail mise en forme…) : liste d'éléments.
export function remplirAvec(modele: string, valeurs: Record<string, ReactNode>): ReactNode[] {
  return modele.split(/(\{[a-z]+\})/).map((morceau, i) => {
    const cle = /^\{([a-z]+)\}$/.exec(morceau)?.[1];
    if (!cle) return morceau;
    if (!(cle in valeurs)) throw new Error(`valeur manquante pour {${cle}}`);
    return <Fragment key={i}>{valeurs[cle]}</Fragment>;
  });
}
