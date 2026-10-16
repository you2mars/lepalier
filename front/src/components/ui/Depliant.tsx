// Dépliant (UX-26, UX-9) : détail facultatif, fermé par défaut, ouvert au clic ou au clavier ; jamais une fenêtre.
import type { ReactNode } from "react";

export function Depliant({ resume, children }: { resume: string; children: ReactNode }) {
  return (
    <details className="depliant">
      <summary>{resume}</summary>
      {children}
    </details>
  );
}
