import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { libelle } from "@/lib/libelles";
import { TEXTES } from "@/textes";
import { FormulaireCode } from "./FormulaireCode";
import Page, { metadata } from "./page";

const remplacer = vi.fn();
const cookies = new Set<string>();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: remplacer }),
  redirect: (adresse: string) => {
    throw new Error(`redirection ${adresse}`);
  },
}));
vi.mock("next/headers", () => ({ cookies: async () => ({ has: (nom: string) => cookies.has(nom) }) }));

function reponse(statut: number, corps: unknown): Response {
  return new Response(JSON.stringify(corps), { status: statut, headers: { "Content-Type": "application/json" } });
}

function refus(statut: number, code: string, message: string): Response {
  return reponse(statut, { code, message, details: {}, trace_id: "t" });
}

const champCode = () => screen.getByLabelText(TEXTES.code.libelle);

async function saisirEtEnvoyer(code = "123 456") {
  await userEvent.type(champCode(), code);
  await userEvent.click(screen.getByRole("button", { name: TEXTES.connexion.bouton }));
}

beforeEach(() => {
  remplacer.mockReset();
  cookies.clear();
});
afterEach(() => vi.unstubAllGlobals());

describe("Code de vérification : accès (pré-session lp_pre)", () => {
  it("sans pré-session : retour à Se connecter, sans message, page demandée gardée", async () => {
    await expect(Page({ searchParams: Promise.resolve({ retour: "/administration/utilisateurs" }) })).rejects.toThrow(
      "redirection /connexion?retour=%2Fadministration%2Futilisateurs",
    );
    await expect(Page({ searchParams: Promise.resolve({}) })).rejects.toThrow(/^redirection \/connexion$/);
  });

  it("avec une pré-session : l'écran s'affiche", async () => {
    cookies.add("lp_pre");
    render(await Page({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(TEXTES.code.titre);
  });

  it("titre de l'onglet « Code de vérification — LePalier »", () => {
    expect(metadata.title).toBe("Code de vérification — LePalier");
  });
});

describe("Code de vérification : structure (R0-02, UX-1, maquettes v3 écran 2)", () => {
  it("titre, consigne, un seul bouton principal « Se connecter », liens et texte d'aide", () => {
    render(<FormulaireCode />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(TEXTES.code.titre);
    expect(screen.getByText(TEXTES.code.consigne)).toBeInTheDocument();
    expect(screen.getAllByRole("button").filter((b) => b.getAttribute("type") === "submit")).toHaveLength(1);
    expect(screen.getByRole("button", { name: TEXTES.connexion.bouton })).toHaveAttribute("type", "submit");
    expect(screen.getByRole("link", { name: TEXTES.code.recommencer })).toHaveAttribute("href", "/connexion");
    expect(screen.getByText(TEXTES.code.sansTelephone)).toBeInTheDocument();
  });

  it("champ du code : un seul champ, clavier numérique, remplissage du code reçu, aide liée", () => {
    render(<FormulaireCode />);
    const code = champCode();
    expect(code).toHaveAttribute("inputmode", "numeric");
    expect(code).toHaveAttribute("autocomplete", "one-time-code");
    expect(code).toHaveAttribute("autocorrect", "off");
    expect(code).toHaveAttribute("spellcheck", "false");
    expect(code).toHaveAccessibleDescription(TEXTES.code.aide);
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
  });

  it("formulaire en POST, sans validation du navigateur", () => {
    const { container } = render(<FormulaireCode />);
    expect(container.querySelector("form")).toHaveAttribute("method", "post");
    expect(container.querySelector("form")).toHaveAttribute("novalidate");
  });

  it("« Recommencer la connexion » garde la page demandée", () => {
    render(<FormulaireCode retour="/administration/utilisateurs" />);
    expect(screen.getByRole("link", { name: TEXTES.code.recommencer })).toHaveAttribute(
      "href",
      "/connexion?retour=%2Fadministration%2Futilisateurs",
    );
  });

  it("le lien vers le code de secours suit le champ et son erreur (M4)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(refus(401, "code_incorrect", libelle("code.incorrect"))));
    render(<FormulaireCode />);
    await saisirEtEnvoyer("000000");
    const erreur = await screen.findByText(libelle("code.incorrect"));
    const lien = screen.getByRole("button", { name: TEXTES.code.utiliserSecours });
    expect(erreur.compareDocumentPosition(lien) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(lien.compareDocumentPosition(screen.getByRole("button", { name: TEXTES.connexion.bouton })) &
      Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});

describe("Code de vérification : mode code de secours", () => {
  it("mode code de secours : la consigne parle des codes de secours, plus de l'application (revue UX, M1)", async () => {
    render(<FormulaireCode />);
    await userEvent.click(screen.getByRole("button", { name: TEXTES.code.utiliserSecours }));
    expect(screen.getByText(TEXTES.code.consigneSecours)).toBeInTheDocument();
    expect(screen.queryByText(TEXTES.code.consigne)).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: TEXTES.code.utiliserApplication }));
    expect(screen.getByText(TEXTES.code.consigne)).toBeInTheDocument();
  });

  it("« Utiliser un code de secours » : champ adapté, aide, champ vidé et focus dessus", async () => {
    render(<FormulaireCode />);
    await userEvent.type(champCode(), "12");
    await userEvent.click(screen.getByRole("button", { name: TEXTES.code.utiliserSecours }));
    const secours = screen.getByLabelText(TEXTES.code.libelleSecours);
    expect(secours).toHaveValue("");
    expect(secours).toHaveFocus();
    expect(secours).toHaveAttribute("inputmode", "text");
    expect(secours).toHaveAttribute("autocapitalize", "characters");
    expect(secours).toHaveAttribute("autocomplete", "off");
    expect(secours).toHaveAccessibleDescription(TEXTES.code.aideSecours);
    expect(screen.queryByLabelText(TEXTES.code.libelle)).toBeNull();
  });

  it("« Utiliser le code de l'application » : retour au mode normal, erreur effacée", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(refus(401, "code_incorrect", libelle("code.incorrect"))));
    render(<FormulaireCode />);
    await userEvent.click(screen.getByRole("button", { name: TEXTES.code.utiliserSecours }));
    await userEvent.type(screen.getByLabelText(TEXTES.code.libelleSecours), "ABCD-EFGH-JKMN");
    await userEvent.click(screen.getByRole("button", { name: TEXTES.connexion.bouton }));
    await screen.findByText(libelle("code.incorrect"));
    await userEvent.click(screen.getByRole("button", { name: TEXTES.code.utiliserApplication }));
    expect(champCode()).toHaveFocus();
    expect(champCode()).toHaveAccessibleDescription(TEXTES.code.aide);
    expect(screen.queryByText(libelle("code.incorrect"))).toBeNull();
  });

  it("le code de secours part tel que saisi : identity tolère minuscules, espaces et tirets", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(200, { nom_affiche: "Mme Durand", role: "associe" }));
    vi.stubGlobal("fetch", appel);
    render(<FormulaireCode />);
    await userEvent.click(screen.getByRole("button", { name: TEXTES.code.utiliserSecours }));
    await userEvent.type(screen.getByLabelText(TEXTES.code.libelleSecours), "abcd efgh-jkmn");
    await userEvent.click(screen.getByRole("button", { name: TEXTES.connexion.bouton }));
    await waitFor(() => expect(remplacer).toHaveBeenCalledWith("/"));
    expect(JSON.parse(appel.mock.calls[0]![1].body)).toEqual({ code: "abcd efgh-jkmn" });
  });
});

describe("Code de vérification : envoi", () => {
  it("code juste : POST /api/identity/auth/code puis accueil, sans retour possible vers cet écran", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(200, { nom_affiche: "M. Martin", role: "gerant" }));
    vi.stubGlobal("fetch", appel);
    render(<FormulaireCode />);
    await saisirEtEnvoyer();
    await waitFor(() => expect(remplacer).toHaveBeenCalledWith("/"));
    expect(appel.mock.calls[0]![0]).toBe("/api/identity/auth/code");
    expect(JSON.parse(appel.mock.calls[0]![1].body)).toEqual({ code: "123 456" });
  });

  it("code juste avec une page demandée : retour à cette page (§ 0.3)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(200, { nom_affiche: "M. Martin", role: "gerant" })));
    render(<FormulaireCode retour="/administration/utilisateurs?page=2" />);
    await saisirEtEnvoyer();
    await waitFor(() => expect(remplacer).toHaveBeenCalledWith("/administration/utilisateurs?page=2"));
  });

  it.each([["//pirate.example"], ["https://pirate.example/"], ["/connexion"], ["%2F%2Fpirate.example"]])(
    "page demandée %s : ignorée, accueil",
    async (retour) => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(200, { nom_affiche: "M. Martin", role: "gerant" })));
      render(<FormulaireCode retour={retour} />);
      await saisirEtEnvoyer();
      await waitFor(() => expect(remplacer).toHaveBeenCalledWith("/"));
    },
  );

  it("code faux : message sous le champ, champ vidé, focus dessus, on reste sur l'écran", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(refus(401, "code_incorrect", libelle("code.incorrect"))));
    render(<FormulaireCode />);
    await saisirEtEnvoyer("000000");
    await waitFor(() => expect(champCode()).toHaveAccessibleDescription(`${TEXTES.code.aide} ${libelle("code.incorrect")}`));
    expect(champCode()).toHaveValue("");
    expect(champCode()).toHaveFocus();
    expect(champCode()).toHaveAttribute("aria-invalid", "true");
    expect(remplacer).not.toHaveBeenCalled();
  });

  it.each([
    [401, "delai_depasse", "code.delai_depasse"],
    [401, "trop_de_codes", "code.trop_de_codes"],
    [403, "compte_suspendu", "connexion.compte_suspendu"],
  ] as const)("%i %s : retour à Se connecter avec le bandeau, page demandée gardée", async (statut, code, cle) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(refus(statut, code, libelle(cle))));
    render(<FormulaireCode retour="/administration/utilisateurs" />);
    await saisirEtEnvoyer();
    await waitFor(() =>
      expect(remplacer).toHaveBeenCalledWith(`/connexion?motif=${code}&retour=%2Fadministration%2Futilisateurs`),
    );
  });

  it("trop d'essais (429) : bandeau « Attention » avec le message reçu, on reste sur l'écran", async () => {
    const message = libelle("connexion.trop_d_essais");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(refus(429, "trop_d_essais", message)));
    render(<FormulaireCode />);
    await saisirEtEnvoyer();
    const bandeau = await screen.findByRole("alert");
    expect(bandeau).toHaveTextContent(TEXTES.etats.attention);
    expect(bandeau).toHaveTextContent(message);
    expect(remplacer).not.toHaveBeenCalled();
  });

  it("panne réseau : bandeau « Erreur » avec le message de commun", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<FormulaireCode />);
    await saisirEtEnvoyer();
    const bandeau = await screen.findByRole("alert");
    expect(bandeau).toHaveTextContent(TEXTES.etats.erreur);
    expect(bandeau).toHaveTextContent(TEXTES.commun.erreurInattendue);
  });

  it("pendant l'envoi : bouton désactivé, « Envoi en cours… » (UX-22)", async () => {
    let terminer: (r: Response) => void = () => undefined;
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise<Response>((r) => (terminer = r))));
    render(<FormulaireCode />);
    await saisirEtEnvoyer();
    expect(screen.getByRole("button", { name: TEXTES.envoiEnCours })).toBeDisabled();
    terminer(reponse(200, { nom_affiche: "M. Martin", role: "gerant" }));
    await waitFor(() => expect(remplacer).toHaveBeenCalled());
  });
});
