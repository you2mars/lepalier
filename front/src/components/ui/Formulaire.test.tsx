import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Bouton } from "./Bouton";
import { Champ } from "./Champ";
import { ChampMotDePasse } from "./ChampMotDePasse";
import { Formulaire } from "./Formulaire";

// Formulaire commun (UX-19, UX-22) : envoi en POST sans validation du navigateur ; vérification à la sortie du
// champ, sauf quand le pointeur appuie sur le bouton d'envoi (un message affiché pendant le clic déplacerait le
// bouton et le clic serait perdu) : l'envoi vérifie alors tout.
function afficher(verifier = vi.fn(), envoyer = vi.fn()) {
  render(
    <Formulaire onSubmit={envoyer}>
      <Champ id="nom" libelle="Nom affiché" verifierALaSortie={verifier} />
      <ChampMotDePasse id="mdp" libelle="Mot de passe" autoComplete="new-password" verifierALaSortie={verifier} />
      <Bouton>Continuer</Bouton>
    </Formulaire>,
  );
  return { verifier, envoyer };
}

describe("Formulaire", () => {
  it("POST sans validation du navigateur ; l'envoi n'est jamais une navigation", async () => {
    const { envoyer } = afficher();
    const formulaire = screen.getByRole("button", { name: "Continuer" }).closest("form")!;
    expect(formulaire).toHaveAttribute("method", "post");
    expect(formulaire).toHaveAttribute("novalidate");
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));
    expect(envoyer).toHaveBeenCalledOnce();
    expect((envoyer.mock.calls[0]![0] as Event).defaultPrevented).toBe(true);
  });

  it("sortie du champ au clavier (Tab) : vérification faite", async () => {
    const { verifier } = afficher();
    await userEvent.click(screen.getByLabelText("Nom affiché"));
    await userEvent.tab();
    expect(verifier).toHaveBeenCalledOnce();
  });

  it("sortie vers un autre champ à la souris : vérification faite", async () => {
    const { verifier } = afficher();
    await userEvent.click(screen.getByLabelText("Nom affiché"));
    await userEvent.click(screen.getByLabelText("Mot de passe"));
    expect(verifier).toHaveBeenCalledOnce();
  });

  it("appui du pointeur sur le bouton d'envoi : la sortie ne vérifie rien, l'envoi a lieu", async () => {
    const { verifier, envoyer } = afficher();
    await userEvent.click(screen.getByLabelText("Mot de passe"));
    await userEvent.click(screen.getByRole("button", { name: "Continuer" }));
    expect(verifier).not.toHaveBeenCalled();
    expect(envoyer).toHaveBeenCalledOnce();
  });

  it("appui sans envoi (pointeur relâché ailleurs) : la sortie suivante vérifie de nouveau", () => {
    const { verifier } = afficher();
    const nom = screen.getByLabelText("Nom affiché");
    fireEvent.pointerDown(screen.getByRole("button", { name: "Continuer" }));
    fireEvent.blur(nom);
    expect(verifier).not.toHaveBeenCalled();
    fireEvent.blur(nom);
    expect(verifier).toHaveBeenCalledOnce();
  });

  it("appui sur un bouton qui n'envoie pas (« Afficher ») : la sortie vérifie", () => {
    const { verifier } = afficher();
    fireEvent.pointerDown(screen.getByRole("button", { name: "Afficher le mot de passe" }));
    fireEvent.blur(screen.getByLabelText("Mot de passe"));
    expect(verifier).toHaveBeenCalledOnce();
  });

  it("champ hors d'un Formulaire : la vérification à la sortie fonctionne aussi", async () => {
    const verifier = vi.fn();
    render(<Champ id="seul" libelle="Seul" verifierALaSortie={verifier} />);
    await userEvent.click(screen.getByLabelText("Seul"));
    await userEvent.tab();
    expect(verifier).toHaveBeenCalledOnce();
  });
});
