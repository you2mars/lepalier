// Accueil « À faire » (maquettes v3, écran 5 ; UX-25, UX-27) : au lot 0, la liste est toujours vide ; état vide selon
// le rôle, sans bouton (aucune action inventée) ; bandeau d'arrivée après l'activation ou des codes perdus.
import type { Metadata } from "next";
import { Bandeau, type EtatBandeau } from "@/components/ui/Bandeau";
import { EtatVide } from "@/components/ui/EtatVide";
import { type Parametres, premier } from "@/lib/parametres";
import { personneConnectee } from "@/lib/session";
import { TEXTES } from "@/textes";

export const metadata: Metadata = { title: "À faire — LePalier" };

const BANDEAUX: Record<string, { etat: EtatBandeau; texte: string }> = {
  compte_active: { etat: "fait", texte: TEXTES.accueil.compteActive },
  codes_perdus: { etat: "attention", texte: TEXTES.codes.perdus },
};

export default async function Accueil({ searchParams }: { searchParams: Parametres }) {
  const motif = premier((await searchParams).motif);
  const bandeau = motif ? BANDEAUX[motif] : undefined;
  const personne = await personneConnectee();
  const vide = personne?.role === "associe" ? TEXTES.accueil.videAssocie : TEXTES.accueil.videGestion;
  return (
    <>
      {bandeau ? <Bandeau etat={bandeau.etat} message={bandeau.texte} /> : null}
      <h1>{TEXTES.accueil.titre}</h1>
      <EtatVide>{vide}</EtatVide>
    </>
  );
}
