import { render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EnvoiApresPriseEnMain, SCRIPT_ENVOI_APRES_PRISE_EN_MAIN } from "./EnvoiApresPriseEnMain";

// Constat UX (18) : un formulaire envoyé avant la prise en main par React partait en POST vers la page, vidé.
vi.mock("next/headers", () => ({ headers: async () => ({ get: (nom: string) => (nom === "x-nonce" ? "nonce-essai" : null) }) }));

function envoyer(pret = false): boolean {
  const formulaire = document.createElement("form");
  if (pret) formulaire.setAttribute("data-pret", "");
  document.body.append(formulaire);
  const evenement = new Event("submit", { bubbles: true, cancelable: true });
  formulaire.dispatchEvent(evenement);
  formulaire.remove();
  return evenement.defaultPrevented;
}

let retirer: (() => void) | undefined;
beforeEach(() => {
  const ajouter = document.addEventListener.bind(document);
  const ecouteurs: [string, EventListenerOrEventListenerObject, boolean | AddEventListenerOptions | undefined][] = [];
  vi.spyOn(document, "addEventListener").mockImplementation((type, ecouteur, options) => {
    ecouteurs.push([type, ecouteur, options]);
    ajouter(type, ecouteur, options);
  });
  retirer = () => ecouteurs.forEach(([t, e, o]) => document.removeEventListener(t, e, o));
});
afterEach(() => {
  retirer?.();
  vi.restoreAllMocks();
});

describe("envoi bloqué avant la prise en main de la page (constat UX (18))", () => {
  it("formulaire pas encore pris en main (sans data-pret) : l'envoi est annulé", () => {
    new Function(SCRIPT_ENVOI_APRES_PRISE_EN_MAIN)();
    expect(envoyer()).toBe(true);
  });

  it("formulaire prêt (data-pret) : l'envoi n'est plus touché, React le prend en charge", () => {
    new Function(SCRIPT_ENVOI_APRES_PRISE_EN_MAIN)();
    expect(envoyer(true)).toBe(false);
  });

  it("script en ligne portant le nonce de la politique de sécurité", async () => {
    const { container } = render(await EnvoiApresPriseEnMain());
    const script = container.querySelector("script");
    expect(script?.getAttribute("nonce")).toBe("nonce-essai");
    expect(script?.textContent).toBe(SCRIPT_ENVOI_APRES_PRISE_EN_MAIN);
  });
});
