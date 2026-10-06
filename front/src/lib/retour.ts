// Retour à la page demandée après une reconnexion (maquettes v3, § 0.3) : seuls les chemins internes de LePalier
// sont acceptés ; tout le reste renvoie à l'accueil. Le chemin est décodé (jusqu'à stabilité, pour les doubles
// encodages comme %252F) puis normalisé comme le ferait le navigateur, pour qu'aucune variante n'y échappe.

const ACCUEIL = "/";
const BASE = "https://lepalier.invalide";
// pages publiques : y revenir après une connexion n'a pas de sens et ferait boucler
const PAGES_PUBLIQUES = ["/connexion", "/activation", "/reinitialisation", "/mot-de-passe-oublie"];
// eslint-disable-next-line no-control-regex -- volontaire : refuser tout caractère de contrôle
const CONTROLE = /[\u0000-\u001f\u007f]/;
const DECODAGES_MAX = 5;

function decoder(brut: string): string | null {
  let courant = brut;
  for (let i = 0; i < DECODAGES_MAX; i++) {
    let suivant: string;
    try {
      suivant = decodeURIComponent(courant);
    } catch {
      return null;
    }
    if (suivant === courant) return courant;
    courant = suivant;
  }
  return null;
}

function interne(chemin: string): boolean {
  return chemin.startsWith("/") && !chemin.startsWith("//") && !chemin.includes("\\") && !CONTROLE.test(chemin);
}

function publique(chemin: string): boolean {
  return PAGES_PUBLIQUES.some((page) => chemin === page || chemin.startsWith(`${page}/`));
}

export function cheminDeRetour(brut: string | null | undefined): string {
  if (!brut) return ACCUEIL;
  const decode = decoder(brut);
  if (decode === null || !interne(brut) || !interne(decode)) return ACCUEIL;
  let url: URL;
  let normalise: URL;
  try {
    url = new URL(brut, BASE);
    normalise = new URL(decode, BASE);
  } catch {
    return ACCUEIL;
  }
  if (url.origin !== BASE || normalise.origin !== BASE) return ACCUEIL;
  if (publique(url.pathname) || publique(normalise.pathname)) return ACCUEIL;
  return url.pathname + url.search;
}
