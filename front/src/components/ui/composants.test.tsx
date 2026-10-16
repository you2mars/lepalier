import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TEXTES } from "@/textes";
import { AdresseEmail } from "./AdresseEmail";
import { BoutonLien } from "./BoutonLien";
import { CleARecopier } from "./CleARecopier";
import { CodeQr } from "./CodeQr";
import { Depliant } from "./Depliant";
import { Encadre } from "./Encadre";
import { EtatVide } from "./EtatVide";
import { FilAriane } from "./FilAriane";
import { FeuilleImpression, HorsImpression } from "./Impression";
import { Lien } from "./Lien";
import { LienBouton } from "./LienBouton";
import { ListeCodes } from "./ListeCodes";
import { RappelPermanent } from "./RappelPermanent";
import { Squelette } from "./Squelette";
import { SurEcranTactile } from "./SurEcranTactile";
import { TableauResponsive } from "./TableauResponsive";
import { TexteMasque } from "./TexteMasque";

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

  it("LienBouton principal : lien présenté comme le bouton principal de l'écran", () => {
    render(
      <LienBouton href="/administration/utilisateurs/inviter" variante="principal">
        Inviter une personne
      </LienBouton>,
    );
    expect(screen.getByRole("link", { name: "Inviter une personne" })).toHaveClass("bouton", "bouton-principal");
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

describe("TexteMasque", () => {
  it("lu par les lecteurs d'écran, invisible à l'écran", () => {
    render(
      <a href="/x">
        Gérer l'accès <TexteMasque>de Mme Durand</TexteMasque>
      </a>,
    );
    expect(screen.getByRole("link", { name: "Gérer l'accès de Mme Durand" })).toBeInTheDocument();
    expect(screen.getByText("de Mme Durand", { exact: false })).toHaveClass("masque-visuellement");
  });
});

describe("FilAriane (UX-9)", () => {
  it("navigation nommée, étapes dans l'ordre ; liens seulement là où une page existe ; page en cours signalée", () => {
    render(
      <FilAriane
        etapes={[
          { libelle: "Administration" },
          { libelle: "Utilisateurs", href: "/administration/utilisateurs" },
          { libelle: "Inviter" },
        ]}
      />,
    );
    const fil = screen.getByRole("navigation", { name: TEXTES.cadre.filAriane });
    const elements = within(fil).getAllByRole("listitem");
    expect(elements.map((e) => e.textContent)).toEqual(["Administration", "Utilisateurs", "Inviter"]);
    expect(within(elements[0]!).queryByRole("link")).toBeNull();
    expect(within(elements[1]!).getByRole("link")).toHaveAttribute("href", "/administration/utilisateurs");
    expect(within(elements[2]!).getByText("Inviter")).toHaveAttribute("aria-current", "page");
  });
});

describe("TableauResponsive (UX-26)", () => {
  const COLONNES = [{ titre: "Nom" }, { titre: "Statut" }, { titre: "Actions", masque: true }];
  const LIGNES = [
    {
      cle: "1",
      cellules: ["Mme Durand", "Accès actif", <a key="a" href="/fiche/1">Gérer</a>],
      carte: { href: "/fiche/1", prefixeMasque: "Gérer l'accès de", contenu: ["Mme Durand", "Accès actif"] },
    },
  ];

  it("ordinateur : tableau nommé, en-têtes de colonnes, en-tête des boutons masqué mais lu", () => {
    render(<TableauResponsive libelle="Utilisateurs" colonnes={COLONNES} lignes={LIGNES} />);
    const tableau = screen.getByRole("table", { name: "Utilisateurs" });
    const entetes = within(tableau).getAllByRole("columnheader");
    expect(entetes.map((e) => e.textContent)).toEqual(["Nom", "Statut", "Actions"]);
    expect(within(entetes[2]!).getByText("Actions")).toHaveClass("masque-visuellement");
    expect(within(tableau).getAllByRole("row")).toHaveLength(2);
  });

  it("mobile : une carte par ligne, toute la carte est un lien, dont tout le contenu est lu (début masqué à l'écran)", () => {
    const { container } = render(<TableauResponsive libelle="Utilisateurs" colonnes={COLONNES} lignes={LIGNES} />);
    const cartes = container.querySelector(".cartes")!;
    const lien = within(cartes as HTMLElement).getByRole("link", { name: "Gérer l'accès de Mme Durand Accès actif" });
    expect(lien).toHaveAttribute("href", "/fiche/1");
    expect(lien).toHaveTextContent("Mme Durand");
  });
});

describe("AdresseEmail et Lien (revue UX, M3 et M4)", () => {
  it("adresse e-mail : jamais coupée à un trait d'union, coupée à la largeur seulement si elle est trop longue", () => {
    render(<AdresseEmail>exemple-mobile-360@essai.local</AdresseEmail>);
    expect(screen.getByText("exemple-mobile-360@essai.local")).toHaveClass("adresse-email");
  });

  it("lien de texte : cible de 44 px (classe lien)", () => {
    render(<Lien href="/connexion">Retour à la connexion</Lien>);
    const lien = screen.getByRole("link", { name: "Retour à la connexion" });
    expect(lien).toHaveAttribute("href", "/connexion");
    expect(lien).toHaveClass("lien");
  });

  it("sur écran tactile seulement : contenu enveloppé, caché sur un poste à souris par la feuille de style", () => {
    render(<SurEcranTactile><a href="otpauth://x">Ajouter à mon application</a></SurEcranTactile>);
    expect(screen.getByRole("link").parentElement).toHaveClass("seulement-tactile");
  });
});
