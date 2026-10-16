// Contrôles faits à la sortie du champ, mêmes règles qu'identity (engines/nom_affiche.py et
// engines/mot_de_passe.py) ; identity reste seul juge à l'envoi final (motifs du mot de passe compris).
import { messageMotDePasse } from "./libelles";

const NOM_LONGUEUR_MAX = 60;
// eslint-disable-next-line no-control-regex -- volontaire : mêmes caractères refusés qu'identity
const NOM_CONTROLE = /[\u0000-\u001f\u007f-\u009f\u2028-\u202e\u2066-\u2069]/;
const MOT_DE_PASSE_MIN = 12;
const MOT_DE_PASSE_MAX = 128;

// longueur en caractères (points de code), comme len() en Python
function longueur(texte: string): number {
  return [...texte].length;
}

export function nomAfficheValide(nom: string): boolean {
  const nettoye = nom.replace(/^ +| +$/g, "");
  return (
    longueur(nettoye) >= 1 &&
    longueur(nettoye) <= NOM_LONGUEUR_MAX &&
    !nettoye.includes("@") &&
    !NOM_CONTROLE.test(nettoye) &&
    nettoye.trim() !== ""
  );
}

// forme mesurée par identity : NFKC, sans espaces autour, espaces intérieurs consécutifs réduits à un
export function erreurLongueurMotDePasse(motDePasse: string): string | undefined {
  const mesure = longueur(motDePasse.normalize("NFKC").split(/\s+/).filter(Boolean).join(" "));
  if (mesure < MOT_DE_PASSE_MIN) return messageMotDePasse("trop_court");
  if (mesure > MOT_DE_PASSE_MAX) return messageMotDePasse("trop_long");
  return undefined;
}

const EMAIL_LONGUEUR_MAX = 254;
// caractères ASCII imprimables seulement (U+0021 à U+007E, hors « @ »), comme identity (api/saisie.py)
const EMAIL = /^[!-?A-~]+@[!-?A-~]+\.[!-?A-~]+$/;

export function emailValide(adresse: string): boolean {
  const nettoyee = adresse.replace(/^ +| +$/g, "");
  return nettoyee.length <= EMAIL_LONGUEUR_MAX && EMAIL.test(nettoyee);
}
