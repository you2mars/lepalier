import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { dateEnToutesLettres } from "@/lib/format";
import { TEXTES } from "@/textes";
import { Activation } from "../Activation";
import { CodesDeSecours } from "./CodesDeSecours";
import Page from "./page";

const T = TEXTES.codes;
const remplacer = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: remplacer }),
  redirect: (adresse: string) => {
    throw new Error(`redirection ${adresse}`);
  },
}));

const CODES = Array.from({ length: 10 }, (_, i) => `ABCD-EFGH-JK${String(i).padStart(2, "0")}`);

function afficher() {
  return render(<CodesDeSecours codes={CODES} nomAffiche="Mme Durand" />);
}

const caseNotes = () => screen.getByRole("checkbox", { name: T.caseNotes });
const continuer = () => userEvent.click(screen.getByRole("button", { name: T.continuer }));

beforeEach(() => remplacer.mockReset());
afterEach(() => vi.unstubAllGlobals());

describe("Codes de secours : affichage (maquettes v3, écran 4 ; ADR 0006, R0-05)", () => {
  it("titre de l'écran, focus dessus, titre de l'onglet", () => {
    afficher();
    const titre = screen.getByRole("heading", { level: 1 });
    expect(titre).toHaveTextContent(T.titre);
    expect(titre).toHaveFocus();
    expect(document.title).toBe("Vos codes de secours — LePalier");
  });

  it("consigne et rappel permanent « Ne fermez pas cette page… »", () => {
    afficher();
    for (const phrase of T.consigne) expect(screen.getByText(phrase)).toBeInTheDocument();
    expect(screen.getByText(T.neFermezPas)).toHaveClass("rappel-permanent");
  });

  it("les 10 codes en liste numérotée, police à chasse fixe", () => {
    afficher();
    const liste = screen.getByRole("list", { name: T.titre });
    expect(liste.tagName).toBe("OL");
    expect(liste).toHaveClass("codes");
    expect(within(liste).getAllByRole("listitem").map((li) => li.textContent)).toEqual(CODES);
  });

  it("« Imprimer » (bouton secondaire) ouvre l'impression du navigateur", async () => {
    const imprimer = vi.fn();
    vi.stubGlobal("print", imprimer);
    afficher();
    const bouton = screen.getByRole("button", { name: T.imprimer });
    expect(bouton).toHaveAttribute("type", "button");
    await userEvent.click(bouton);
    expect(imprimer).toHaveBeenCalledOnce();
  });

  it("un seul bouton principal « Continuer vers l'accueil », jamais désactivé", () => {
    afficher();
    const principaux = screen.getAllByRole("button").filter((b) => b.getAttribute("type") === "submit");
    expect(principaux).toHaveLength(1);
    expect(principaux[0]).toHaveTextContent(T.continuer);
    expect(principaux[0]).toBeEnabled();
  });
});

describe("Codes de secours : feuille imprimée (UX-10)", () => {
  it("LePalier, titre, nom affiché, date d'édition, les 10 codes et la consigne d'usage ; ignorée à l'écran", () => {
    const { container } = afficher();
    const feuille = container.querySelector(".feuille-impression") as HTMLElement;
    expect(feuille).toHaveAttribute("aria-hidden", "true");
    expect(feuille).toHaveTextContent(TEXTES.application);
    expect(feuille).toHaveTextContent(T.titre);
    expect(feuille).toHaveTextContent("Mme Durand");
    expect(feuille).toHaveTextContent(`${T.imprimeLe} ${dateEnToutesLettres(new Date())}`);
    // format du lexique : jour de la semaine compris (« Imprimé le mardi 6 octobre 2026 »)
    expect(feuille.textContent).toMatch(/Imprimé le (lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche) /);
    expect(feuille).toHaveTextContent(T.barrezApresUsage);
    for (const code of CODES) expect(feuille).toHaveTextContent(code);
  });
});

describe("Codes de secours : case « J'ai noté mes codes »", () => {
  it("non cochée : message sous la case, focus dessus, on reste sur l'écran", async () => {
    afficher();
    await continuer();
    expect(caseNotes()).toHaveAccessibleDescription(T.caseNonCochee);
    expect(caseNotes()).toHaveAttribute("aria-invalid", "true");
    expect(caseNotes()).toHaveFocus();
    expect(remplacer).not.toHaveBeenCalled();
  });

  it("cochée : message effacé, accueil avec le bandeau « compte activé », sans retour possible aux codes", async () => {
    afficher();
    await continuer();
    await userEvent.click(caseNotes());
    expect(caseNotes()).not.toHaveAccessibleDescription(T.caseNonCochee);
    await continuer();
    expect(remplacer).toHaveBeenCalledWith("/?motif=compte_active");
  });
});

describe("Codes de secours : avertissement du navigateur avant de quitter ou recharger", () => {
  function quitter(): boolean {
    const evenement = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(evenement);
    return evenement.defaultPrevented;
  }

  it("tant que la case n'est pas cochée : le navigateur demande confirmation", () => {
    afficher();
    expect(quitter()).toBe(true);
  });

  it("case cochée : plus d'avertissement ; décochée : il revient", async () => {
    afficher();
    await userEvent.click(caseNotes());
    expect(quitter()).toBe(false);
    await userEvent.click(caseNotes());
    expect(quitter()).toBe(true);
  });

  it("écran quitté (démontage) : l'avertissement est retiré", () => {
    const { unmount } = afficher();
    unmount();
    expect(quitter()).toBe(false);
  });
});

describe("Codes de secours : rechargement de la page", () => {
  it("/activation/codes chargée de nouveau : codes perdus, accueil avec le bandeau qui le dit", () => {
    expect(() => Page()).toThrow("redirection /?motif=codes_perdus");
  });
});

describe("Activer mon compte puis codes de secours (même page, codes en mémoire seulement)", () => {
  it("après l'activation : écran des codes, adresse /activation/codes", async () => {
    window.history.replaceState(null, "", `/activation#${"a".repeat(43)}`);
    const reponses: Record<string, unknown> = {
      "/api/identity/auth/activation/debut": {
        uri_otpauth: "otpauth://totp/LePalier:x?secret=JBSWY3DPEHPK3PXP&issuer=LePalier",
        nom_affiche: "Mme Durand",
        email: "marie.durand@exemple.fr",
      },
      "/api/identity/auth/activation/fin": {
        etape: "confirmation_codes",
        codes_secours: CODES,
        nom_affiche: "Mme Durand",
        role: "associe",
      },
    };
    vi.stubGlobal(
      "fetch",
      vi.fn((chemin: string) =>
        Promise.resolve(
          new Response(JSON.stringify(reponses[chemin]), { headers: { "Content-Type": "application/json" } }),
        ),
      ),
    );
    render(<Activation />);
    await userEvent.click(await screen.findByRole("button", { name: TEXTES.activation.continuer }));
    await userEvent.type(screen.getByLabelText(TEXTES.activation.motDePasse), "le chat dort sur le toit");
    await userEvent.click(screen.getByRole("button", { name: TEXTES.activation.continuer }));
    await userEvent.type(screen.getByLabelText(TEXTES.activation.libelleCode), "123456");
    await userEvent.click(screen.getByRole("button", { name: TEXTES.activation.bouton }));
    await waitFor(() => expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(T.titre));
    expect(window.location.pathname).toBe("/activation/codes");
    expect(window.location.hash).toBe("");
    expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toEqual(CODES);
  });
});
