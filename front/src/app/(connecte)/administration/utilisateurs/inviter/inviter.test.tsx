import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { libelle } from "@/lib/libelles";
import type { Personne } from "@/lib/session";
import { TEXTES } from "@/textes";
import { FormulaireInvitation } from "./FormulaireInvitation";
import Page, { metadata } from "./page";

const I = TEXTES.utilisateurs.inviter;
const D = TEXTES.descriptionsRoles;
const pousser = vi.fn();
const reprendreSession = vi.fn();
let personne: Personne | null = { id: "g", email: "g@exemple.fr", nom_affiche: "M. Martin", role: "gerant" };
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pousser }) }));
vi.mock("@/lib/navigation", () => ({ reprendreSession: () => reprendreSession() }));
vi.mock("@/lib/session", () => ({ personneConnectee: async () => personne }));

function reponse(statut: number, corps: unknown): Response {
  return new Response(JSON.stringify(corps), { status: statut, headers: { "Content-Type": "application/json" } });
}

function refus(statut: number, code: string, message: string, champ?: string): Response {
  return reponse(statut, { code, message, details: champ ? { champs: [{ champ, message }] } : {}, trace_id: "t" });
}

const nom = () => screen.getByLabelText(I.nomAffiche);
const adresse = () => screen.getByLabelText(I.adresse);
const radio = (role: "associe" | "operateur" | "gerant") =>
  screen.getByRole("radio", { name: `${TEXTES.roles[role]} — ${D[role]}.` });

async function remplir(n = "Mme Durand", a = "marie.durand@exemple.fr") {
  await userEvent.type(nom(), n);
  await userEvent.type(adresse(), a);
}

async function envoyer() {
  await userEvent.click(screen.getByRole("button", { name: I.envoyer }));
}

async function confirmer() {
  const boite = screen.getByRole("dialog");
  await userEvent.click(within(boite).getByRole("button", { name: I.envoyer }));
}

beforeEach(() => {
  pousser.mockReset();
  reprendreSession.mockReset();
  personne = { id: "g", email: "g@exemple.fr", nom_affiche: "M. Martin", role: "gerant" };
});
afterEach(() => vi.unstubAllGlobals());

describe("Inviter une personne : page (maquettes v3, écran 6.2 ; R0-04)", () => {
  it("gérant : titre, onglet, fil d'Ariane avec lien vers la liste", async () => {
    render(await Page());
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(I.titre);
    expect(metadata.title).toBe("Inviter une personne — LePalier");
    const fil = screen.getByRole("navigation", { name: TEXTES.cadre.filAriane });
    expect(within(fil).getAllByRole("listitem").map((e) => e.textContent)).toEqual([
      TEXTES.cadre.administration,
      TEXTES.utilisateurs.liste.titre,
      I.filAriane,
    ]);
    expect(within(fil).getByRole("link", { name: TEXTES.utilisateurs.liste.titre })).toHaveAttribute(
      "href",
      "/administration/utilisateurs",
    );
  });

  it("associé : page réservée au gérant", async () => {
    personne = { id: "a", email: "a@exemple.fr", nom_affiche: "Mme A", role: "associe" };
    render(await Page());
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(TEXTES.reservee.titre);
  });
});

describe("Inviter une personne : formulaire", () => {
  it("nom affiché d'abord, puis adresse, puis rôle ; aides liées ; attributs de l'adresse", () => {
    render(<FormulaireInvitation />);
    expect(nom().compareDocumentPosition(adresse()) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(nom()).toHaveAccessibleDescription(I.aideNom);
    expect(adresse()).toHaveAccessibleDescription(I.aideAdresse);
    expect(adresse()).toHaveAttribute("type", "email");
    expect(adresse()).toHaveAttribute("autocomplete", "off");
    expect(adresse()).toHaveAttribute("inputmode", "email");
    expect(adresse()).toHaveAttribute("autocapitalize", "none");
    expect(adresse()).toHaveAttribute("spellcheck", "false");
  });

  it("rôle : trois choix avec leur description unique (Q5), « Associé » coché par défaut (UX-18)", () => {
    render(<FormulaireInvitation />);
    const groupe = screen.getByRole("group", { name: I.role });
    expect(within(groupe).getAllByRole("radio")).toHaveLength(3);
    expect(radio("associe")).toBeChecked();
    expect(radio("operateur")).not.toBeChecked();
    expect(radio("gerant")).not.toBeChecked();
  });

  it("un seul bouton principal « Envoyer l'invitation » ; « Annuler » ramène à la liste", () => {
    render(<FormulaireInvitation />);
    expect(screen.getAllByRole("button").filter((b) => b.getAttribute("type") === "submit")).toHaveLength(1);
    const annuler = screen.getByRole("link", { name: I.annuler });
    expect(annuler).toHaveAttribute("href", "/administration/utilisateurs");
    expect(annuler).toHaveClass("bouton-secondaire");
  });

  it.each([
    ["nom avec « @ »", () => nom(), "marie@exemple.fr", libelle("nom_affiche.invalide"), I.aideNom],
    ["adresse incorrecte", () => adresse(), "marie", libelle("utilisateurs.email_invalide"), I.aideAdresse],
  ])("%s : message sous le champ à la sortie (UX-19)", async (_, champ, valeur, message, aide) => {
    render(<FormulaireInvitation />);
    await userEvent.type(champ(), valeur);
    await userEvent.tab();
    expect(champ()).toHaveAccessibleDescription(`${aide} ${message}`);
  });

  it("envoi avec des champs vides : aucune confirmation, messages, focus sur le premier champ", async () => {
    const appel = vi.fn();
    vi.stubGlobal("fetch", appel);
    render(<FormulaireInvitation />);
    await envoyer();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(nom()).toHaveFocus();
    expect(nom()).toHaveAttribute("aria-invalid", "true");
    expect(adresse()).toHaveAttribute("aria-invalid", "true");
    expect(appel).not.toHaveBeenCalled();
  });
});

describe("Inviter une personne : confirmation récapitulative (UX-3, B2)", () => {
  it("question, adresse, rôle avec sa description, validité sans date ; focus sur « Modifier » ; rien d'envoyé", async () => {
    const appel = vi.fn();
    vi.stubGlobal("fetch", appel);
    render(<FormulaireInvitation />);
    await remplir();
    await envoyer();
    const boite = screen.getByRole("dialog", { name: "Envoyer l'invitation à Mme Durand ?" });
    expect(within(boite).getByText("marie.durand@exemple.fr").closest("p")).toHaveTextContent(
      "Adresse : marie.durand@exemple.fr",
    );
    expect(within(boite).getByText(`Rôle : Associé — ${D.associe}.`)).toBeInTheDocument();
    expect(within(boite).getByText(I.confirmation.validite)).toBeInTheDocument();
    expect(within(boite).getByRole("button", { name: I.confirmation.modifier })).toHaveFocus();
    expect(appel).not.toHaveBeenCalled();
  });

  it("rôle choisi : sa description dans la confirmation", async () => {
    render(<FormulaireInvitation />);
    await remplir();
    await userEvent.click(radio("operateur"));
    await envoyer();
    expect(within(screen.getByRole("dialog")).getByText(`Rôle : Opérateur — ${D.operateur}.`)).toBeInTheDocument();
  });

  it("« Modifier » : retour au formulaire, saisie gardée, rien d'envoyé", async () => {
    const appel = vi.fn();
    vi.stubGlobal("fetch", appel);
    render(<FormulaireInvitation />);
    await remplir();
    await envoyer();
    await userEvent.click(screen.getByRole("button", { name: I.confirmation.modifier }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(nom()).toHaveValue("Mme Durand");
    expect(adresse()).toHaveValue("marie.durand@exemple.fr");
    expect(appel).not.toHaveBeenCalled();
  });
});

describe("Inviter une personne : envoi", () => {
  it("POST /api/identity/utilisateurs/inviter avec une clé d'idempotence ; puis la liste, qui dit ce qui a été fait", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(201, { id: "0192-b", email: "marie.durand@exemple.fr" }));
    vi.stubGlobal("fetch", appel);
    render(<FormulaireInvitation />);
    await remplir();
    await userEvent.click(radio("gerant"));
    await envoyer();
    await confirmer();
    await waitFor(() => expect(pousser).toHaveBeenCalledWith("/administration/utilisateurs?invitee=0192-b"));
    const [chemin, options] = appel.mock.calls[0] as [string, RequestInit];
    expect(chemin).toBe("/api/identity/utilisateurs/inviter");
    expect(JSON.parse(options.body as string)).toEqual({
      nom_affiche: "Mme Durand",
      email: "marie.durand@exemple.fr",
      role: "gerant",
    });
    expect((options.headers as Record<string, string>)["Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("nouvel essai après une panne, dans la même confirmation : même clé d'idempotence (pas de double invitation)", async () => {
    const appel = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValue(reponse(201, { id: "0192-b" }));
    vi.stubGlobal("fetch", appel);
    render(<FormulaireInvitation />);
    await remplir();
    await envoyer();
    await confirmer();
    await screen.findByRole("alert");
    await envoyer();
    await confirmer();
    await waitFor(() => expect(pousser).toHaveBeenCalled());
    const cles = appel.mock.calls.map((c) => ((c as [string, RequestInit])[1].headers as Record<string, string>)["Idempotency-Key"]);
    expect(cles[0]).toBe(cles[1]);
  });

  it.each([
    [409, "email_deja_utilise", "utilisateurs.email_deja_utilise", "email", () => adresse(), I.aideAdresse],
    [422, "invalid", "nom_affiche.invalide", "nom_affiche", () => nom(), I.aideNom],
  ] as const)("%i %s : confirmation fermée, message sous le champ, focus dessus", async (statut, code, cle, champ, element, aide) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(refus(statut, code, libelle(cle), champ)));
    render(<FormulaireInvitation />);
    await remplir();
    await envoyer();
    await confirmer();
    await waitFor(() => expect(element()).toHaveAccessibleDescription(`${aide} ${libelle(cle)}`));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(element()).toHaveFocus();
    expect(pousser).not.toHaveBeenCalled();
  });

  it("message du serveur gardé à la sortie du champ tant que la valeur ne change pas ; renvoi sans changement : pas de nouvelle confirmation", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(refus(409, "email_deja_utilise", libelle("utilisateurs.email_deja_utilise"), "email")),
    );
    render(<FormulaireInvitation />);
    await remplir();
    await envoyer();
    await confirmer();
    const message = `${I.aideAdresse} ${libelle("utilisateurs.email_deja_utilise")}`;
    await waitFor(() => expect(adresse()).toHaveFocus());
    await userEvent.tab();
    expect(adresse()).toHaveAccessibleDescription(message);
    await envoyer();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(adresse()).toHaveFocus();
    await userEvent.type(adresse(), "x");
    expect(adresse()).toHaveAccessibleDescription(I.aideAdresse);
  });

  it("session expirée ou accès suspendu (401) : reprise de session (Se connecter avec le bon bandeau)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(401, { code: "unauthenticated", message: "x" })));
    render(<FormulaireInvitation />);
    await remplir();
    await envoyer();
    await confirmer();
    await waitFor(() => expect(reprendreSession).toHaveBeenCalledOnce());
  });

  it("panne : confirmation fermée, bandeau « Erreur » avec le message de commun", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<FormulaireInvitation />);
    await remplir();
    await envoyer();
    await confirmer();
    const bandeau = await screen.findByRole("alert");
    expect(bandeau).toHaveTextContent(TEXTES.etats.erreur);
    expect(bandeau).toHaveTextContent(TEXTES.commun.erreurInattendue);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("pendant l'envoi : bouton de la confirmation désactivé, « Envoi en cours… » (UX-22)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => undefined)));
    render(<FormulaireInvitation />);
    await remplir();
    await envoyer();
    await confirmer();
    expect(within(screen.getByRole("dialog")).getByRole("button", { name: TEXTES.envoiEnCours })).toBeDisabled();
  });
});
