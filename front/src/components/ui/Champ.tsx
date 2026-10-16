"use client";
// Champ de formulaire (UX-15, UX-17, UX-19, UX-23) : libellé au-dessus, aide puis erreur sous le champ, reliées
// au champ par aria-describedby ; « (facultatif) » sur l'optionnel.
import type { InputHTMLAttributes, ReactNode, Ref } from "react";
import { useVerificationALaSortie } from "./Formulaire";

export type ProprietesChamp = InputHTMLAttributes<HTMLInputElement> & {
  id: string;
  libelle: string;
  aide?: string;
  erreur?: string;
  facultatif?: boolean;
  ref?: Ref<HTMLInputElement>;
  apres?: ReactNode;
  // vérification à la sortie du champ, reportée à l'envoi sur appui du pointeur (voir Formulaire)
  verifierALaSortie?: () => void;
};

export function Champ({
  id,
  libelle,
  aide,
  erreur,
  facultatif,
  apres,
  className,
  verifierALaSortie,
  onBlur,
  ...champ
}: ProprietesChamp) {
  const aLaSortie = useVerificationALaSortie();
  const decrit = [aide ? `${id}-aide` : null, erreur ? `${id}-erreur` : null].filter(Boolean).join(" ");
  return (
    <div className={["champ", className].filter(Boolean).join(" ")}>
      <label htmlFor={id}>{facultatif ? `${libelle} (facultatif)` : libelle}</label>
      <div className="champ-saisie">
        <input
          {...champ}
          id={id}
          onBlur={(e) => {
            onBlur?.(e);
            if (verifierALaSortie) aLaSortie(verifierALaSortie);
          }}
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
