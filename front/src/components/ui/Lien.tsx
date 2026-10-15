// Lien de texte (UX-8) : cible de 44 px de haut, pour le doigt comme pour la souris. Lien <a> ordinaire : navigation
// complète par le navigateur (le routeur de Next perd parfois une navigation sous charge, lib/navigation.ts).
import type { AnchorHTMLAttributes } from "react";

export function Lien({ children, ...lien }: Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "className"> & { href: string }) {
  return (
    <a {...lien} className="lien">
      {children}
    </a>
  );
}
