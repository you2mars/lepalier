import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { libelle, messageMotDePasse } from "@/lib/libelles";
import { TEXTES } from "@/textes";
import { FormulaireReinitialisation } from "./FormulaireReinitialisation";
import { metadata } from "./page";

const C = TEXTES.reinitialisation.choix;
const M = TEXTES.motDePasse;
const JETON = "b".repeat(43);
const MOT_DE_PASSE = "le chat dort sur le toit";
const remplacer = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: remplacer }) }));

function reponse(statut: number, corps: unknown = null): Response {
  return corps === null
    ? new Response(null, { status: statut })
    : new Response(JSON.stringify(corps), { status: statut, headers: { "Content-Type": "application/json" } });
}

function refus(statut: number, code: string, message: string, champ?: string): Response {
  return reponse(statut, { code, message, details: champ ? { champs: [{ champ, message }] } : {}, trace_id: "t" });
}

const motDePasse = () => screen.getByLabelText(C.motDePasse);
const confirmation = () => screen.getByLabelText(M.confirmation);
const code = () => screen.getByLabelText(C.code);

async function remplir(mdp = MOT_DE_PASSE, conf = mdp, valeurCode = "123456") {
  await userEvent.type(motDePasse(), mdp);
  await userEvent.type(confirmation(), conf);
  await userEvent.type(code(), valeurCode);
}

const changer = () => userEvent.click(screen.getByRole("button", { name: C.bouton }));

beforeEach(() => {
  remplacer.mockReset();
  window.history.replaceState(null, "", `/reinitialisation#${JETON}`);
});
afterEach(() => vi.unstubAllGlobals());

describe("Choisir un nouveau mot de passe : écran (maquettes v3, écran 9 ; ADR 0006)", () => {
  it("titre, onglet ; mot de passe et confirmation (nouveau mot de passe, « Afficher » propres) ; code ; un seul bouton principal", () => {
    render(<FormulaireReinitialisation />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(C.titre);
    expect(metadata.title).toBe("Choisir un nouveau mot de passe — LePalier");
    expect(motDePasse()).toHaveAttribute("autocomplete", "new-password");
    expect(motDePasse()).toHaveAccessibleDescription(TEXTES.activation.aideMotDePasse);
    expect(confirmation()).toHaveAttribute("autocomplete", "new-password");
    expect(screen.getByRole("button", { name: M.afficherAccessible })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: M.afficherConfirmationAccessible })).toBeInTheDocument();
    expect(code()).toHaveAttribute("inputmode", "numeric");
    expect(code()).toHaveAttribute("autocomplete", "one-time-code");
    expect(code()).toHaveAccessibleDescription(C.aideCode);
    expect(screen.getAllByRole("button").filter((b) => b.getAttribute("type") === "submit")).toHaveLength(1);
    expect(screen.getByText(TEXTES.code.sansTelephone)).toBeInTheDocument();
  });

  it("« Utiliser un code de secours » : même bascule qu'à l'écran du code", async () => {
    render(<FormulaireReinitialisation />);
    await userEvent.click(screen.getByRole("button", { name: TEXTES.code.utiliserSecours }));
    const secours = screen.getByLabelText(TEXTES.code.libelleSecours);
    expect(secours).toHaveFocus();
    expect(secours).toHaveAccessibleDescription(TEXTES.code.aideSecours);
    await userEvent.click(screen.getByRole("button", { name: TEXTES.code.utiliserApplication }));
    expect(code()).toHaveFocus();
  });

  it("sans le lien de l'e-mail : invitation à l'ouvrir, lien « Mot de passe oublié », aucun champ", () => {
    window.history.replaceState(null, "", "/reinitialisation");
    render(<FormulaireReinitialisation />);
    expect(screen.getByText(C.sansLien)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: TEXTES.connexion.oublie })).toHaveAttribute("href", "/mot-de-passe-oublie");
    expect(screen.queryByRole("textbox")).toBeNull();
  });
});

describe("Choisir un nouveau mot de passe : vérifications du front", () => {
  it("confirmation différente : message sous le second champ, focus dessus, rien d'envoyé", async () => {
    const appel = vi.fn();
    vi.stubGlobal("fetch", appel);
    render(<FormulaireReinitialisation />);
    await remplir(MOT_DE_PASSE, "le chat dort sur le toi");
    await changer();
    expect(confirmation()).toHaveAccessibleDescription(M.differents);
    expect(confirmation()).toHaveFocus();
    expect(appel).not.toHaveBeenCalled();
  });

  it("mot de passe trop court : message sous le premier champ, focus dessus, rien d'envoyé", async () => {
    const appel = vi.fn();
    vi.stubGlobal("fetch", appel);
    render(<FormulaireReinitialisation />);
    await remplir("le chat", "le chat");
    await changer();
    expect(motDePasse()).toHaveAccessibleDescription(`${TEXTES.activation.aideMotDePasse} ${messageMotDePasse("trop_court")}`);
    expect(motDePasse()).toHaveFocus();
    expect(appel).not.toHaveBeenCalled();
  });
});

describe("Choisir un nouveau mot de passe : envoi", () => {
  it("réussite : POST reinitialisation/fin (jeton, un seul mot de passe, code) ; jeton retiré ; Se connecter avec le bandeau", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(204));
    vi.stubGlobal("fetch", appel);
    render(<FormulaireReinitialisation />);
    expect(window.location.hash).toBe(`#${JETON}`);
    await remplir();
    await changer();
    await waitFor(() => expect(remplacer).toHaveBeenCalledWith("/connexion?motif=mot_de_passe_change"));
    expect(appel.mock.calls[0]![0]).toBe("/api/identity/auth/reinitialisation/fin");
    expect(JSON.parse((appel.mock.calls[0] as [string, RequestInit])[1].body as string)).toEqual({
      jeton: JETON,
      mot_de_passe: MOT_DE_PASSE,
      code: "123456",
    });
    expect(window.location.hash).toBe("");
  });

  it("mot de passe refusé (422) : les deux champs et le code vidés, message du motif sous le premier champ, focus", async () => {
    const message = messageMotDePasse("courant");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(refus(422, "mot_de_passe_refuse", message, "mot_de_passe")));
    render(<FormulaireReinitialisation />);
    await remplir();
    await changer();
    await waitFor(() => expect(motDePasse()).toHaveAccessibleDescription(`${TEXTES.activation.aideMotDePasse} ${message}`));
    expect(motDePasse()).toHaveValue("");
    expect(confirmation()).toHaveValue("");
    expect(code()).toHaveValue("");
    expect(motDePasse()).toHaveFocus();
  });

  it("code faux (400) : message sous le code, code vidé, mot de passe gardé, focus sur le code", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(refus(400, "code_incorrect", libelle("code.incorrect"), "code")));
    render(<FormulaireReinitialisation />);
    await remplir();
    await changer();
    await waitFor(() => expect(code()).toHaveAccessibleDescription(`${C.aideCode} ${libelle("code.incorrect")}`));
    expect(code()).toHaveValue("");
    expect(code()).toHaveFocus();
    expect(motDePasse()).toHaveValue(MOT_DE_PASSE);
    expect(window.location.hash).toBe(`#${JETON}`);
  });

  it.each([
    [400, "trop_de_codes", "reinitialisation.trop_de_codes"],
    [410, "lien_invalide", "reinitialisation.lien_invalide"],
  ] as const)("%i %s : la page ne montre que le message, avec le lien « Mot de passe oublié »", async (statut, codeRefus, cle) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(refus(statut, codeRefus, libelle(cle), statut === 400 ? "code" : undefined)));
    render(<FormulaireReinitialisation />);
    await remplir();
    await changer();
    expect(await screen.findByText(libelle(cle))).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.getByRole("link", { name: TEXTES.connexion.oublie })).toHaveAttribute("href", "/mot-de-passe-oublie");
  });

  it("trop d'essais (429) : bandeau « Attention »", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(refus(429, "trop_d_essais", libelle("connexion.trop_d_essais"))),
    );
    render(<FormulaireReinitialisation />);
    await remplir();
    await changer();
    const bandeau = await screen.findByRole("alert");
    expect(bandeau).toHaveTextContent(TEXTES.etats.attention);
    expect(bandeau).toHaveTextContent(libelle("connexion.trop_d_essais"));
  });
});
