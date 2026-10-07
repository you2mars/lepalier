"use client";
// Formulaire commun (UX-19, UX-22) : POST sans validation du navigateur, envoi traité par la page. Vérification à la
// sortie de chaque champ (verifierALaSortie de Champ, ChampMotDePasse), sauf quand le pointeur (souris, doigt) appuie
// sur un bouton d'envoi : un message affiché entre l'appui et le relâchement déplacerait le bouton et le clic serait
// perdu ; l'envoi vérifie alors tout. Au clavier, la vérification à la sortie reste entière.
import { createContext, type FormEvent, type ReactNode, useCallback, useContext, useMemo, useRef } from "react";

type Sortie = { aLaSortie: (verifier: () => void) => void };

const ContexteFormulaire = createContext<Sortie>({ aLaSortie: (verifier) => verifier() });

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
