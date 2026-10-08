// Lien de texte (UX-8) : cible de 44 px de haut, pour le doigt comme pour la souris.
import Link from "next/link";
import type { ComponentProps } from "react";

export function Lien(lien: Omit<ComponentProps<typeof Link>, "className">) {
  return <Link {...lien} className="lien" />;
}
