"use client";
// Signal pour les essais de bout en bout : posé sur <html> une fois la page prise en main par React (hydratation).
// Un essai qui agit avant (clic, saisie) verrait son action perdue ou défaite ; sans effet pour les utilisateurs.
import { useEffect } from "react";

export function SignalHydratation() {
  useEffect(() => {
    document.documentElement.setAttribute("data-hydrate", "");
  }, []);
  return null;
}
