import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { libelle, messageMotDePasse } from "@/lib/libelles";
import { TEXTES } from "@/textes";
import { FormulaireActivation } from "./FormulaireActivation";
import { metadata } from "./page";

const JETON = "a".repeat(43);
const URI =
  "otpauth://totp/LePalier:Mme%20Durand?secret=JBSWY3DPEHPK3PXPJBSWY3DP&issuer=LePalier&algorithm=SHA1&digits=6&period=30";
const DEBUT = { uri_otpauth: URI, nom_affiche: "Mme Durand", email: "marie.durand@exemple.fr" };
const ACTIVE = {
  etape: "confirmation_codes",
  codes_secours: ["ABCD-EFGH-JKMN"],
  nom_affiche: "Mme Durand",
  role: "associe",
};
const MOT_DE_PASSE = "le chat dort sur le toit";

function reponse(statut: number, corps: unknown): Response {
  return new Response(JSON.stringify(corps), { status: statut, headers: { "Content-Type": "application/json" } });
}

function refus(statut: number, code: string, message: string, champ?: string): Response {
  const details = champ ? { champs: [{ champ, message }] } : {};
  return reponse(statut, { code, message, details, trace_id: "t" });
}

// fetch simulé : réponse de activation/debut, puis celles de activation/fin dans l'ordre donné
function api(...fins: Response[]) {
  const appel = vi.fn((chemin: string) =>
    Promise.resolve(chemin.endsWith("/debut") ? reponse(200, DEBUT) : (fins.shift() ?? reponse(500, {}))),
  );
  vi.stubGlobal("fetch", appel);
  return appel;
}

const etape = (n: 0 | 1 | 2) => screen.findByRole("heading", { level: 2, name: TEXTES.activation.etapes[n] });
const continuer = () => userEvent.click(screen.getByRole("button", { name: TEXTES.activation.continuer }));

const champConfirmation = () => screen.getByLabelText(TEXTES.motDePasse.confirmation);

async function saisirMotsDePasse(motDePasse: string, confirmation: string) {
  await userEvent.type(screen.getByLabelText(TEXTES.activation.motDePasse), motDePasse);
  if (confirmation) await userEvent.type(champConfirmation(), confirmation);
}

async function jusquALEtape3(surActivation = vi.fn()) {
  render(<FormulaireActivation surActivation={surActivation} />);
  await etape(0);
  await continuer();
  await etape(1);
  await saisirMotsDePasse(MOT_DE_PASSE, MOT_DE_PASSE);
  await continuer();
  await etape(2);
  return surActivation;
}

async function activer(code = "123456") {
  await userEvent.type(screen.getByLabelText(TEXTES.activation.libelleCode), code);
  await userEvent.click(screen.getByRole("button", { name: TEXTES.activation.bouton }));
}

beforeEach(() => window.history.replaceState(null, "", `/activation#${JETON}`));
afterEach(() => vi.unstubAllGlobals());

describe("Activer mon compte : chargement du lien (ADR 0006, maquettes v3 écran 3)", () => {
  it("jeton lu après #, envoyé en POST à activation/debut ; il reste dans l'adresse pendant l'activation", async () => {
    const appel = api();
    render(<FormulaireActivation surActivation={vi.fn()} />);
    await etape(0);
    expect(window.location.hash).toBe(`#${JETON}`);
    expect(appel.mock.calls[0]![0]).toBe("/api/identity/auth/activation/debut");
    expect(JSON.parse((appel.mock.calls[0] as unknown as [string, RequestInit])[1].body as string)).toEqual({
      jeton: JETON,
    });
  });

  it("pendant le chargement : titre et squelette, aucun champ (UX-30)", () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => undefined)));
    const { container } = render(<FormulaireActivation surActivation={vi.fn()} />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(TEXTES.activation.titre);
    expect(container.querySelector("[aria-busy='true']")).not.toBeNull();
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("lien expiré, utilisé ou inconnu (410) : seulement le titre et le message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(refus(410, "lien_invalide", libelle("invitation.lien_invalide"))));
    render(<FormulaireActivation surActivation={vi.fn()} />);
    expect(await screen.findByText(libelle("invitation.lien_invalide"))).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(TEXTES.activation.titre);
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByText(TEXTES.activation.avantDeCommencer)).toBeNull();
  });

  it("adresse sans jeton : invitation à ouvrir le lien de l'e-mail, aucun appel, pas de « lien invalide »", async () => {
    window.history.replaceState(null, "", "/activation");
    const appel = vi.fn();
    vi.stubGlobal("fetch", appel);
    render(<FormulaireActivation surActivation={vi.fn()} />);
    expect(await screen.findByText(TEXTES.activation.sansLien)).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(TEXTES.activation.titre);
    expect(screen.queryByText(libelle("invitation.lien_invalide"))).toBeNull();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(appel).not.toHaveBeenCalled();
  });

  it("panne : bandeau « Erreur » avec le message de commun", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<FormulaireActivation surActivation={vi.fn()} />);
    const bandeau = await screen.findByRole("alert");
    expect(bandeau).toHaveTextContent(TEXTES.etats.erreur);
    expect(bandeau).toHaveTextContent(TEXTES.commun.erreurInattendue);
  });
});

describe("Activer mon compte : en-tête commun aux trois étapes", () => {
  it("bloc « Avant de commencer », autres applications dépliables, adresse de connexion", async () => {
    api();
    render(<FormulaireActivation surActivation={vi.fn()} />);
    await etape(0);
    expect(screen.getByText(TEXTES.activation.avantDeCommencer)).toBeInTheDocument();
    const autres = screen.getByText(TEXTES.activation.autresApplications);
    expect(autres.tagName).toBe("SUMMARY");
    for (const nom of TEXTES.activation.autresApplicationsListe) expect(screen.getByText(nom)).toBeInTheDocument();
    expect(screen.getByText(`${TEXTES.activation.adresseDeConnexion} ${DEBUT.email}`)).toBeInTheDocument();
  });

  it("l'en-tête reste aux étapes 2 et 3", async () => {
    api();
    await jusquALEtape3();
    expect(screen.getByText(TEXTES.activation.avantDeCommencer)).toBeInTheDocument();
    expect(screen.getByText(`${TEXTES.activation.adresseDeConnexion} ${DEBUT.email}`)).toBeInTheDocument();
  });
});

describe("Activer mon compte : étape 1, votre nom", () => {
  it("nom affiché pré-rempli et modifiable, aide liée, un seul bouton « Continuer »", async () => {
    api();
    render(<FormulaireActivation surActivation={vi.fn()} />);
    await etape(0);
    const nom = screen.getByLabelText(TEXTES.activation.nomAffiche);
    expect(nom).toHaveValue("Mme Durand");
    expect(nom).toHaveAccessibleDescription(TEXTES.activation.aideNom);
    expect(screen.getAllByRole("button").filter((b) => b.getAttribute("type") === "submit")).toHaveLength(1);
    expect(screen.queryByRole("button", { name: TEXTES.activation.etapePrecedente })).toBeNull();
  });

  it("nom refusé à la sortie du champ : message sous le champ (UX-19)", async () => {
    api();
    render(<FormulaireActivation surActivation={vi.fn()} />);
    await etape(0);
    const nom = screen.getByLabelText(TEXTES.activation.nomAffiche);
    await userEvent.clear(nom);
    await userEvent.type(nom, "marie@exemple.fr");
    await userEvent.tab();
    expect(nom).toHaveAccessibleDescription(`${TEXTES.activation.aideNom} ${libelle("nom_affiche.invalide")}`);
  });

  it("appui sur « Continuer » depuis le nom : aucun message à la sortie, la vérification se fait à l'envoi", async () => {
    api();
    render(<FormulaireActivation surActivation={vi.fn()} />);
    await etape(0);
    const nom = screen.getByLabelText(TEXTES.activation.nomAffiche);
    await userEvent.clear(nom);
    fireEvent.pointerDown(screen.getByRole("button", { name: TEXTES.activation.continuer }));
    fireEvent.blur(nom);
    expect(nom).not.toHaveAccessibleDescription(`${TEXTES.activation.aideNom} ${libelle("nom_affiche.invalide")}`);
  });

  it("« Continuer » avec un nom vide : on reste, message, focus sur le champ", async () => {
    api();
    render(<FormulaireActivation surActivation={vi.fn()} />);
    await etape(0);
    await userEvent.clear(screen.getByLabelText(TEXTES.activation.nomAffiche));
    await continuer();
    const nom = screen.getByLabelText(TEXTES.activation.nomAffiche);
    expect(nom).toHaveFocus();
    expect(nom).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(TEXTES.activation.etapes[0]);
  });

  it("« Continuer » : étape 2 annoncée, focus sur son titre", async () => {
    api();
    render(<FormulaireActivation surActivation={vi.fn()} />);
    await etape(0);
    await continuer();
    expect(await etape(1)).toHaveFocus();
  });
});

describe("Activer mon compte : étape 2, votre mot de passe", () => {
  async function jusquALEtape2() {
    api();
    render(<FormulaireActivation surActivation={vi.fn()} />);
    await etape(0);
    await continuer();
    await etape(1);
  }

  it("champ masqué par défaut, nouveau mot de passe, aide, identifiant pour le gestionnaire de mots de passe", async () => {
    await jusquALEtape2();
    const champ = screen.getByLabelText(TEXTES.activation.motDePasse);
    expect(champ).toHaveAttribute("type", "password");
    expect(champ).toHaveAttribute("autocomplete", "new-password");
    expect(champ).toHaveAccessibleDescription(TEXTES.activation.aideMotDePasse);
    expect(screen.getByRole("button", { name: TEXTES.motDePasse.afficherAccessible })).toBeInTheDocument();
    const identifiant = document.querySelector("input[autocomplete='username']");
    expect(identifiant).toHaveValue(DEBUT.email);
    expect(identifiant?.closest("form")).toBe(champ.closest("form"));
  });

  it("mot de passe trop court à la sortie du champ : message sous le champ", async () => {
    await jusquALEtape2();
    const champ = screen.getByLabelText(TEXTES.activation.motDePasse);
    await userEvent.type(champ, "le chat");
    await userEvent.tab();
    expect(champ).toHaveAccessibleDescription(`${TEXTES.activation.aideMotDePasse} ${messageMotDePasse("trop_court")}`);
  });

  it("« Continuer » avec un mot de passe trop court : on reste, focus sur le champ", async () => {
    await jusquALEtape2();
    await userEvent.type(screen.getByLabelText(TEXTES.activation.motDePasse), "le chat");
    await continuer();
    expect(screen.getByLabelText(TEXTES.activation.motDePasse)).toHaveFocus();
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(TEXTES.activation.etapes[1]);
  });

  it("confirmation : second champ masqué, nouveau mot de passe, son propre bouton « Afficher »", async () => {
    await jusquALEtape2();
    const confirmation = champConfirmation();
    expect(confirmation).toHaveAttribute("type", "password");
    expect(confirmation).toHaveAttribute("autocomplete", "new-password");
    expect(
      screen.getByRole("button", { name: TEXTES.motDePasse.afficherConfirmationAccessible }),
    ).toBeInTheDocument();
    // sous le premier champ, dans le même formulaire
    const motDePasse = screen.getByLabelText(TEXTES.activation.motDePasse);
    expect(motDePasse.compareDocumentPosition(confirmation) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(confirmation.closest("form")).toBe(motDePasse.closest("form"));
  });

  it("confirmation différente à la sortie du champ : message sous le second champ", async () => {
    await jusquALEtape2();
    await saisirMotsDePasse(MOT_DE_PASSE, "le chat dort sur le toi");
    await userEvent.tab();
    expect(champConfirmation()).toHaveAccessibleDescription(TEXTES.motDePasse.differents);
  });

  it.each([
    ["mot de passe", "le chat", ""],
    ["confirmation", "le chat dort sur le toit", "autre chose"],
  ])("appui (souris, doigt) sur « Continuer » depuis le champ %s : aucun message à la sortie (il déplacerait le bouton sous le pointeur), la vérification se fait à l'envoi", async (nom, motDePasse, confirmation) => {
    await jusquALEtape2();
    await saisirMotsDePasse(motDePasse, confirmation);
    const champ = nom === "confirmation" ? champConfirmation() : screen.getByLabelText(TEXTES.activation.motDePasse);
    expect(champ).toHaveFocus();
    fireEvent.pointerDown(screen.getByRole("button", { name: TEXTES.activation.continuer }));
    fireEvent.blur(champ);
    expect(document.querySelectorAll(".champ-erreur")).toHaveLength(0);
  });

  it("au clavier (Tab vers « Continuer ») : le message s'affiche bien à la sortie du champ", async () => {
    await jusquALEtape2();
    await saisirMotsDePasse(MOT_DE_PASSE, "autre chose");
    await userEvent.tab();
    await userEvent.tab();
    expect(champConfirmation()).toHaveAccessibleDescription(TEXTES.motDePasse.differents);
  });

  it("confirmation vide à la sortie du champ : aucun message (on ne gronde pas avant la saisie)", async () => {
    await jusquALEtape2();
    await userEvent.click(champConfirmation());
    await userEvent.tab();
    expect(champConfirmation()).not.toHaveAccessibleDescription(TEXTES.motDePasse.differents);
  });

  it.each([
    ["différente", "le chat dort sur le toi"],
    ["vide", ""],
  ])("« Continuer » avec une confirmation %s : on reste à l'étape 2, message, curseur dans le second champ", async (_, confirmation) => {
    await jusquALEtape2();
    await saisirMotsDePasse(MOT_DE_PASSE, confirmation);
    await continuer();
    expect(champConfirmation()).toHaveFocus();
    expect(champConfirmation()).toHaveAttribute("aria-invalid", "true");
    expect(champConfirmation()).toHaveAccessibleDescription(TEXTES.motDePasse.differents);
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(TEXTES.activation.etapes[1]);
  });

  it("premier champ trop court : son message d'abord, même si la confirmation diffère", async () => {
    await jusquALEtape2();
    await saisirMotsDePasse("le chat", "autre chose");
    await continuer();
    expect(screen.getByLabelText(TEXTES.activation.motDePasse)).toHaveFocus();
    expect(champConfirmation()).not.toHaveAccessibleDescription(TEXTES.motDePasse.differents);
  });

  it("« Étape précédente » : retour à l'étape 1, le nom saisi est gardé", async () => {
    api();
    render(<FormulaireActivation surActivation={vi.fn()} />);
    await etape(0);
    const nom = screen.getByLabelText(TEXTES.activation.nomAffiche);
    await userEvent.clear(nom);
    await userEvent.type(nom, "Marie Durand");
    await continuer();
    await etape(1);
    await userEvent.click(screen.getByRole("button", { name: TEXTES.activation.etapePrecedente }));
    expect(await etape(0)).toHaveFocus();
    expect(screen.getByLabelText(TEXTES.activation.nomAffiche)).toHaveValue("Marie Durand");
  });
});

describe("Activer mon compte : étape 3, votre application d'authentification", () => {
  it("consigne, lien vers l'application, QR code avec texte de remplacement, clé par groupes de 4", async () => {
    api();
    await jusquALEtape3();
    expect(screen.getByText(TEXTES.activation.consigneApplication)).toBeInTheDocument();
    expect(screen.getByText(TEXTES.activation.consigneTelephone)).toBeInTheDocument();
    expect(screen.getByText(TEXTES.activation.consigneOrdinateur)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: TEXTES.activation.ajouter })).toHaveAttribute("href", URI);
    expect(screen.getByText(TEXTES.activation.rienNeSouvre)).toBeInTheDocument();
    const qr = await screen.findByRole("img", { name: TEXTES.activation.altQr });
    expect(qr.getAttribute("src")).toMatch(/^data:image\/svg\+xml/);
    expect(screen.getByText(TEXTES.activation.cleManuelle)).toBeInTheDocument();
    expect(screen.getByLabelText("JBSW Y3DP EHPK 3PXP JBSW Y3DP")).toHaveTextContent("JBSW Y3DP EHPK 3PXP JBSW Y3DP");
  });

  it("« Copier la clé » : clé sans espaces dans le presse-papiers, « Clé copiée. » annoncé", async () => {
    api();
    const user = userEvent.setup();
    await jusquALEtape3();
    const ecrire = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    await user.click(screen.getByRole("button", { name: TEXTES.activation.copierCle }));
    expect(ecrire).toHaveBeenCalledWith("JBSWY3DPEHPK3PXPJBSWY3DP");
    expect(await screen.findByRole("status")).toHaveTextContent(TEXTES.activation.cleCopiee);
  });

  it("champ du code : clavier numérique, remplissage du code ; bouton principal « Activer mon compte »", async () => {
    api();
    await jusquALEtape3();
    const code = screen.getByLabelText(TEXTES.activation.libelleCode);
    expect(code).toHaveAttribute("inputmode", "numeric");
    expect(code).toHaveAttribute("autocomplete", "one-time-code");
    const soumettre = screen.getAllByRole("button").filter((b) => b.getAttribute("type") === "submit");
    expect(soumettre).toHaveLength(1);
    expect(soumettre[0]).toHaveTextContent(TEXTES.activation.bouton);
    expect(screen.getByRole("button", { name: TEXTES.activation.etapePrecedente })).toBeInTheDocument();
  });
});

describe("Activer mon compte : envoi final (activation/fin)", () => {
  it("réussite : jeton, nom, mot de passe et code envoyés ; les codes de secours passent à l'écran suivant", async () => {
    const appel = api(reponse(200, ACTIVE));
    const surActivation = await jusquALEtape3();
    await activer();
    await waitFor(() => expect(surActivation).toHaveBeenCalledWith(ACTIVE));
    // le jeton ne quitte l'adresse qu'une fois le compte activé
    expect(window.location.hash).toBe("");
    expect(window.location.pathname).toBe("/activation");
    const [chemin, options] = appel.mock.calls[1] as unknown as [string, RequestInit];
    expect(chemin).toBe("/api/identity/auth/activation/fin");
    expect(JSON.parse(options.body as string)).toEqual({
      jeton: JETON,
      nom_affiche: "Mme Durand",
      mot_de_passe: MOT_DE_PASSE,
      code: "123456",
    });
  });

  it("code faux (400) : on reste à l'étape 3, message sous le champ, champ vidé, focus", async () => {
    const message = libelle("activation.code_incorrect");
    api(refus(400, "code_incorrect", message, "code"));
    const surActivation = await jusquALEtape3();
    await activer("000000");
    const code = screen.getByLabelText(TEXTES.activation.libelleCode);
    await waitFor(() => expect(code).toHaveAccessibleDescription(message));
    expect(code).toHaveValue("");
    expect(code).toHaveFocus();
    expect(surActivation).not.toHaveBeenCalled();
    expect(window.location.hash).toBe(`#${JETON}`);
  });

  it("nom refusé (422) : retour à l'étape 1, message sous le champ, focus", async () => {
    const message = libelle("nom_affiche.invalide");
    // format de commun : message général, et message du champ dans details.champs
    api(
      reponse(422, {
        code: "invalid",
        message: "Certaines informations sont incorrectes. Corrigez les champs signalés.",
        details: { champs: [{ champ: "nom_affiche", message }] },
      }),
    );
    await jusquALEtape3();
    await activer();
    await etape(0);
    const nom = screen.getByLabelText(TEXTES.activation.nomAffiche);
    expect(nom).toHaveAccessibleDescription(`${TEXTES.activation.aideNom} ${message}`);
    expect(nom).toHaveFocus();
  });

  it("mot de passe refusé (422) : retour à l'étape 2, les deux champs vidés, message du motif, focus", async () => {
    const message = messageMotDePasse("courant");
    api(refus(422, "mot_de_passe_refuse", message, "mot_de_passe"));
    await jusquALEtape3();
    await activer();
    await etape(1);
    const champ = screen.getByLabelText(TEXTES.activation.motDePasse);
    expect(champ).toHaveAccessibleDescription(`${TEXTES.activation.aideMotDePasse} ${message}`);
    expect(champ).toHaveFocus();
    expect(champ).toHaveValue("");
    expect(champConfirmation()).toHaveValue("");
  });

  it("lien devenu invalide (410) : seulement le titre et le message", async () => {
    api(refus(410, "lien_invalide", libelle("invitation.lien_invalide")));
    await jusquALEtape3();
    await activer();
    expect(await screen.findByText(libelle("invitation.lien_invalide"))).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("trop de demandes (429) : bandeau « Attention », on reste à l'étape 3", async () => {
    const message = "Trop de demandes en peu de temps. Patientez une minute, puis réessayez.";
    api(refus(429, "trop_de_requetes", message));
    await jusquALEtape3();
    await activer();
    const bandeau = await screen.findByRole("alert");
    expect(bandeau).toHaveTextContent(TEXTES.etats.attention);
    expect(bandeau).toHaveTextContent(message);
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(TEXTES.activation.etapes[2]);
  });

  it("pendant l'envoi : bouton désactivé, « Envoi en cours… » (UX-22)", async () => {
    let terminer: (r: Response) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((chemin: string) =>
        chemin.endsWith("/debut")
          ? Promise.resolve(reponse(200, DEBUT))
          : new Promise<Response>((r) => (terminer = r)),
      ),
    );
    const surActivation = await jusquALEtape3();
    await activer();
    expect(screen.getByRole("button", { name: TEXTES.envoiEnCours })).toBeDisabled();
    terminer(reponse(200, ACTIVE));
    await waitFor(() => expect(surActivation).toHaveBeenCalled());
  });
});

describe("Activer mon compte : page", () => {
  it("titre de l'onglet « Activer mon compte — LePalier »", () => {
    expect(metadata.title).toBe("Activer mon compte — LePalier");
  });
});
