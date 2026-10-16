"use client";
// Formulaire commun (UX-19, UX-22) : POST sans validation du navigateur, envoi traité par la page. Vérification à la
// sortie de chaque champ (verifierALaSortie de Champ, ChampMotDePasse), sauf quand le pointeur (souris, doigt) appuie
// sur un bouton d'envoi : un message affiché entre l'appui et le relâchement déplacerait le bouton et le clic serait
// perdu ; l'envoi vérifie alors tout. Au clavier, la vérification à la sortie reste entière.
// Constat UX (18) : sur un téléphone lent, la personne tape avant la prise en main du formulaire par React (la page
// peut arriver en flux, ce formulaire après le reste) ; les champs restent affichés remplis, mais l'état de React les
// croit vides. À sa prise en main, le formulaire rejoue chaque saisie pour React, puis porte data-pret : le script en
// ligne EnvoiApresPriseEnMain annule tout envoi d'un formulaire qui ne le porte pas encore.
import {
  createContext,
  type FormEvent,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
} from "react";

type Sortie = { aLaSortie: (verifier: () => void) => void };

const ContexteFormulaire = createContext<Sortie>({ aLaSortie: (verifier) => verifier() });

const SANS_SAISIE = ["hidden", "radio", "checkbox", "submit", "button", "file"];

function rejouerLesSaisies(formulaire: HTMLFormElement): void {
  for (const champ of formulaire.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("input, textarea")) {
    if (SANS_SAISIE.includes(champ.type) || champ.value === "") continue;
    const valeur = champ.value;
    // vidé par l'accesseur que suit React, puis remis par l'accesseur natif : React voit une saisie et appelle
    // onChange avec la valeur affichée ; sans effet si son état la contenait déjà
    const natif = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(champ) as object, "value");
    champ.value = "";
    natif?.set?.call(champ, valeur);
    champ.dispatchEvent(new Event("input", { bubbles: true }));
  }
}

// pour les champs : enveloppe leur vérification de sortie
export function useVerificationALaSortie(): Sortie["aLaSortie"] {
  return useContext(ContexteFormulaire).aLaSortie;
}

export function Formulaire({
  onSubmit,
  children,
}: {
  onSubmit: (evenement: FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
}) {
  const appuiSurEnvoi = useRef(false);
  const formulaire = useRef<HTMLFormElement>(null);

  useEffect(() => {
    const element = formulaire.current;
    if (!element) return;
    rejouerLesSaisies(element);
    element.setAttribute("data-pret", "");
  }, []);

  const aLaSortie = useCallback((verifier: () => void) => {
    if (appuiSurEnvoi.current) {
      appuiSurEnvoi.current = false;
      return;
    }
    verifier();
  }, []);
  const contexte = useMemo(() => ({ aLaSortie }), [aLaSortie]);

  return (
    <ContexteFormulaire.Provider value={contexte}>
      <form
        ref={formulaire}
        method="post"
        noValidate
        onPointerDownCapture={(e) => {
          const bouton = (e.target as Element).closest("button");
          appuiSurEnvoi.current = bouton !== null && bouton.type === "submit";
        }}
        onSubmit={(e) => {
          e.preventDefault();
          appuiSurEnvoi.current = false;
          onSubmit(e);
        }}
      >
        {children}
      </form>
    </ContexteFormulaire.Provider>
  );
}
