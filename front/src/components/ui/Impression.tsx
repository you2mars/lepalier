// Impression (UX-10) : HorsImpression enveloppe l'écran, masqué à l'impression ; FeuilleImpression n'existe qu'à
// l'impression (feuille sobre, nom de l'application en tête) et n'est jamais lue par les lecteurs d'écran.
import type { ReactNode } from "react";
import { TEXTES } from "@/textes";

export function HorsImpression({ children }: { children: ReactNode }) {
  return <div className="ecran-seul">{children}</div>;
}

export function FeuilleImpression({ children }: { children: ReactNode }) {
  return (
    <section className="feuille-impression" aria-hidden="true">
      <p className="nom-application">{TEXTES.application}</p>
      {children}
    </section>
  );
}
