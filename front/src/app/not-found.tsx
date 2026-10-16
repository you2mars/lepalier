// Page introuvable : message 404 de commun et retour à l'accueil, sans style en ligne (politique de sécurité) ; dans
// le cadre connecté quand la session est valide (constat UX (5)), sinon dans le cadre public.
import type { Metadata } from "next";
import { CadreConnecte } from "@/components/cadre/CadreConnecte";
import { CadrePublic } from "@/components/cadre/CadrePublic";
import { Lien } from "@/components/ui/Lien";
import { personneSiConnectee } from "@/lib/session";
import { TEXTES } from "@/textes";

export const metadata: Metadata = { title: "LePalier" };

export default async function Introuvable() {
  const contenu = (
    <>
      <h1>{TEXTES.commun.introuvable}</h1>
      <p>
        <Lien href="/">{TEXTES.retourAccueil}</Lien>
      </p>
    </>
  );
  const personne = await personneSiConnectee();
  return personne ? <CadreConnecte personne={personne}>{contenu}</CadreConnecte> : <CadrePublic>{contenu}</CadrePublic>;
}
