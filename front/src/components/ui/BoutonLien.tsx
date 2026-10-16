// Action secondaire dans la page (changer de mode, revenir à l'étape précédente), présentée comme un lien ; jamais
// un envoi de formulaire ; cible de 44 px. sousChamp : placée juste sous le champ et son message (M4).
import type { ButtonHTMLAttributes } from "react";

type Props = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "type" | "className"> & { sousChamp?: boolean };

export function BoutonLien({ sousChamp = false, ...bouton }: Props) {
  return (
    <p className={sousChamp ? "action-sous-champ" : undefined}>
      <button {...bouton} type="button" className="bouton-lien" />
    </p>
  );
}
