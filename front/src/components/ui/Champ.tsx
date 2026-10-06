// Champ de formulaire (UX-15, UX-17, UX-19, UX-23) : libellé au-dessus, aide puis erreur sous le champ, reliées
// au champ par aria-describedby ; « (facultatif) » sur l'optionnel.
import type { InputHTMLAttributes, ReactNode, Ref } from "react";

export type ProprietesChamp = InputHTMLAttributes<HTMLInputElement> & {
  id: string;
  libelle: string;
  aide?: string;
  erreur?: string;
  facultatif?: boolean;
  ref?: Ref<HTMLInputElement>;
  apres?: ReactNode;
};

export function Champ({ id, libelle, aide, erreur, facultatif, apres, className, ...champ }: ProprietesChamp) {
  const decrit = [aide ? `${id}-aide` : null, erreur ? `${id}-erreur` : null].filter(Boolean).join(" ");
  return (
    <div className={["champ", className].filter(Boolean).join(" ")}>
      <label htmlFor={id}>{facultatif ? `${libelle} (facultatif)` : libelle}</label>
      <div className="champ-saisie">
        <input
          {...champ}
          id={id}
          aria-describedby={decrit || undefined}
          aria-invalid={erreur ? true : undefined}
        />
        {apres}
      </div>
      {aide ? (
        <p id={`${id}-aide`} className="champ-aide">
          {aide}
        </p>
      ) : null}
      {erreur ? (
        <p id={`${id}-erreur`} className="champ-erreur">
          {erreur}
        </p>
      ) : null}
    </div>
  );
}
