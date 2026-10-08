// Page introuvable : message 404 de commun et retour à l'accueil, sans style en ligne (politique de sécurité).
import type { Metadata } from "next";
import { CadrePublic } from "@/components/cadre/CadrePublic";
import { Lien } from "@/components/ui/Lien";
import { TEXTES } from "@/textes";

export const metadata: Metadata = { title: "LePalier" };

export default function Introuvable() {
  return (
    <CadrePublic>
      <h1>{TEXTES.commun.introuvable}</h1>
      <p>
        <Lien href="/">{TEXTES.retourAccueil}</Lien>
      </p>
    </CadrePublic>
  );
}
