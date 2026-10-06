"use client";
// Mot de passe (front/CLAUDE.md, M12, Q9) : masqué par défaut, bouton « Afficher » / « Masquer » (aria-pressed) ;
// correcteur et majuscule automatique désactivés, y compris quand le champ passe en texte.
import { useState } from "react";
import { TEXTES } from "@/textes";
import { Champ, type ProprietesChamp } from "./Champ";

type Props = Omit<ProprietesChamp, "type" | "autoComplete" | "apres"> & {
  autoComplete: "current-password" | "new-password";
};

export function ChampMotDePasse(props: Props) {
  const [visible, setVisible] = useState(false);
  return (
    <Champ
      {...props}
      type={visible ? "text" : "password"}
      autoCapitalize="none"
      autoCorrect="off"
      spellCheck={false}
      apres={
        <button
          type="button"
          className="bouton bouton-texte"
          aria-pressed={visible}
          aria-label={visible ? TEXTES.motDePasse.masquerAccessible : TEXTES.motDePasse.afficherAccessible}
          onClick={() => setVisible((v) => !v)}
        >
          {visible ? TEXTES.motDePasse.masquer : TEXTES.motDePasse.afficher}
        </button>
      }
    />
  );
}
