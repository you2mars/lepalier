// Textes validés d'identity, écrits une seule fois dans contracts/libelles/identity.json et lus ici, jamais
// recopiés (un test le vérifie). Une clé inconnue ne compile pas.
import identity from "@contrats/libelles/identity.json";

type Libelles = typeof identity;
export type CleLibelle = {
  [G in keyof Libelles]: `${G & string}.${keyof Libelles[G] & string}`;
}[keyof Libelles];
export type MotifMotDePasse = keyof Libelles["mot_de_passe"];

export function libelle(cle: CleLibelle): string {
  const [groupe, nom] = cle.split(".") as [keyof Libelles, string];
  return (identity[groupe] as Record<string, string>)[nom] as string;
}

export function messageMotDePasse(motif: MotifMotDePasse): string {
  return identity.mot_de_passe[motif];
}
