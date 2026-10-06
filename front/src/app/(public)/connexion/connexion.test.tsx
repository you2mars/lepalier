import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { libelle } from "@/lib/libelles";
import { TEXTES } from "@/textes";
import { FormulaireConnexion } from "./FormulaireConnexion";
import Page, { metadata } from "./page";

const pousser = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pousser }) }));

function reponse(statut: number, corps: unknown): Response {
  return new Response(JSON.stringify(corps), { status: statut, headers: { "Content-Type": "application/json" } });
}

async function remplirEtEnvoyer(email = "marie.durand@exemple.fr", motDePasse = "le chat dort sur le toit") {
  await userEvent.type(screen.getByLabelText(TEXTES.connexion.adresse), email);
  await userEvent.type(screen.getByLabelText(TEXTES.connexion.motDePasse), motDePasse);
  await userEvent.click(screen.getByRole("button", { name: TEXTES.connexion.bouton }));
}

beforeEach(() => pousser.mockReset());
afterEach(() => vi.unstubAllGlobals());

describe("Se connecter : structure (R0-01, UX-1, front/CLAUDE.md)", () => {
  it("titre et seul bouton principal « Se connecter », lien « Mot de passe oublié »", () => {
    render(<FormulaireConnexion />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(TEXTES.connexion.titre);
    expect(screen.getAllByRole("button").filter((b) => b.getAttribute("type") === "submit")).toHaveLength(1);
    expect(screen.getByRole("link", { name: TEXTES.connexion.oublie })).toHaveAttribute("href", "/mot-de-passe-oublie");
  });

  it("adresse e-mail : type, remplissage et anti-correcteur", () => {
    render(<FormulaireConnexion />);
    const adresse = screen.getByLabelText(TEXTES.connexion.adresse);
    expect(adresse).toHaveAttribute("type", "email");
    expect(adresse).toHaveAttribute("autocomplete", "username");
    expect(adresse).toHaveAttribute("inputmode", "email");
    expect(adresse).toHaveAttribute("autocapitalize", "none");
    expect(adresse).toHaveAttribute("autocorrect", "off");
    expect(adresse).toHaveAttribute("spellcheck", "false");
    expect(screen.getByLabelText(TEXTES.connexion.motDePasse)).toHaveAttribute("autocomplete", "current-password");
  });

  it("formulaire en POST : sans JavaScript, le mot de passe ne part jamais dans l'adresse", () => {
    const { container } = render(<FormulaireConnexion />);
    expect(container.querySelector("form")).toHaveAttribute("method", "post");
  });

  it("titre de l'onglet « Se connecter — LePalier »", () => {
    expect(metadata.title).toBe("Se connecter — LePalier");
  });
});

describe("Se connecter : envoi", () => {
  it("réussite : POST /api/identity/auth/connexion puis écran du code", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(200, { etape: "code" }));
    vi.stubGlobal("fetch", appel);
    render(<FormulaireConnexion />);
    await remplirEtEnvoyer();
    await waitFor(() => expect(pousser).toHaveBeenCalledWith("/connexion/code"));
    expect(appel.mock.calls[0]![0]).toBe("/api/identity/auth/connexion");
    expect(JSON.parse(appel.mock.calls[0]![1].body)).toEqual({
      email: "marie.durand@exemple.fr",
      mot_de_passe: "le chat dort sur le toit",
    });
  });

  it("réussite avec une page demandée : le chemin de retour, contrôlé, suit jusqu'à l'écran du code", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(200, { etape: "code" })));
    render(<FormulaireConnexion retour="/administration/utilisateurs" />);
    await remplirEtEnvoyer();
    await waitFor(() =>
      expect(pousser).toHaveBeenCalledWith("/connexion/code?retour=%2Fadministration%2Futilisateurs"),
    );
  });

  it("chemin de retour externe : ignoré", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(200, { etape: "code" })));
    render(<FormulaireConnexion retour="//pirate.example" />);
    await remplirEtEnvoyer();
    await waitFor(() => expect(pousser).toHaveBeenCalledWith("/connexion/code"));
  });

  it("mot de passe faux : message sous le champ, mot de passe vidé, adresse gardée, focus sur le champ (R0-24)", async () => {
    const message = libelle("connexion.identifiants_incorrects");
    const corps = { code: "identifiants_incorrects", message, details: { champs: [{ champ: "mot_de_passe", message }] } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(401, corps)));
    render(<FormulaireConnexion />);
    await remplirEtEnvoyer();
    const motDePasse = screen.getByLabelText(TEXTES.connexion.motDePasse);
    await waitFor(() => expect(motDePasse).toHaveAccessibleDescription(message));
    expect(motDePasse).toHaveValue("");
    expect(motDePasse).toHaveFocus();
    expect(screen.getByLabelText(TEXTES.connexion.adresse)).toHaveValue("marie.durand@exemple.fr");
    expect(pousser).not.toHaveBeenCalled();
  });

  it("trop d'essais (429) : bandeau « Attention » avec le message reçu", async () => {
    const message = libelle("connexion.trop_d_essais");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(429, { code: "trop_d_essais", message, details: {} })));
    render(<FormulaireConnexion />);
    await remplirEtEnvoyer();
    const bandeau = await screen.findByRole("alert");
    expect(bandeau).toHaveTextContent(TEXTES.etats.attention);
    expect(bandeau).toHaveTextContent(message);
  });

  it("panne réseau : bandeau « Erreur » avec le message de commun", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<FormulaireConnexion />);
    await remplirEtEnvoyer();
    const bandeau = await screen.findByRole("alert");
    expect(bandeau).toHaveTextContent(TEXTES.etats.erreur);
    expect(bandeau).toHaveTextContent(TEXTES.commun.erreurInattendue);
  });

  it("pendant l'envoi : bouton désactivé, « Envoi en cours… » (UX-22)", async () => {
    let terminer: (r: Response) => void = () => undefined;
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise<Response>((r) => (terminer = r))));
    render(<FormulaireConnexion />);
    await remplirEtEnvoyer();
    expect(screen.getByRole("button", { name: TEXTES.envoiEnCours })).toBeDisabled();
    terminer(reponse(200, { etape: "code" }));
    await waitFor(() => expect(pousser).toHaveBeenCalled());
  });
});

describe("Se connecter : bandeau d'arrivée selon le motif", () => {
  it.each([
    ["deconnexion", "status", TEXTES.etats.fait, TEXTES.connexion.deconnexionEffectuee],
    ["mot_de_passe_change", "status", TEXTES.etats.fait, TEXTES.connexion.motDePasseChange],
    ["session_expiree", "alert", TEXTES.etats.attention, TEXTES.commun.sessionExpiree],
    ["compte_suspendu", "alert", TEXTES.etats.attention, libelle("connexion.compte_suspendu")],
    ["delai_depasse", "alert", TEXTES.etats.attention, libelle("code.delai_depasse")],
    ["trop_de_codes", "alert", TEXTES.etats.attention, libelle("code.trop_de_codes")],
  ] as const)("%s", async (motif, role, mot, message) => {
    render(await Page({ searchParams: Promise.resolve({ motif }) }));
    const bandeau = screen.getByRole(role);
    expect(bandeau).toHaveTextContent(mot);
    expect(bandeau).toHaveTextContent(message);
  });

  it("motif inconnu ou absent : aucun bandeau", async () => {
    render(await Page({ searchParams: Promise.resolve({ motif: "inconnu" }) }));
    expect(screen.queryByRole("status")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
