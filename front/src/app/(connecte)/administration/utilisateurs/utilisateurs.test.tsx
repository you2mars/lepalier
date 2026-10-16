import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { laisserMessage, MessageFlashProvider } from "@/components/cadre/MessageFlash";
import type { Personne } from "@/lib/session";
import { TEXTES } from "@/textes";
import Page, { metadata } from "./page";

const L = TEXTES.utilisateurs.liste;
const GERANT: Personne = { id: "g", email: "gerant@exemple.fr", nom_affiche: "M. Martin", role: "gerant" };
const UTILISATEURS = [
  {
    id: "0192-a",
    email: "gerant@exemple.fr",
    nom_affiche: "M. Martin",
    role: "gerant",
    statut: "actif",
    statut_libelle: "Accès actif",
    invitation_envoyee_le: null,
    invitation_expire_le: null,
  },
  {
    id: "0192-b",
    email: "marie.durand@exemple.fr",
    nom_affiche: "Mme Durand",
    role: "associe",
    statut: "invite",
    statut_libelle: "Invitation envoyée",
    invitation_envoyee_le: "2026-10-03T08:00:00+00:00",
    invitation_expire_le: "2026-10-10T08:00:00+00:00",
  },
  {
    id: "0192-c",
    email: "paul.petit@exemple.fr",
    nom_affiche: "M. Petit",
    role: "operateur",
    statut: "invite",
    statut_libelle: "Invitation expirée",
    invitation_envoyee_le: "2026-09-20T08:00:00+00:00",
    invitation_expire_le: "2026-09-27T08:00:00+00:00",
  },
];

let personne: Personne | null = GERANT;
const lireConnecte = vi.fn();
vi.mock("next/navigation", () => ({ usePathname: () => "/administration/utilisateurs" }));
vi.mock("@/lib/session", () => ({
  personneConnectee: async () => personne,
  lireConnecte: (chemin: string) => lireConnecte(chemin),
}));

beforeEach(() => {
  sessionStorage.clear();
  personne = GERANT;
  lireConnecte.mockReset();
  lireConnecte.mockResolvedValue({ ok: true, statut: 200, donnees: { utilisateurs: UTILISATEURS } });
});

describe("Administration › Utilisateurs (maquettes v3, écran 6.1 ; R0-04)", () => {
  it("titre, titre de l'onglet, fil d'Ariane (« Administration » en texte, page en cours signalée)", async () => {
    render(await Page({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(L.titre);
    expect(metadata.title).toBe("Utilisateurs — LePalier");
    const fil = screen.getByRole("navigation", { name: TEXTES.cadre.filAriane });
    expect(within(fil).getAllByRole("listitem").map((e) => e.textContent)).toEqual([
      TEXTES.cadre.administration,
      L.titre,
    ]);
    expect(within(fil).queryAllByRole("link")).toHaveLength(0);
    expect(within(fil).getByText(L.titre)).toHaveAttribute("aria-current", "page");
    expect(lireConnecte).toHaveBeenCalledWith("/identity/utilisateurs");
  });

  it("« Inviter une personne » : bouton principal, seul de l'écran", async () => {
    render(await Page({ searchParams: Promise.resolve({}) }));
    const inviter = screen.getByRole("link", { name: L.inviter });
    expect(inviter).toHaveAttribute("href", "/administration/utilisateurs/inviter");
    expect(inviter).toHaveClass("bouton-principal");
    expect(document.querySelectorAll(".bouton-principal")).toHaveLength(1);
  });

  it("tableau : nom, adresse, rôle en mots du lexique, statut en mots d'identity, dans l'ordre reçu (tri par nom)", async () => {
    render(await Page({ searchParams: Promise.resolve({}) }));
    const tableau = screen.getByRole("table", { name: L.titre });
    const lignes = within(tableau).getAllByRole("row").slice(1);
    expect(
      lignes.map((ligne) =>
        within(ligne)
          .getAllByRole("cell")
          .slice(0, 4)
          .map((c) => c.textContent),
      ),
    ).toEqual([
      ["M. Martin", "gerant@exemple.fr", "Gérant", "Accès actif"],
      ["Mme Durand", "marie.durand@exemple.fr", "Associé", "Invitation envoyée"],
      ["M. Petit", "paul.petit@exemple.fr", "Opérateur", "Invitation expirée"],
    ]);
    expect(within(tableau).getAllByRole("columnheader").map((e) => e.textContent)).toEqual([
      L.colonnes.nom,
      L.colonnes.adresse,
      L.colonnes.role,
      L.colonnes.statut,
      L.colonnes.actions,
    ]);
  });

  it("« Gérer l'accès » : lien vers la fiche, complété « de {nom} » pour les lecteurs d'écran (M8)", async () => {
    render(await Page({ searchParams: Promise.resolve({}) }));
    const tableau = screen.getByRole("table", { name: L.titre });
    const lien = within(tableau).getByRole("link", { name: "Gérer l'accès de Mme Durand" });
    expect(lien).toHaveAttribute("href", "/administration/utilisateurs/0192-b");
    expect(lien).toHaveTextContent(/^Gérer l'accès/);
  });

  it("mobile : une carte par personne (nom, rôle, statut), toute la carte est le lien vers la fiche", async () => {
    const { container } = render(await Page({ searchParams: Promise.resolve({}) }));
    const cartes = within(container.querySelector(".cartes") as HTMLElement).getAllByRole("link");
    expect(cartes.map((c) => c.getAttribute("href"))).toEqual(UTILISATEURS.map((u) => `/administration/utilisateurs/${u.id}`));
    // revue UX (M6) : le lecteur d'écran entend aussi le rôle et le statut
    expect(cartes[1]).toHaveAccessibleName("Gérer l'accès de Mme Durand Associé Invitation envoyée");
    expect(cartes[1]).toHaveTextContent("Mme Durand");
    expect(cartes[1]).toHaveTextContent("Associé");
    expect(cartes[1]).toHaveTextContent("Invitation envoyée");
  });

  it("identity en panne : « Information momentanément indisponible », titre et bouton gardés (UX-30)", async () => {
    lireConnecte.mockResolvedValue({ ok: false, statut: 502 });
    render(await Page({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(L.titre);
    expect(screen.getByText(TEXTES.indisponible)).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
  });
});

describe("Page réservée au gérant (maquettes v3, écran 7 ; R0-06)", () => {
  it.each([
    ["associé", { ...GERANT, role: "associe" as const }],
    ["opérateur", { ...GERANT, role: "operateur" as const }],
  ])("%s : titre, explication, « Retour à l'accueil » en bouton principal ; aucune lecture des utilisateurs", async (_, qui) => {
    personne = qui;
    render(await Page({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(TEXTES.reservee.titre);
    expect(screen.getByText(TEXTES.reservee.reservee)).toBeInTheDocument();
    expect(screen.getByText(TEXTES.reservee.demandez)).toBeInTheDocument();
    const retour = screen.getByRole("link", { name: TEXTES.retourAccueil });
    expect(retour).toHaveAttribute("href", "/");
    expect(retour).toHaveClass("bouton-principal");
    expect(lireConnecte).not.toHaveBeenCalled();
  });

  it("refus d'identity (403, rôle changé entre-temps) : même page, jamais une page blanche", async () => {
    lireConnecte.mockResolvedValue({ ok: false, statut: 403 });
    render(await Page({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(TEXTES.reservee.titre);
  });
});

describe("Après une invitation : la liste dit ce qui a été fait (UX-4, UX-24)", () => {
  it("bandeau « Fait » avec le nom et l'adresse, lus dans la liste ; aucune donnée personnelle dans l'adresse de la page", async () => {
    render(await Page({ searchParams: Promise.resolve({ invitee: "0192-b" }) }));
    const bandeau = screen.getByRole("status");
    expect(bandeau).toHaveTextContent(TEXTES.etats.fait);
    expect(bandeau).toHaveTextContent(
      "Invitation envoyée à Mme Durand (marie.durand@exemple.fr). Le lien est valable 7 jours.",
    );
  });

  it("identifiant inconnu : aucun bandeau", async () => {
    const { container } = render(await Page({ searchParams: Promise.resolve({ invitee: "autre" }) }));
    expect(container.querySelector(".bandeau")).toBeNull();
  });
});

describe("Après l'annulation d'une invitation : message laissé par la fiche (stockage de session de l'onglet)", () => {
  it("bandeau « Fait » sur la page d'arrivée, chargée en entier ; message effacé une fois lu", async () => {
    laisserMessage({ etat: "fait", texte: "Invitation de Mme Durand annulée.", pour: "/administration/utilisateurs" });
    render(<MessageFlashProvider>{await Page({ searchParams: Promise.resolve({}) })}</MessageFlashProvider>);
    expect(screen.getByRole("status")).toHaveTextContent("Invitation de Mme Durand annulée.");
    expect(sessionStorage.length).toBe(0);
  });

  it("message laissé pour une autre page : rien ici", async () => {
    laisserMessage({ etat: "fait", texte: "Autre.", pour: "/ailleurs" });
    render(<MessageFlashProvider>{await Page({ searchParams: Promise.resolve({}) })}</MessageFlashProvider>);
    expect(screen.queryByRole("status")).toBeNull();
  });
});
