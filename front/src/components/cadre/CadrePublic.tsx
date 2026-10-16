// Cadre des écrans hors connexion (maquettes v3, § 0.1) : nom de l'application, puis le contenu ; pas de menu.
import type { ReactNode } from "react";
import { TEXTES } from "@/textes";

export function CadrePublic({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="entete-public">
        <p className="nom-application">{TEXTES.application}</p>
      </header>
      <main id="contenu" className="contenu-public">
        {children}
      </main>
    </>
  );
}
