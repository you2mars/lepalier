import type { Metadata } from "next";
import { PageReservee } from "@/components/cadre/PageReservee";
import { FilAriane } from "@/components/ui/FilAriane";
import { personneConnectee } from "@/lib/session";
import { TEXTES } from "@/textes";
import { FormulaireInvitation } from "./FormulaireInvitation";

export const metadata: Metadata = { title: "Inviter une personne — LePalier" };

export default async function Page() {
  const personne = await personneConnectee();
  if (personne?.role !== "gerant") return <PageReservee />;
  return (
    <>
      <FilAriane
        etapes={[
          { libelle: TEXTES.cadre.administration },
          { libelle: TEXTES.utilisateurs.liste.titre, href: "/administration/utilisateurs" },
          { libelle: TEXTES.utilisateurs.inviter.filAriane },
        ]}
      />
      <h1>{TEXTES.utilisateurs.inviter.titre}</h1>
      <FormulaireInvitation />
    </>
  );
}
