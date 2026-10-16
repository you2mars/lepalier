"use client";
// Boîte de confirmation récapitulative (UX-3, maquettes v3 § 0.5) : boîte modale du navigateur (<dialog>,
// arrière-plan inerte, Échap) ; la question est le titre ; focus d'abord sur le choix qui n'agit pas (« Annuler »,
// « Modifier »…) ; Échap = ce choix ; à la fermeture, le focus revient au bouton qui l'a ouverte. Verbes explicites,
// jamais « OK » ni « Continuer ».
import { type ReactNode, useEffect, useId, useRef } from "react";
import { Actions } from "./Actions";
import { Bouton } from "./Bouton";

type Props = {
  ouverte: boolean;
  titre: string;
  children: ReactNode;
  libelleConfirmer: string;
  libelleAnnuler: string;
  surConfirmer: () => void;
  surAnnuler: () => void;
  envoiEnCours?: boolean;
};

export function BoiteDeConfirmation({
  ouverte,
  titre,
  children,
  libelleConfirmer,
  libelleAnnuler,
  surConfirmer,
  surAnnuler,
  envoiEnCours = false,
}: Props) {
  const boite = useRef<HTMLDialogElement>(null);
  const annuler = useRef<HTMLButtonElement>(null);
  const ouvreur = useRef<HTMLElement | null>(null);
  const idTitre = useId();

  useEffect(() => {
    const element = boite.current;
    if (!element) return;
    if (ouverte && !element.open) {
      ouvreur.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      element.showModal();
      annuler.current?.focus();
    } else if (!ouverte && element.open) {
      element.close();
      ouvreur.current?.focus();
    }
  }, [ouverte]);

  return (
    <dialog
      ref={boite}
      className="boite-de-confirmation"
      aria-labelledby={idTitre}
      onCancel={(e) => {
        // Échap : le navigateur fermerait la boîte seul ; c'est la page qui décide (comme « Annuler »)
        e.preventDefault();
        surAnnuler();
      }}
    >
      {ouverte ? (
        <>
          <h2 id={idTitre}>{titre}</h2>
          {children}
          <Actions>
            <Bouton type="button" envoiEnCours={envoiEnCours} onClick={surConfirmer}>
              {libelleConfirmer}
            </Bouton>
            <Bouton ref={annuler} variante="secondaire" onClick={surAnnuler} disabled={envoiEnCours}>
              {libelleAnnuler}
            </Bouton>
          </Actions>
        </>
      ) : null}
    </dialog>
  );
}
