// Contenu utile seulement sur un téléphone ou une tablette (lien qui ouvre une application du téléphone) : caché sur
// un poste à souris, où il ne pourrait rien ouvrir (revue UX, M2).
import type { ReactNode } from "react";

export function SurEcranTactile({ children }: { children: ReactNode }) {
  return <div className="seulement-tactile">{children}</div>;
}
