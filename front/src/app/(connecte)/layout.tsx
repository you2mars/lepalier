// Écrans connectés : la personne est lue dans identity à chaque requête ; sans session, retour à Se connecter
// (lib/session.ts) ; identity en panne : « Information momentanément indisponible » (UX-30).
import type { ReactNode } from "react";
import { CadreConnecte } from "@/components/cadre/CadreConnecte";
import { CadrePublic } from "@/components/cadre/CadrePublic";
import { personneConnectee } from "@/lib/session";
import { TEXTES } from "@/textes";

export default async function MiseEnPageConnectee({ children }: { children: ReactNode }) {
  const personne = await personneConnectee();
  if (personne === null) {
    return (
      <CadrePublic>
        <p>{TEXTES.indisponible}</p>
      </CadrePublic>
    );
  }
  return <CadreConnecte personne={personne}>{children}</CadreConnecte>;
}
