// Bandeau de message (UX-4, UX-14) : mot d'état écrit, en gras sur sa propre ligne, jamais une couleur seule.
import { TEXTES } from "@/textes";

export type EtatBandeau = "fait" | "attention" | "erreur";

export function Bandeau({ etat, message }: { etat: EtatBandeau; message: string }) {
  return (
    <div className={`bandeau bandeau-${etat}`} role={etat === "fait" ? "status" : "alert"}>
      <p>
        <strong>{TEXTES.etats[etat]}</strong>
      </p>
      <p>{message}</p>
    </div>
  );
}
