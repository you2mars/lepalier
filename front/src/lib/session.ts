// Personne connectée (écrans connectés) : lue une fois par requête dans /moi d'identity, par le BFF. Sans cookie
// de session : Se connecter, sans message ; 401 : Se connecter avec le bandeau qui convient (etat-session) et la
// page demandée (maquettes v3, § 0.3) ; panne d'identity : null (information momentanément indisponible).
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";
import { lire, motifSession } from "./bff";
import { adresseConnexion } from "./retour";

export type Role = "gerant" | "associe" | "operateur";
export type Personne = { id: string; email: string; nom_affiche: string; role: Role };

// chemin demandé, posé par le middleware (jamais celui envoyé par le navigateur)
export const ENTETE_CHEMIN = "x-lepalier-chemin";

export const personneConnectee = cache(async (): Promise<Personne | null> => {
  const session = (await cookies()).get("lp_session")?.value;
  const chemin = (await headers()).get(ENTETE_CHEMIN);
  if (!session) redirect(adresseConnexion(null, chemin));
  const moi = await lire<Personne>("/identity/moi", session);
  if (moi.ok) return moi.donnees;
  if (moi.statut === 401) redirect(adresseConnexion(await motifSession(session), chemin));
  return null;
});
