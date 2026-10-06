// Page introuvable : message 404 de commun et retour à l'accueil, sans style en ligne (politique de sécurité).
import type { Metadata } from "next";
import Link from "next/link";
import { CadrePublic } from "@/components/cadre/CadrePublic";
import { TEXTES } from "@/textes";

export const metadata: Metadata = { title: "LePalier" };

export default function Introuvable() {
  return (
    <CadrePublic>
      <h1>{TEXTES.commun.introuvable}</h1>
      <p>
        <Link href="/">{TEXTES.retourAccueil}</Link>
      </p>
    </CadrePublic>
  );
}
