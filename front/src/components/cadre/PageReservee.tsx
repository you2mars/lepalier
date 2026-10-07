// Page réservée au gérant (maquettes v3, écran 7 ; R0-06) : une page d'administration ouverte par un associé ou un
// opérateur, ou refusée par l'API (403) ; jamais une page blanche ; retour à l'accueil en bouton principal (Q3).
import { LienBouton } from "@/components/ui/LienBouton";
import { TEXTES } from "@/textes";

export function PageReservee() {
  return (
    <>
      <h1>{TEXTES.reservee.titre}</h1>
      <p>{TEXTES.reservee.reservee}</p>
      <p>{TEXTES.reservee.demandez}</p>
      <p>
        <LienBouton href="/" variante="principal">
          {TEXTES.retourAccueil}
        </LienBouton>
      </p>
    </>
  );
}
