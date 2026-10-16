// État vide (UX-27) : explique pourquoi la liste est vide et ce qui y apparaîtra.
import type { ReactNode } from "react";

export function EtatVide({ children }: { children: ReactNode }) {
  return <p className="etat-vide">{children}</p>;
}
