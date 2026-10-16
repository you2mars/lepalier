import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { TEXTES } from "@/textes";
import { Bandeau } from "./Bandeau";
import { Bouton } from "./Bouton";
import { Champ } from "./Champ";
import { ChampMotDePasse } from "./ChampMotDePasse";

describe("Bandeau (UX-4, UX-14)", () => {
  it("succès : mot d'état écrit, annoncé poliment (role=status)", () => {
    render(<Bandeau etat="fait" message="Déconnexion effectuée." />);
    const bandeau = screen.getByRole("status");
    expect(bandeau).toHaveTextContent(TEXTES.etats.fait);
    expect(bandeau).toHaveTextContent("Déconnexion effectuée.");
  });

  it.each([
    ["attention", TEXTES.etats.attention],
    ["erreur", TEXTES.etats.erreur],
  ] as const)("%s : mot d'état écrit, annoncé tout de suite (role=alert)", (etat, mot) => {
    render(<Bandeau etat={etat} message="Message." />);
    expect(screen.getByRole("alert")).toHaveTextContent(mot);
  });

  it("le mot d'état est sur sa propre ligne, en gras, jamais une couleur seule", () => {
    render(<Bandeau etat="erreur" message="Une erreur…" />);
    const mot = screen.getByText(TEXTES.etats.erreur);
    expect(mot.tagName).toBe("STRONG");
    expect(mot.closest("p")).not.toHaveTextContent("Une erreur");
  });
});

describe("Champ (UX-17, UX-19, UX-15)", () => {
  it("libellé associé, aide et erreur annoncées par aria-describedby, aria-invalid", () => {
    render(<Champ id="email" libelle="Adresse e-mail" aide="Une aide." erreur="Une erreur." type="email" />);
    const champ = screen.getByLabelText("Adresse e-mail");
    expect(champ).toHaveAccessibleDescription("Une aide. Une erreur.");
    expect(champ).toHaveAttribute("aria-invalid", "true");
  });

  it("sans erreur : pas d'aria-invalid", () => {
    render(<Champ id="email" libelle="Adresse e-mail" type="email" />);
    expect(screen.getByLabelText("Adresse e-mail")).not.toHaveAttribute("aria-invalid");
  });

  it("champ facultatif marqué « (facultatif) » dans le libellé (UX-23)", () => {
    render(<Champ id="note" libelle="Note" facultatif />);
    expect(screen.getByLabelText("Note (facultatif)")).toBeInTheDocument();
  });
});

describe("ChampMotDePasse (front/CLAUDE.md, M12)", () => {
  it("masqué par défaut, attributs anti-correcteur, autocomplete choisi", () => {
    render(<ChampMotDePasse id="mdp" libelle="Mot de passe" autoComplete="current-password" />);
    const champ = screen.getByLabelText("Mot de passe");
    expect(champ).toHaveAttribute("type", "password");
    expect(champ).toHaveAttribute("autocomplete", "current-password");
    expect(champ).toHaveAttribute("autocapitalize", "none");
    expect(champ).toHaveAttribute("autocorrect", "off");
    expect(champ).toHaveAttribute("spellcheck", "false");
  });

  it("« Afficher » bascule en texte, garde les attributs, change de nom et d'état (aria-pressed)", async () => {
    render(<ChampMotDePasse id="mdp" libelle="Mot de passe" autoComplete="new-password" />);
    const bouton = screen.getByRole("button", { name: TEXTES.motDePasse.afficherAccessible });
    expect(bouton).toHaveAttribute("aria-pressed", "false");
    expect(bouton).toHaveTextContent(TEXTES.motDePasse.afficher);
    await userEvent.click(bouton);
    const champ = screen.getByLabelText("Mot de passe");
    expect(champ).toHaveAttribute("type", "text");
    expect(champ).toHaveAttribute("autocapitalize", "none");
    expect(champ).toHaveAttribute("spellcheck", "false");
    const masquer = screen.getByRole("button", { name: TEXTES.motDePasse.masquerAccessible });
    expect(masquer).toHaveAttribute("aria-pressed", "true");
    expect(masquer).toHaveTextContent(TEXTES.motDePasse.masquer);
  });

  it("le bouton n'envoie jamais le formulaire", () => {
    render(<ChampMotDePasse id="mdp" libelle="Mot de passe" autoComplete="current-password" />);
    expect(screen.getByRole("button", { name: TEXTES.motDePasse.afficherAccessible })).toHaveAttribute("type", "button");
  });
});

describe("Bouton (UX-22)", () => {
  it("principal : type submit par défaut", () => {
    render(<Bouton>Se connecter</Bouton>);
    expect(screen.getByRole("button", { name: "Se connecter" })).toHaveAttribute("type", "submit");
  });

  it("pendant l'envoi : désactivé, texte « Envoi en cours… », double clic impossible", () => {
    render(<Bouton envoiEnCours>Se connecter</Bouton>);
    const bouton = screen.getByRole("button", { name: TEXTES.envoiEnCours });
    expect(bouton).toBeDisabled();
    expect(bouton).toHaveAttribute("aria-busy", "true");
  });

  it("secondaire : type button, classe distincte", () => {
    render(<Bouton variante="secondaire">Annuler</Bouton>);
    const bouton = screen.getByRole("button", { name: "Annuler" });
    expect(bouton).toHaveAttribute("type", "button");
    expect(bouton.className).toContain("secondaire");
  });
});

describe("ChampMotDePasse : noms accessibles propres (deux champs sur un même écran)", () => {
  it("le bouton « Afficher » d'un second champ porte son propre nom, lu sans ambiguïté", async () => {
    render(
      <ChampMotDePasse
        id="confirmation"
        libelle={TEXTES.motDePasse.confirmation}
        autoComplete="new-password"
        nomsAccessibles={{
          afficher: TEXTES.motDePasse.afficherConfirmationAccessible,
          masquer: TEXTES.motDePasse.masquerConfirmationAccessible,
        }}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: TEXTES.motDePasse.afficherConfirmationAccessible }));
    expect(screen.getByRole("button", { name: TEXTES.motDePasse.masquerConfirmationAccessible })).toHaveTextContent(
      TEXTES.motDePasse.masquer,
    );
    expect(screen.getByLabelText(TEXTES.motDePasse.confirmation)).toHaveAttribute("type", "text");
  });
});
