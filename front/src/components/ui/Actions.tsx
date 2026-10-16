// Rangée de boutons d'un formulaire ou d'une confirmation : le bouton principal d'abord, puis les secondaires.
import type { ReactNode } from "react";

export function Actions({ children }: { children: ReactNode }) {
  return <div className="actions">{children}</div>;
}
