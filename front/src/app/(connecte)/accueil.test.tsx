import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CadreConnecte } from "@/components/cadre/CadreConnecte";
import { SeDeconnecter } from "@/components/cadre/SeDeconnecter";
import type { Personne } from "@/lib/session";
import { TEXTES } from "@/textes";
import Accueil, { metadata } from "./page";
import MiseEnPageConnectee from "./layout";

const quitterVers = vi.fn();
let chemin = "/";
let personne: Personne | null = null;
vi.mock("@/lib/navigation", () => ({ quitterVers: (adresse: string) => quitterVers(adresse) }));
vi.mock("next/navigation", () => ({ usePathname: () => chemin }));
vi.mock("@/lib/session", () => ({ personneConnectee: async () => personne }));

const GERANT: Personne = { id: "1", email: "gerant@exemple.fr", nom_affiche: "M. Martin", role: "gerant" };
const ASSOCIE: Personne = { id: "2", email: "associe@exemple.fr", nom_affiche: "Mme Durand", role: "associe" };
const OPERATEUR: Personne = { id: "3", email: "operateur@exemple.fr", nom_affiche: "M. Petit", role: "operateur" };
const A = TEXTES.accueil;
const C = TEXTES.cadre;

function reponse(statut: number): Response {
  return new Response(null, { status: statut });
}

beforeEach(() => {
  quitterVers.mockReset();
  chemin = "/";
  personne = GERANT;
});
afterEach(() => vi.unstubAllGlobals());

describe("Cadre des écrans connectés (maquettes v3, § 0.2 ; R0-03)", () => {
  it("« Aller au contenu » en premier élément focalisable, vers le contenu principal", async () => {
    render(<CadreConnecte personne={GERANT}>contenu</CadreConnecte>);
    await userEvent.tab();
    const lien = screen.getByRole("link", { name: TEXTES.allerAuContenu });
    expect(lien).toHaveFocus();
    expect(lien).toHaveAttribute("href", "#contenu");
    expect(screen.getByRole("main")).toHaveAttribute("id", "contenu");
  });

  it.each([
    [GERANT, "M. Martin · Rôle : Gérant"],
    [ASSOCIE, "Mme Durand · Rôle : Associé"],
    [OPERATEUR, "M. Petit · Rôle : Opérateur"],
  ])("nom affiché et rôle en mots du lexique : %o", (qui, texte) => {
    render(<CadreConnecte personne={qui}>contenu</CadreConnecte>);
    expect(screen.getByText(texte)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: C.seDeconnecter })).toBeInTheDocument();
  });

  it("menu du gérant : « À faire » et « Administration » (liste des utilisateurs)", () => {
    render(<CadreConnecte personne={GERANT}>contenu</CadreConnecte>);
    const menu = screen.getByRole("navigation", { name: C.menuPrincipal });
    expect(within(menu).getByRole("link", { name: C.aFaire })).toHaveAttribute("href", "/");
    expect(within(menu).getByRole("link", { name: C.administration })).toHaveAttribute(
      "href",
      "/administration/utilisateurs",
    );
  });

  it.each([[ASSOCIE], [OPERATEUR]])("menu sans « Administration » : %o", (qui) => {
    render(<CadreConnecte personne={qui}>contenu</CadreConnecte>);
    const menu = screen.getByRole("navigation");
    expect(within(menu).getAllByRole("link").map((l) => l.textContent)).toEqual([C.aFaire]);
  });

  it("page en cours signalée dans le menu (aria-current), y compris sur les pages profondes", () => {
    chemin = "/administration/utilisateurs/0192";
    render(<CadreConnecte personne={GERANT}>contenu</CadreConnecte>);
    expect(screen.getByRole("link", { name: C.administration })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: C.aFaire })).not.toHaveAttribute("aria-current");
  });
});

describe("Se déconnecter (R0-03, R0-08)", () => {
  it("POST /api/identity/auth/deconnexion puis Se connecter avec « Déconnexion effectuée. », page remplacée", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(204));
    vi.stubGlobal("fetch", appel);
    render(<SeDeconnecter />);
    await userEvent.click(screen.getByRole("button", { name: C.seDeconnecter }));
    await waitFor(() => expect(quitterVers).toHaveBeenCalledWith("/connexion?motif=deconnexion"));
    expect(appel.mock.calls[0]![0]).toBe("/api/identity/auth/deconnexion");
    expect(appel.mock.calls[0]![1].method).toBe("POST");
  });

  it("session déjà expirée (401) : Se connecter quand même, avec « Déconnexion effectuée. »", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(401)));
    render(<SeDeconnecter />);
    await userEvent.click(screen.getByRole("button", { name: C.seDeconnecter }));
    await waitFor(() => expect(quitterVers).toHaveBeenCalledWith("/connexion?motif=deconnexion"));
  });

  it("panne : message « Erreur », on reste connecté (la session n'est pas fermée)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<SeDeconnecter />);
    await userEvent.click(screen.getByRole("button", { name: C.seDeconnecter }));
    const alerte = await screen.findByRole("alert");
    expect(alerte).toHaveTextContent(TEXTES.etats.erreur);
    expect(alerte).toHaveTextContent(TEXTES.commun.erreurInattendue);
    expect(quitterVers).not.toHaveBeenCalled();
  });
});

describe("Accueil « À faire » (maquettes v3, écran 5 ; UX-25, UX-27)", () => {
  it("titre « À faire », titre de l'onglet, aucun bouton principal", async () => {
    render(await Accueil({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(A.titre);
    expect(metadata.title).toBe("À faire — LePalier");
    expect(screen.queryByRole("button")).toBeNull();
  });

  it.each([
    [GERANT, A.videGestion],
    [OPERATEUR, A.videGestion],
    [ASSOCIE, A.videAssocie],
  ])("état vide selon le rôle : %o", async (qui, texte) => {
    personne = qui;
    render(await Accueil({ searchParams: Promise.resolve({}) }));
    expect(screen.getByText(texte)).toBeInTheDocument();
  });

  it("après l'activation : bandeau « Fait » et la façon de se connecter la prochaine fois (N19)", async () => {
    render(await Accueil({ searchParams: Promise.resolve({ motif: "compte_active" }) }));
    const bandeau = screen.getByRole("status");
    expect(bandeau).toHaveTextContent(TEXTES.etats.fait);
    expect(bandeau).toHaveTextContent(A.compteActive);
  });

  it("codes de secours perdus au rechargement : bandeau « Attention » (N18)", async () => {
    render(await Accueil({ searchParams: Promise.resolve({ motif: "codes_perdus" }) }));
    const bandeau = screen.getByRole("alert");
    expect(bandeau).toHaveTextContent(TEXTES.etats.attention);
    expect(bandeau).toHaveTextContent(TEXTES.codes.perdus);
  });

  it("après avoir quitté soi-même le rôle de gérant (A8) : bandeau « Fait » avec le rôle relu chez identity", async () => {
    personne = { ...ASSOCIE };
    render(await Accueil({ searchParams: Promise.resolve({ motif: "role_quitte" }) }));
    expect(screen.getByRole("status")).toHaveTextContent(
      "Votre rôle est maintenant Associé. L'Administration n'est plus accessible depuis ce compte.",
    );
  });

  it("« role_quitte » ouvert par un gérant (adresse retapée) : aucun bandeau", async () => {
    const { container } = render(await Accueil({ searchParams: Promise.resolve({ motif: "role_quitte" }) }));
    expect(container.querySelector(".bandeau")).toBeNull();
  });

  it("motif inconnu : aucun bandeau", async () => {
    const { container } = render(await Accueil({ searchParams: Promise.resolve({ motif: "autre" }) }));
    expect(container.querySelector(".bandeau")).toBeNull();
  });
});

describe("Écrans connectés : identity indisponible (UX-30)", () => {
  it("« Information momentanément indisponible », sans menu ni contenu", async () => {
    personne = null;
    render(await MiseEnPageConnectee({ children: <p>contenu</p> }));
    expect(screen.getByText(TEXTES.indisponible)).toBeInTheDocument();
    expect(screen.queryByText("contenu")).toBeNull();
    expect(screen.queryByRole("navigation")).toBeNull();
  });

  it("personne connectée : cadre et contenu", async () => {
    render(await MiseEnPageConnectee({ children: <p>contenu</p> }));
    expect(screen.getByText("contenu")).toBeInTheDocument();
    expect(screen.getByRole("navigation")).toBeInTheDocument();
  });
});
