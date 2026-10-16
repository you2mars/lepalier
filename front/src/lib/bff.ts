// Lectures du BFF (front côté serveur) par l'écoute interne de nginx (LEPALIER_BFF, port 8081) : seul le cookie
// de session est relayé, rien n'est mis en cache ; une panne ou un service qui ne répond pas dans le délai devient
// un résultat, jamais une exception ni une page qui reste en attente : la page dégrade le seul bloc concerné (UX-30).

export type Lecture<T> = { ok: true; statut: number; donnees: T } | { ok: false; statut: number };
export type MotifSession = "compte_suspendu" | "session_expiree";

const DELAI_MS = 5000;

export async function lire<T>(
  chemin: string,
  session: string | undefined,
  { delaiMs = DELAI_MS }: { delaiMs?: number } = {},
): Promise<Lecture<T>> {
  try {
    const reponse = await fetch(`${process.env.LEPALIER_BFF}/api${chemin}`, {
      cache: "no-store",
      headers: session ? { Cookie: `lp_session=${session}` } : {},
      signal: AbortSignal.timeout(delaiMs),
    });
    if (!reponse.ok) return { ok: false, statut: reponse.status };
    return { ok: true, statut: reponse.status, donnees: (await reponse.json()) as T };
  } catch {
    return { ok: false, statut: 0 };
  }
}

// Après un 401 : identity dit au seul détenteur du cookie si sa session a été coupée par une suspension ; tout le
// reste, panne comprise, est une session expirée (ADR 0006, seule exception à /auth/* sur l'écoute interne).
export async function motifSession(session: string | undefined): Promise<MotifSession> {
  const etat = await lire<{ code?: unknown }>("/identity/auth/etat-session", session);
  return etat.ok && etat.donnees.code === "compte_suspendu" ? "compte_suspendu" : "session_expiree";
}
