// Lien présenté comme un bouton secondaire (cible de 44 px), pour une adresse à ouvrir (application, document).
import type { AnchorHTMLAttributes, ReactNode } from "react";

type Props = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "className" | "children"> & { children: ReactNode };

export function LienBouton({ children, ...lien }: Props) {
  return (
    <a {...lien} className="bouton bouton-secondaire">
      {children}
    </a>
  );
}
