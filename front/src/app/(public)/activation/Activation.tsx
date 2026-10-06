"use client";
// Activation puis codes de secours : les codes renvoyés par activation/fin ne vivent que dans la mémoire de cette
// page (maquettes v3, écran 4) ; l'écran des codes de secours se branche ici.
import { useState } from "react";
import { type Activee, FormulaireActivation } from "./FormulaireActivation";

export function Activation() {
  const [activee, setActivee] = useState<Activee | null>(null);
  if (activee === null) return <FormulaireActivation surActivation={setActivee} />;
  // écran 4 (Codes de secours) : étape suivante de l'étape 7
  return null;
}
