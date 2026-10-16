// Adresse e-mail à vérifier ou à retenir (revue UX, M3) : jamais coupée à un trait d'union, qui ferait douter de
// l'adresse ; coupée à la largeur disponible seulement si elle est trop longue pour la ligne. seule : sur sa propre
// ligne (adresse à vérifier d'un coup d'œil dans une confirmation).
import type { ReactNode } from "react";

export function AdresseEmail({ seule = false, children }: { seule?: boolean; children: ReactNode }) {
  return <span className={seule ? "adresse-email adresse-email-seule" : "adresse-email"}>{children}</span>;
}
