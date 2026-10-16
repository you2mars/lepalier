import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Personne } from "@/lib/session";
import { TEXTES } from "@/textes";
import Introuvable from "./not-found";

let personne: Personne | null = null;
vi.mock("next/navigation", () => ({ usePathname: () => "/adresse-inconnue" }));
vi.mock("@/lib/session", () => ({ personneSiConnectee: async () => personne }));

const GERANT: Personne = { id: "1", email: "gerant@exemple.fr", nom_affiche: "M. Martin", role: "gerant" };

beforeEach(() => {
  personne = null;
});

describe("page introuvable", () => {
  it("sans session : message 404 de commun et lien vers l'accueil, cadre public", async () => {
    render(await Introuvable());
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(TEXTES.commun.introuvable);
    expect(screen.getByRole("link", { name: TEXTES.retourAccueil })).toHaveAttribute("href", "/");
    expect(screen.queryByRole("navigation")).toBeNull();
  });

  it("personne connectée : même message dans le cadre connecté, menu et « Se déconnecter » gardés (constat UX (5))", async () => {
    personne = GERANT;
    render(await Introuvable());
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(TEXTES.commun.introuvable);
    expect(screen.getByRole("link", { name: TEXTES.retourAccueil })).toHaveAttribute("href", "/");
    expect(screen.getByRole("navigation")).toBeInTheDocument();
    expect(screen.getByText(`M. Martin · ${TEXTES.cadre.role} ${TEXTES.roles.gerant}`)).toBeInTheDocument();
  });
});
