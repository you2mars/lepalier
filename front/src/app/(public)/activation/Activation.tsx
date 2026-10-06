"use client";
// Activation puis codes de secours : les codes renvoyés par activation/fin ne vivent que dans la mémoire de cette
// page (maquettes v3, écran 4) ; l'adresse devient /activation/codes, qui, rechargée, mène à l'accueil.
import { useState } from "react";
import { CodesDeSecours } from "./codes/CodesDeSecours";
import { type Activee, FormulaireActivation } from "./FormulaireActivation";

export function Activation() {
  const [activee, setActivee] = useState<Activee | null>(null);

  function surActivation(resultat: Activee) {
    window.history.replaceState(window.history.state, "", "/activation/codes");
    setActivee(resultat);
  }

  if (activee === null) return <FormulaireActivation surActivation={surActivation} />;
  return <CodesDeSecours codes={activee.codes_secours} nomAffiche={activee.nom_affiche} />;
}
