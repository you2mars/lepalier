// Valeur à vérifier d'un coup d'œil dans une confirmation (adresse e-mail…) : en grand, jamais coupée au milieu.
import type { ReactNode } from "react";

export function ValeurEnGrand({ children }: { children: ReactNode }) {
  return <p className="valeur-en-grand">{children}</p>;
}
