// Navigation complète (pas celle du routeur de Next) : après une déconnexion, aucune page connectée ne reste en
// mémoire, et la page quittée est remplacée dans l'historique (R0-08).
import { adresseConnexion } from "./retour";

export function quitterVers(adresse: string): void {
  window.location.replace(adresse);
}

// 401 sur une écriture, dans le navigateur : identity dit, par nginx 443, si la session a été coupée par une
// suspension (ADR 0006) ; puis Se connecter avec le bon bandeau et la page en cours (maquettes v3, § 0.3).
export async function reprendreSession(remplacer: (adresse: string) => void = quitterVers): Promise<void> {
  let motif = "session_expiree";
  try {
    const reponse = await fetch("/api/identity/auth/etat-session", { credentials: "same-origin", cache: "no-store" });
    const corps = (await reponse.json()) as { code?: unknown };
    if (reponse.ok && corps.code === "compte_suspendu") motif = "compte_suspendu";
  } catch {
    // panne : session expirée
  }
  remplacer(adresseConnexion(motif, window.location.pathname + window.location.search));
}
