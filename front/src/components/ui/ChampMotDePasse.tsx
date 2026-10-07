"use client";
// Mot de passe (front/CLAUDE.md, M12, Q9) : masqué par défaut, bouton « Afficher » / « Masquer » (aria-pressed) ;
// correcteur et majuscule automatique désactivés, y compris quand le champ passe en texte. Deux champs sur un même
// écran (mot de passe et confirmation) : noms accessibles propres au second, pour être lus sans ambiguïté.
import { useState } from "react";
import { TEXTES } from "@/textes";
import { Champ, type ProprietesChamp } from "./Champ";

type Props = Omit<ProprietesChamp, "type" | "autoComplete" | "apres"> & {
  autoComplete: "current-password" | "new-password";
  nomsAccessibles?: { afficher: string; masquer: string };
};

const NOMS = { afficher: TEXTES.motDePasse.afficherAccessible, masquer: TEXTES.motDePasse.masquerAccessible };

export function ChampMotDePasse({ nomsAccessibles = NOMS, ...props }: Props) {
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
          aria-label={visible ? nomsAccessibles.masquer : nomsAccessibles.afficher}
          onClick={() => setVisible((v) => !v)}
        >
          {visible ? TEXTES.motDePasse.masquer : TEXTES.motDePasse.afficher}
        </button>
      }
    />
  );
}
