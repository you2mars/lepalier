import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BandeauFlash, MessageFlashProvider } from "@/components/cadre/MessageFlash";
import { libelle } from "@/lib/libelles";
import type { Personne } from "@/lib/session";
import { TEXTES } from "@/textes";
import type { Fiche } from "../GestionAcces";
import { FormulaireRole } from "./FormulaireRole";
import Page, { generateMetadata } from "./page";

const R = TEXTES.utilisateurs.role;
const D = TEXTES.descriptionsRoles;
const FICHE_CHEMIN = "/administration/utilisateurs/0192-b";
const pousser = vi.fn();
const quitterVers = vi.fn();
const reprendreSession = vi.fn();
const lireConnecte = vi.fn();
const GERANT: Personne = { id: "g", email: "gerant@exemple.fr", nom_affiche: "M. Martin", role: "gerant" };
let personne: Personne | null = GERANT;
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pousser }),
  usePathname: () => FICHE_CHEMIN,
  notFound: () => {
    throw new Error("introuvable");
  },
}));
vi.mock("@/lib/navigation", () => ({
  quitterVers: (adresse: string) => quitterVers(adresse),
  reprendreSession: () => reprendreSession(),
}));
vi.mock("@/lib/session", () => ({
  personneConnectee: async () => personne,
  lireConnecte: (chemin: string) => lireConnecte(chemin),
}));

const DURAND: Fiche = {
  id: "0192-b",
  email: "marie.durand@exemple.fr",
  nom_affiche: "Mme Durand",
  role: "associe",
  statut: "actif",
  statut_libelle: "Accès actif",
  invitation_envoyee_le: null,
  invitation_expire_le: null,
};
const MOI_GERANT: Fiche = { ...DURAND, id: "g", nom_affiche: "M. Martin", role: "gerant" };

function reponse(statut: number, corps: unknown): Response {
  return new Response(JSON.stringify(corps), { status: statut, headers: { "Content-Type": "application/json" } });
}

const option = (role: "associe" | "operateur" | "gerant", actuel = false) =>
  screen.getByRole("radio", {
    name: `${TEXTES.roles[role]} — ${D[role]}.${actuel ? ` ${R.roleActuel}` : ""}`,
  });

function afficher(fiche: Fiche, estMoi = false) {
  return render(
    <MessageFlashProvider>
      <BandeauFlash />
      <FormulaireRole fiche={fiche} estMoi={estMoi} />
    </MessageFlashProvider>,
  );
}

const enregistrer = () => userEvent.click(screen.getByRole("button", { name: R.enregistrer }));

beforeEach(() => {
  personne = GERANT;
  pousser.mockReset();
  quitterVers.mockReset();
  reprendreSession.mockReset();
  lireConnecte.mockReset();
  lireConnecte.mockResolvedValue({ ok: true, statut: 200, donnees: DURAND });
});
afterEach(() => vi.unstubAllGlobals());

describe("Changer le rôle : page (maquettes v3, écran 6.4 ; M7)", () => {
  it("titre, onglet, fil d'Ariane jusqu'à la fiche ; fiche lue chez identity", async () => {
    const parametres = { params: Promise.resolve({ id: "0192-b" }) };
    render(await Page(parametres));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Changer le rôle de Mme Durand");
    expect((await generateMetadata(parametres)).title).toBe("Changer le rôle de Mme Durand — LePalier");
    const fil = screen.getByRole("navigation", { name: TEXTES.cadre.filAriane });
    expect(within(fil).getAllByRole("listitem").map((e) => e.textContent)).toEqual([
      TEXTES.cadre.administration,
      TEXTES.utilisateurs.liste.titre,
      "Mme Durand",
      R.filAriane,
    ]);
    expect(within(fil).getByRole("link", { name: "Mme Durand" })).toHaveAttribute("href", FICHE_CHEMIN);
    expect(lireConnecte).toHaveBeenCalledWith("/identity/utilisateurs/0192-b");
  });

  it("personne inconnue : page introuvable ; associé : page réservée ; panne : information indisponible", async () => {
    lireConnecte.mockResolvedValue({ ok: false, statut: 404 });
    await expect(Page({ params: Promise.resolve({ id: "x" }) })).rejects.toThrow("introuvable");
    lireConnecte.mockResolvedValue({ ok: false, statut: 502 });
    render(await Page({ params: Promise.resolve({ id: "0192-b" }) }));
    expect(screen.getByText(TEXTES.indisponible)).toBeInTheDocument();
    personne = { ...GERANT, role: "associe" };
    render(await Page({ params: Promise.resolve({ id: "0192-b" }) }));
    expect(screen.getByRole("heading", { level: 1, name: TEXTES.reservee.titre })).toBeInTheDocument();
  });
});

describe("Changer le rôle : formulaire", () => {
  it("trois rôles avec leur description unique, le rôle actuel coché et signalé « (rôle actuel) »", () => {
    afficher(DURAND);
    expect(within(screen.getByRole("group", { name: TEXTES.utilisateurs.inviter.role })).getAllByRole("radio")).toHaveLength(3);
    expect(option("associe", true)).toBeChecked();
    expect(option("operateur")).not.toBeChecked();
    expect(option("gerant")).not.toBeChecked();
  });

  it("« Enregistrer » seul bouton principal ; « Annuler » ramène à la fiche", () => {
    afficher(DURAND);
    expect(screen.getAllByRole("button").filter((b) => b.getAttribute("type") === "submit")).toHaveLength(1);
    expect(screen.getByRole("link", { name: R.annuler })).toHaveAttribute("href", FICHE_CHEMIN);
  });

  it("rôle inchangé (A7) : rien d'envoyé, retour à la fiche qui le dit", async () => {
    const appel = vi.fn();
    vi.stubGlobal("fetch", appel);
    afficher(DURAND);
    await enregistrer();
    expect(appel).not.toHaveBeenCalled();
    expect(pousser).toHaveBeenCalledWith(FICHE_CHEMIN);
    expect(screen.getByRole("status")).toHaveTextContent("Aucun changement : Mme Durand a déjà le rôle Associé.");
  });

  it("autre changement : sans confirmation, PATCH du rôle avec clé d'idempotence ; la fiche dit l'ancien et le nouveau rôle", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(200, { ...DURAND, role: "operateur" }));
    vi.stubGlobal("fetch", appel);
    afficher(DURAND);
    await userEvent.click(option("operateur"));
    await enregistrer();
    expect(screen.queryByRole("dialog")).toBeNull();
    await waitFor(() => expect(pousser).toHaveBeenCalledWith(FICHE_CHEMIN));
    const [chemin, options] = appel.mock.calls[0] as [string, RequestInit];
    expect(chemin).toBe("/api/identity/utilisateurs/0192-b");
    expect(options.method).toBe("PATCH");
    expect(JSON.parse(options.body as string)).toEqual({ role: "operateur" });
    expect((options.headers as Record<string, string>)["Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(screen.getByRole("status")).toHaveTextContent("Rôle de Mme Durand changé : Opérateur (auparavant Associé).");
  });

  it("donner le rôle de gérant : confirmation, focus sur « Annuler » ; « Annuler » ne fait rien", async () => {
    const appel = vi.fn();
    vi.stubGlobal("fetch", appel);
    afficher(DURAND);
    await userEvent.click(option("gerant"));
    await enregistrer();
    const boite = screen.getByRole("dialog", { name: "Donner le rôle de gérant à Mme Durand ?" });
    expect(boite).toHaveTextContent(R.donnerGerant.explication);
    await userEvent.click(within(boite).getByRole("button", { name: R.annuler }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(appel).not.toHaveBeenCalled();
  });

  it("donner le rôle de gérant confirmé : PATCH, puis la fiche", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(200, { ...DURAND, role: "gerant" })));
    afficher(DURAND);
    await userEvent.click(option("gerant"));
    await enregistrer();
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: R.donnerGerant.bouton }));
    await waitFor(() => expect(pousser).toHaveBeenCalledWith(FICHE_CHEMIN));
    expect(screen.getByRole("status")).toHaveTextContent("Rôle de Mme Durand changé : Gérant (auparavant Associé).");
  });

  it("quitter soi-même le rôle de gérant : confirmation obligatoire ; puis l'accueil, rechargé pour le menu et le rôle", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(200, { ...MOI_GERANT, role: "associe" }));
    vi.stubGlobal("fetch", appel);
    afficher(MOI_GERANT, true);
    await userEvent.click(option("associe"));
    await enregistrer();
    const boite = screen.getByRole("dialog", { name: R.quitterGerant.question });
    expect(boite).toHaveTextContent(R.quitterGerant.explication);
    await userEvent.click(within(boite).getByRole("button", { name: R.quitterGerant.bouton }));
    await waitFor(() => expect(quitterVers).toHaveBeenCalledWith("/?motif=role_quitte"));
    expect(JSON.parse((appel.mock.calls[0] as [string, RequestInit])[1].body as string)).toEqual({ role: "associe" });
  });

  it("dernier gérant (409) : bandeau « Attention » avec le message d'identity, on reste sur l'écran", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        reponse(409, { code: "dernier_gerant", message: libelle("utilisateurs.dernier_gerant"), details: {} }),
      ),
    );
    afficher(MOI_GERANT, true);
    await userEvent.click(option("operateur"));
    await enregistrer();
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: R.quitterGerant.bouton }));
    const bandeau = await screen.findByRole("alert");
    expect(bandeau).toHaveTextContent(TEXTES.etats.attention);
    expect(bandeau).toHaveTextContent(libelle("utilisateurs.dernier_gerant"));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(quitterVers).not.toHaveBeenCalled();
  });

  it("401 : reprise de session ; panne : bandeau « Erreur »", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(401, { code: "unauthenticated", message: "x" })));
    const { unmount } = afficher(DURAND);
    await userEvent.click(option("operateur"));
    await enregistrer();
    await waitFor(() => expect(reprendreSession).toHaveBeenCalledOnce());
    unmount();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    afficher(DURAND);
    await userEvent.click(option("operateur"));
    await enregistrer();
    expect(await screen.findByRole("alert")).toHaveTextContent(TEXTES.commun.erreurInattendue);
  });
});
