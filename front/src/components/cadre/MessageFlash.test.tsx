import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BandeauFlash, MessageFlashProvider, useAnnonce } from "./MessageFlash";

let chemin = "/administration/utilisateurs/0192-b";
vi.mock("next/navigation", () => ({ usePathname: () => chemin }));

function Annonceur() {
  const annoncer = useAnnonce();
  return (
    <button
      type="button"
      onClick={() => annoncer({ etat: "fait", texte: "Invitation de Mme Durand annulée.", pour: "/administration/utilisateurs" })}
    >
      Annuler
    </button>
  );
}

function Cadre() {
  return (
    <MessageFlashProvider>
      <Annonceur />
      <BandeauFlash />
    </MessageFlashProvider>
  );
}

// Message d'une page à la suivante : annoncé sur la fiche, affiché sur la liste, oublié ailleurs.
describe("MessageFlash", () => {
  it("annoncé sur la fiche : pas affiché là, gardé ; affiché sur la page d'arrivée ; oublié dès qu'on va ailleurs", async () => {
    chemin = "/administration/utilisateurs/0192-b";
    const { rerender } = render(<Cadre />);
    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));
    expect(screen.queryByRole("status")).toBeNull();

    chemin = "/administration/utilisateurs";
    rerender(<Cadre />);
    expect(screen.getByRole("status")).toHaveTextContent("Invitation de Mme Durand annulée.");

    chemin = "/";
    rerender(<Cadre />);
    expect(screen.queryByRole("status")).toBeNull();

    chemin = "/administration/utilisateurs";
    rerender(<Cadre />);
    expect(screen.queryByRole("status")).toBeNull();
  });
});
