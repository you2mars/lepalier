import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TEXTES } from "@/textes";
import Introuvable from "./not-found";

describe("page introuvable", () => {
  it("message 404 de commun et lien vers l'accueil", () => {
    render(<Introuvable />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(TEXTES.commun.introuvable);
    expect(screen.getByRole("link", { name: TEXTES.retourAccueil })).toHaveAttribute("href", "/");
  });
});
