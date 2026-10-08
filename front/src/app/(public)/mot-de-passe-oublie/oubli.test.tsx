import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { libelle } from "@/lib/libelles";
import { TEXTES } from "@/textes";
import { FormulaireOubli } from "./FormulaireOubli";
import { metadata } from "./page";

const T = TEXTES.reinitialisation.demande;

function reponse(statut: number, corps: unknown): Response {
  return new Response(JSON.stringify(corps), { status: statut, headers: { "Content-Type": "application/json" } });
}

const adresse = () => screen.getByLabelText(T.adresse);

afterEach(() => vi.unstubAllGlobals());

describe("Mot de passe oublié (maquettes v3, écran 8 ; ADR 0006)", () => {
  it("titre, onglet, consigne, adresse (attributs du champ), un seul bouton principal, « Retour à la connexion »", () => {
    render(<FormulaireOubli />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(T.titre);
    expect(metadata.title).toBe("Mot de passe oublié — LePalier");
    expect(screen.getByText(T.consigne)).toBeInTheDocument();
    expect(adresse()).toHaveAttribute("type", "email");
    expect(adresse()).toHaveAttribute("autocomplete", "username");
    expect(adresse()).toHaveAttribute("inputmode", "email");
    expect(adresse()).toHaveAttribute("autocapitalize", "none");
    expect(adresse()).toHaveAttribute("spellcheck", "false");
    expect(screen.getAllByRole("button").filter((b) => b.getAttribute("type") === "submit")).toHaveLength(1);
    expect(screen.getByRole("button", { name: T.bouton })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: T.retour })).toHaveAttribute("href", "/connexion");
  });

  it("adresse incorrecte : message sous le champ à la sortie ; à l'envoi, rien n'est demandé", async () => {
    const appel = vi.fn();
    vi.stubGlobal("fetch", appel);
    render(<FormulaireOubli />);
    await userEvent.type(adresse(), "marie");
    await userEvent.tab();
    expect(adresse()).toHaveAccessibleDescription(libelle("utilisateurs.email_invalide"));
    await userEvent.click(screen.getByRole("button", { name: T.bouton }));
    expect(adresse()).toHaveFocus();
    expect(appel).not.toHaveBeenCalled();
  });

  it("envoi : POST reinitialisation/demande ; le formulaire disparaît, bandeau « Fait », le lien de retour reste", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(202, { message: libelle("reinitialisation.demande_envoyee") }));
    vi.stubGlobal("fetch", appel);
    render(<FormulaireOubli />);
    await userEvent.type(adresse(), "marie.durand@exemple.fr");
    await userEvent.click(screen.getByRole("button", { name: T.bouton }));
    const bandeau = await screen.findByRole("status");
    expect(bandeau).toHaveTextContent(TEXTES.etats.fait);
    expect(bandeau).toHaveTextContent(libelle("reinitialisation.demande_envoyee"));
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("button", { name: T.bouton })).toBeNull();
    expect(screen.getByRole("link", { name: T.retour })).toBeInTheDocument();
    expect(appel.mock.calls[0]![0]).toBe("/api/identity/auth/reinitialisation/demande");
    expect(JSON.parse((appel.mock.calls[0] as [string, RequestInit])[1].body as string)).toEqual({
      email: "marie.durand@exemple.fr",
    });
  });

  it("après l'envoi : l'adresse saisie est rappelée ; « Saisir une autre adresse » rouvre le formulaire, adresse gardée (revue UX, M5)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(202, { message: libelle("reinitialisation.demande_envoyee") })));
    render(<FormulaireOubli />);
    await userEvent.type(adresse(), "marie.durnad@exemple.fr");
    await userEvent.click(screen.getByRole("button", { name: T.bouton }));
    await screen.findByRole("status");
    expect(screen.getByText(T.adresseSaisie).closest("p")).toHaveTextContent(`${T.adresseSaisie} marie.durnad@exemple.fr`);
    await userEvent.click(screen.getByRole("button", { name: T.autreAdresse }));
    expect(adresse()).toHaveValue("marie.durnad@exemple.fr");
    expect(adresse()).toHaveFocus();
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("trop de demandes (429) : bandeau « Attention », formulaire gardé", async () => {
    const message = "Trop de demandes en peu de temps. Patientez une minute, puis réessayez.";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(429, { code: "trop_de_requetes", message, details: {} })));
    render(<FormulaireOubli />);
    await userEvent.type(adresse(), "marie.durand@exemple.fr");
    await userEvent.click(screen.getByRole("button", { name: T.bouton }));
    const bandeau = await screen.findByRole("alert");
    expect(bandeau).toHaveTextContent(TEXTES.etats.attention);
    expect(bandeau).toHaveTextContent(message);
    expect(adresse()).toHaveValue("marie.durand@exemple.fr");
  });

  it("panne : bandeau « Erreur » ; pendant l'envoi : « Envoi en cours… »", async () => {
    let terminer: (r: Response) => void = () => undefined;
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise<Response>((r) => (terminer = r))));
    render(<FormulaireOubli />);
    await userEvent.type(adresse(), "marie.durand@exemple.fr");
    await userEvent.click(screen.getByRole("button", { name: T.bouton }));
    expect(screen.getByRole("button", { name: TEXTES.envoiEnCours })).toBeDisabled();
    terminer(new Response("panne", { status: 500 }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(TEXTES.commun.erreurInattendue));
  });
});
