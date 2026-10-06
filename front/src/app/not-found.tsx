// Page introuvable : message 404 de commun et retour à l'accueil, sans style en ligne (politique de sécurité).
import type { Metadata } from "next";
import Link from "next/link";
import { TEXTES } from "@/textes";

export const metadata: Metadata = { title: "LePalier" };

export default function Introuvable() {
  return (
    <main id="contenu" className="contenu-public">
      <p className="nom-application">{TEXTES.application}</p>
      <h1>{TEXTES.commun.introuvable}</h1>
      <p>
        <Link href="/">{TEXTES.retourAccueil}</Link>
      </p>
    </main>
  );
}
