import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TEXTES } from "@/textes";
import { BoutonLien } from "./BoutonLien";
import { CleARecopier } from "./CleARecopier";
import { CodeQr } from "./CodeQr";
import { Depliant } from "./Depliant";
import { Encadre } from "./Encadre";
import { EtatVide } from "./EtatVide";
import { FeuilleImpression, HorsImpression } from "./Impression";
import { LienBouton } from "./LienBouton";
import { ListeCodes } from "./ListeCodes";
import { RappelPermanent } from "./RappelPermanent";
import { Squelette } from "./Squelette";

// Composants du design system minimal (UX_CHARTE § 9) : les écrans n'ont pas de style propre (front/CLAUDE.md).
describe("Encadre et Depliant", () => {
  it("bloc encadré ; dépliant fermé par défaut, résumé cliquable", async () => {
    render(
      <Encadre>
        <p>Avant de commencer</p>
        <Depliant resume="Autres applications possibles">
          <p>FreeOTP</p>
        </Depliant>
      </Encadre>,
    );
    expect(screen.getByText("Avant de commencer").parentElement).toHaveClass("encadre");
    const resume = screen.getByText("Autres applications possibles");
    expect(resume.tagName).toBe("SUMMARY");
    expect(resume.closest("details")).not.toHaveAttribute("open");
    await userEvent.click(resume);
    expect(resume.closest("details")).toHaveAttribute("open");
  });
});

describe("BoutonLien et LienBouton", () => {
  it("BoutonLien : action dans la page, jamais un envoi de formulaire ; option sous le champ", async () => {
    const action = vi.fn();
    const { container } = render(
      <form onSubmit={() => action("envoi")}>
        <BoutonLien sousChamp onClick={() => action("clic")}>
          Utiliser un code de secours
        </BoutonLien>
      </form>,
    );
    const bouton = screen.getByRole("button", { name: "Utiliser un code de secours" });
    expect(bouton).toHaveAttribute("type", "button");
    expect(bouton).toHaveClass("bouton-lien");
    expect(container.querySelector(".action-sous-champ")).toContainElement(bouton);
    await userEvent.click(bouton);
    expect(action.mock.calls).toEqual([["clic"]]);
  });

  it("LienBouton : lien présenté comme un bouton secondaire", () => {
    render(<LienBouton href="otpauth://totp/x">Ajouter à mon application</LienBouton>);
    const lien = screen.getByRole("link", { name: "Ajouter à mon application" });
    expect(lien).toHaveAttribute("href", "otpauth://totp/x");
    expect(lien).toHaveClass("bouton", "bouton-secondaire");
  });
});

describe("CleARecopier", () => {
  it("clé par groupes de 4, lue groupe par groupe ; « Copier la clé » sans espaces, « Clé copiée. » annoncé", async () => {
    const user = userEvent.setup();
    render(<CleARecopier groupes={["JBSW", "Y3DP", "EH"]} />);
    expect(screen.getByLabelText("JBSW Y3DP EH")).toHaveTextContent("JBSW Y3DP EH");
    const ecrire = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    await user.click(screen.getByRole("button", { name: TEXTES.activation.copierCle }));
    expect(ecrire).toHaveBeenCalledWith("JBSWY3DPEH");
    expect(await screen.findByRole("status")).toHaveTextContent(TEXTES.activation.cleCopiee);
  });

  it("presse-papiers indisponible : rien n'est annoncé, la clé reste affichée", async () => {
    const user = userEvent.setup();
    render(<CleARecopier groupes={["ABCD"]} />);
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new Error("refusé"));
    await user.click(screen.getByRole("button", { name: TEXTES.activation.copierCle }));
    expect(screen.getByRole("status")).toHaveTextContent("");
  });
});

describe("CodeQr", () => {
  it("image SVG du contenu, avec son texte de remplacement", async () => {
    render(<CodeQr valeur="otpauth://totp/LePalier:x?secret=ABCD" alt="Code à scanner" />);
    const image = await screen.findByRole("img", { name: "Code à scanner" });
    expect(image.getAttribute("src")).toMatch(/^data:image\/svg\+xml/);
    expect(image).toHaveClass("qr");
  });
});

describe("ListeCodes", () => {
  it("liste numérotée nommée, police à chasse fixe", () => {
    render(<ListeCodes codes={["AAAA-BBBB-CCCC", "DDDD-EEEE-FFFF"]} libelle="Vos codes de secours" />);
    const liste = screen.getByRole("list", { name: "Vos codes de secours" });
    expect(liste.tagName).toBe("OL");
    expect(liste).toHaveClass("codes");
    expect(within(liste).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "AAAA-BBBB-CCCC",
      "DDDD-EEEE-FFFF",
    ]);
  });
});

describe("RappelPermanent, EtatVide, Squelette", () => {
  it("rappel visible en permanence", () => {
    render(<RappelPermanent>Ne fermez pas cette page.</RappelPermanent>);
    expect(screen.getByText("Ne fermez pas cette page.")).toHaveClass("rappel-permanent");
  });

  it("état vide : explique (UX-27)", () => {
    render(<EtatVide>Rien à faire pour le moment.</EtatVide>);
    expect(screen.getByText("Rien à faire pour le moment.")).toHaveClass("etat-vide");
  });

  it("squelette : chargement annoncé (aria-busy), n blocs ou cartes, sans texte", () => {
    const { container } = render(<Squelette forme="carte" nombre={3} />);
    expect(container.firstElementChild).toHaveAttribute("aria-busy", "true");
    expect(container.querySelectorAll(".squelette.squelette-carte")).toHaveLength(3);
    expect(container.textContent).toBe("");
  });
});

describe("FeuilleImpression et HorsImpression (UX-10)", () => {
  it("feuille : nom de l'application en tête, ignorée des lecteurs d'écran ; le reste de l'écran masqué à l'impression", () => {
    const { container } = render(
      <>
        <HorsImpression>
          <h1>Vos codes de secours</h1>
        </HorsImpression>
        <FeuilleImpression>
          <h2>Vos codes de secours</h2>
        </FeuilleImpression>
      </>,
    );
    const feuille = container.querySelector(".feuille-impression")!;
    expect(feuille).toHaveAttribute("aria-hidden", "true");
    expect(feuille.firstElementChild).toHaveTextContent(TEXTES.application);
    expect(container.querySelector(".ecran-seul")).toContainElement(screen.getByRole("heading", { level: 1 }));
  });
});
