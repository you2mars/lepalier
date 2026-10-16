// Case à cocher (design system § 9) : libellé cliquable à droite, cible de 44 px, erreur sous la case reliée par
// aria-describedby (UX-19).
import type { InputHTMLAttributes, Ref } from "react";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  id: string;
  libelle: string;
  erreur?: string;
  ref?: Ref<HTMLInputElement>;
};

export function CaseACocher({ id, libelle, erreur, ...champ }: Props) {
  return (
    <div className="case-a-cocher">
      <label htmlFor={id}>
        <input
          {...champ}
          id={id}
          type="checkbox"
          aria-describedby={erreur ? `${id}-erreur` : undefined}
          aria-invalid={erreur ? true : undefined}
        />
        {libelle}
      </label>
      {erreur ? (
        <p id={`${id}-erreur`} className="champ-erreur">
          {erreur}
        </p>
      ) : null}
    </div>
  );
}
