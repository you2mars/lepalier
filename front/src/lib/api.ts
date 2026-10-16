// Écritures depuis le navigateur, à travers nginx (vraie adresse IP du client, contrôle de l'origine) ; erreurs
// lues au format de commun : {code, message, details: {champs: [{champ, message}]}, trace_id}.
import { TEXTES } from "@/textes";

export type ErreurApi = { code: string; message: string; champs: Record<string, string> };
export type Resultat<T> =
  | { ok: true; statut: number; donnees: T | null }
  | { ok: false; statut: number; erreur: ErreurApi };

const INATTENDUE: ErreurApi = { code: "inattendue", message: TEXTES.commun.erreurInattendue, champs: {} };

function lireErreur(corps: unknown): ErreurApi {
  if (typeof corps !== "object" || corps === null) return INATTENDUE;
  const { code, message, details } = corps as { code?: unknown; message?: unknown; details?: unknown };
  if (typeof code !== "string" || typeof message !== "string") return INATTENDUE;
  const champs: Record<string, string> = {};
  const liste = (details as { champs?: unknown } | undefined)?.champs;
  if (Array.isArray(liste)) {
    for (const element of liste) {
      const { champ, message: texte } = element as { champ?: unknown; message?: unknown };
      if (typeof champ === "string" && typeof texte === "string") champs[champ] = texte;
    }
  }
  return { code, message, champs };
}

export async function envoyer<T = unknown>(
  chemin: string,
  corps: unknown,
  options: { methode?: "POST" | "PATCH"; cleIdempotence?: string } = {},
): Promise<Resultat<T>> {
  const entetes: Record<string, string> = { "Content-Type": "application/json" };
  if (options.cleIdempotence) entetes["Idempotency-Key"] = options.cleIdempotence;
  let reponse: Response;
  try {
    reponse = await fetch(`/api${chemin}`, {
      method: options.methode ?? "POST",
      credentials: "same-origin",
      headers: entetes,
      body: JSON.stringify(corps),
    });
  } catch {
    return { ok: false, statut: 0, erreur: INATTENDUE };
  }
  const json = (reponse.headers.get("Content-Type") ?? "").includes("application/json");
  const contenu: unknown = json ? await reponse.json().catch(() => null) : null;
  if (reponse.ok) return { ok: true, statut: reponse.status, donnees: (contenu as T | null) ?? null };
  return { ok: false, statut: reponse.status, erreur: json ? lireErreur(contenu) : INATTENDUE };
}
