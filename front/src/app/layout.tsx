import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = { title: "LePalier" };

// Toutes les pages sont calculées à chaque requête : le nonce de la politique de sécurité (CSP) change à chaque
// requête, une page pré-générée n'en aurait aucun et ses scripts seraient bloqués.
export const dynamic = "force-dynamic";

export default function MiseEnPageRacine({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
