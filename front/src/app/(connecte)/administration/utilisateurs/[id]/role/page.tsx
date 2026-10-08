// Administration › Utilisateurs › {nom} › Rôle (maquettes v3, écran 6.4) : fiche lue chez identity ; inconnue ou
// annulée : page introuvable ; associé ou opérateur (ou 403) : page réservée ; panne : information indisponible.
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PageReservee } from "@/components/cadre/PageReservee";
import { FilAriane } from "@/components/ui/FilAriane";
import { remplir } from "@/lib/modele";
import { lireConnecte, personneConnectee } from "@/lib/session";
import { TEXTES } from "@/textes";
import type { Fiche } from "../GestionAcces";
import { FormulaireRole } from "./FormulaireRole";

type Parametres = { params: Promise<{ id: string }> };

async function lireFiche(id: string) {
  return lireConnecte<Fiche>(`/identity/utilisateurs/${encodeURIComponent(id)}`);
}

export async function generateMetadata({ params }: Parametres): Promise<Metadata> {
  const lecture = await lireFiche((await params).id);
  const titre = lecture.ok ? remplir(TEXTES.utilisateurs.role.titre, { nom: lecture.donnees.nom_affiche }) : null;
  return { title: titre ? `${titre} — LePalier` : "LePalier" };
}

export default async function Page({ params }: Parametres) {
  const personne = await personneConnectee();
  if (personne?.role !== "gerant") return <PageReservee />;
  const lecture = await lireFiche((await params).id);
  if (!lecture.ok && lecture.statut === 404) notFound();
  if (!lecture.ok && lecture.statut === 403) return <PageReservee />;
  const etapes = [
    { libelle: TEXTES.cadre.administration },
    { libelle: TEXTES.utilisateurs.liste.titre, href: "/administration/utilisateurs" },
  ];
  if (!lecture.ok) {
    return (
      <>
        <FilAriane etapes={etapes} />
        <h1>{TEXTES.indisponible}</h1>
      </>
    );
  }
  const fiche = lecture.donnees;
  return (
    <>
      <FilAriane
        etapes={[
          ...etapes,
          { libelle: fiche.nom_affiche, href: `/administration/utilisateurs/${fiche.id}` },
          { libelle: TEXTES.utilisateurs.role.filAriane },
        ]}
      />
      <h1>{remplir(TEXTES.utilisateurs.role.titre, { nom: fiche.nom_affiche })}</h1>
      <FormulaireRole fiche={fiche} estMoi={fiche.id === personne.id} />
    </>
  );
}
