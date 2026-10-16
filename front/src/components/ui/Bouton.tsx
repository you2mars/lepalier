// Boutons (design system § 9) : principal (envoie le formulaire) ou secondaire ; pendant l'envoi, désactivé avec
// « Envoi en cours… » : double soumission impossible (UX-22).
import type { ButtonHTMLAttributes, Ref } from "react";
import { TEXTES } from "@/textes";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: "principal" | "secondaire";
  envoiEnCours?: boolean;
  ref?: Ref<HTMLButtonElement>;
};

export function Bouton({ variante = "principal", envoiEnCours = false, type, className, children, ...reste }: Props) {
  return (
    <button
      {...reste}
      type={type ?? (variante === "principal" ? "submit" : "button")}
      className={["bouton", `bouton-${variante}`, className].filter(Boolean).join(" ")}
      disabled={envoiEnCours || reste.disabled}
      aria-busy={envoiEnCours || undefined}
    >
      {envoiEnCours ? TEXTES.envoiEnCours : children}
    </button>
  );
}
