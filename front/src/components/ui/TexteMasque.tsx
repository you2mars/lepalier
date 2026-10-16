// Texte lu par les lecteurs d'écran, invisible à l'écran (« Gérer l'accès » complété « de Mme Durand », M8). L'espace
// qui le sépare du texte visible se place avant le composant : à l'intérieur, il serait perdu dans le nom calculé.
import type { ReactNode } from "react";

export function TexteMasque({ children }: { children: ReactNode }) {
  return <span className="masque-visuellement">{children}</span>;
}
