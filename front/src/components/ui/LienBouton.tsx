// Lien présenté comme un bouton (cible de 44 px) : principal pour la tâche suivante de l'écran (une seule fois par
// écran, UX-1), secondaire pour une adresse à ouvrir (application, document).
import type { AnchorHTMLAttributes, ReactNode } from "react";

type Props = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "className" | "children"> & {
  children: ReactNode;
  variante?: "principal" | "secondaire";
};

export function LienBouton({ children, variante = "secondaire", ...lien }: Props) {
  return (
    <a {...lien} className={`bouton bouton-${variante}`}>
      {children}
    </a>
  );
}
