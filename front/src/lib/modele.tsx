// Textes à trous de textes.ts (« Envoyer l'invitation à {nom} ? ») : chaque {clé} remplacée par sa valeur, recopiée
// telle quelle ; une clé sans valeur est une erreur, jamais un texte à trous affiché.
export function remplir(modele: string, valeurs: Record<string, string>): string {
  return modele.replace(/\{([a-z]+)\}/g, (_, cle: string) => {
    const valeur = valeurs[cle];
    if (valeur === undefined) throw new Error(`valeur manquante pour {${cle}}`);
    return valeur;
  });
}
