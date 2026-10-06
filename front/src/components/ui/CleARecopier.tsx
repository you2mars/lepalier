"use client";
// Clé à recopier à la main (maquettes v3, § 0.5) : groupes de 4 caractères, lus groupe par groupe ; « Copier la clé »
// la met sans espaces dans le presse-papiers et l'annonce (« Clé copiée. ») ; sans presse-papiers, rien n'est dit.
import { useState } from "react";
import { TEXTES } from "@/textes";

export function CleARecopier({ groupes }: { groupes: string[] }) {
  const [copiee, setCopiee] = useState(false);
  const lisible = groupes.join(" ");

  async function copier() {
    try {
      await navigator.clipboard.writeText(groupes.join(""));
      setCopiee(true);
    } catch {
      // presse-papiers indisponible : la clé reste affichée pour être recopiée
    }
  }

  return (
    <>
      <p className="cle">
        <code aria-label={lisible}>{lisible}</code>{" "}
        <button type="button" className="bouton bouton-secondaire" onClick={copier}>
          {TEXTES.activation.copierCle}
        </button>
      </p>
      <p role="status">{copiee ? TEXTES.activation.cleCopiee : ""}</p>
    </>
  );
}
