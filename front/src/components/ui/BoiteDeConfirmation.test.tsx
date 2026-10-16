import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { BoiteDeConfirmation } from "./BoiteDeConfirmation";

// Boîte de confirmation récapitulative (UX-3, maquettes v3 § 0.5) : la question est le titre ; focus d'abord sur
// le choix qui n'agit pas ; Échap = ce choix ; au retour, le focus revient au bouton qui l'a ouverte.
function Essai({ confirmer = vi.fn(), envoiEnCours = false }: { confirmer?: () => void; envoiEnCours?: boolean }) {
  const [ouverte, setOuverte] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOuverte(true)}>
        Ouvrir
      </button>
      <BoiteDeConfirmation
        ouverte={ouverte}
        titre="Envoyer l'invitation à Mme Durand ?"
        libelleConfirmer="Envoyer l'invitation"
        libelleAnnuler="Modifier"
        envoiEnCours={envoiEnCours}
        surConfirmer={confirmer}
        surAnnuler={() => setOuverte(false)}
      >
        <p>Le lien sera valable 7 jours.</p>
      </BoiteDeConfirmation>
    </>
  );
}

describe("BoiteDeConfirmation", () => {
  it("fermée : rien n'est affiché", () => {
    render(<Essai />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("ouverte : boîte nommée par sa question, récapitulatif, focus sur le choix qui n'agit pas", async () => {
    render(<Essai />);
    await userEvent.click(screen.getByRole("button", { name: "Ouvrir" }));
    const boite = screen.getByRole("dialog", { name: "Envoyer l'invitation à Mme Durand ?" });
    expect(boite).toHaveTextContent("Le lien sera valable 7 jours.");
    expect(screen.getByRole("button", { name: "Modifier" })).toHaveFocus();
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Envoyer l'invitation à Mme Durand ?");
  });

  it("« Modifier » : boîte fermée, focus rendu au bouton qui l'a ouverte, rien n'est fait", async () => {
    const confirmer = vi.fn();
    render(<Essai confirmer={confirmer} />);
    const ouvrir = screen.getByRole("button", { name: "Ouvrir" });
    await userEvent.click(ouvrir);
    await userEvent.click(screen.getByRole("button", { name: "Modifier" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(ouvrir).toHaveFocus();
    expect(confirmer).not.toHaveBeenCalled();
  });

  it("Échap (événement cancel de la boîte) : même effet que « Modifier »", async () => {
    render(<Essai />);
    await userEvent.click(screen.getByRole("button", { name: "Ouvrir" }));
    fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByRole("button", { name: "Ouvrir" })).toHaveFocus();
  });

  it("confirmer : l'action est demandée une fois", async () => {
    const confirmer = vi.fn();
    render(<Essai confirmer={confirmer} />);
    await userEvent.click(screen.getByRole("button", { name: "Ouvrir" }));
    await userEvent.click(screen.getByRole("button", { name: "Envoyer l'invitation" }));
    expect(confirmer).toHaveBeenCalledOnce();
  });

  it("pendant l'envoi : bouton désactivé, « Envoi en cours… » (UX-22)", async () => {
    render(<Essai envoiEnCours />);
    await userEvent.click(screen.getByRole("button", { name: "Ouvrir" }));
    expect(screen.getByRole("button", { name: "Envoi en cours…" })).toBeDisabled();
  });
});
