import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BandeauFlash, laisserMessage, MessageFlashProvider } from "./MessageFlash";

let chemin = "/administration/utilisateurs";
vi.mock("next/navigation", () => ({ usePathname: () => chemin }));

const ANNULATION = { etat: "fait" as const, texte: "Invitation de Mme Durand annulée.", pour: "/administration/utilisateurs" };

// page chargée en entier par le navigateur (navigation complète) : nouveau cadre, nouvelle mémoire
function chargerLaPage() {
  return render(
    <MessageFlashProvider>
      <BandeauFlash />
    </MessageFlashProvider>,
  );
}

beforeEach(() => {
  chemin = "/administration/utilisateurs";
  sessionStorage.clear();
});
afterEach(() => vi.restoreAllMocks());

// Message d'une page à la suivante, au travers d'une navigation complète : laissé par la page de départ dans le
// stockage de session de l'onglet, lu puis effacé par la page d'arrivée.
describe("MessageFlash", () => {
  it("laissé par la fiche : affiché sur la page d'arrivée, puis effacé (perdu au rechargement)", () => {
    laisserMessage(ANNULATION);
    const { unmount } = chargerLaPage();
    expect(screen.getByRole("status")).toHaveTextContent("Invitation de Mme Durand annulée.");
    expect(sessionStorage.length).toBe(0);
    unmount();
    chargerLaPage();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("autre page d'arrivée : rien d'affiché, message effacé", () => {
    laisserMessage(ANNULATION);
    chemin = "/";
    chargerLaPage();
    expect(screen.queryByRole("status")).toBeNull();
    expect(sessionStorage.length).toBe(0);
  });

  it("contenu illisible ou incomplet : rien d'affiché, jamais d'erreur", () => {
    sessionStorage.setItem("lepalier.message", "{pas du json");
    const { unmount } = chargerLaPage();
    expect(screen.queryByRole("status")).toBeNull();
    unmount();
    sessionStorage.setItem("lepalier.message", JSON.stringify({ etat: "inconnu", texte: 3, pour: chemin }));
    chargerLaPage();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("stockage refusé par le navigateur : ni le départ ni l'arrivée ne cassent", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("refusé", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("refusé", "SecurityError");
    });
    expect(() => laisserMessage(ANNULATION)).not.toThrow();
    chargerLaPage();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("message donné au cadre (essais des écrans) : affiché sur sa page", () => {
    render(
      <MessageFlashProvider initial={ANNULATION}>
        <BandeauFlash />
      </MessageFlashProvider>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Invitation de Mme Durand annulée.");
  });
});
