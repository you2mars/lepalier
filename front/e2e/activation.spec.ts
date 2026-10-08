// Écran Activer mon compte (maquettes v3, écran 3) : R0-05, R0-20, R0-23 ; politique de sécurité vérifiée par
// aides.ts. Une invitation par projet : les deux premiers essais ne la consomment pas, le dernier l'active.
import type { Page } from "@playwright/test";
import { libelle, messageMotDePasse } from "../src/lib/libelles";
import { TEXTES } from "../src/textes";
import { base32EnHex, codeFaux, codeTotp, expect, jetonInvitation, test, verifierAccessibilite } from "./aides";

const T = TEXTES.activation;
const MOT_DE_PASSE = "le chat dort sur le toit rouge";

async function ouvrirLeLien(page: Page, jeton: string): Promise<void> {
  // depuis une autre page : sinon le seul changement de « # » ne recharge pas l'écran
  await page.goto("about:blank");
  await page.goto(`/activation#${jeton}`);
}

const titreEtape = (page: Page, n: 0 | 1 | 2) => page.getByRole("heading", { level: 2, name: T.etapes[n] });

async function continuer(page: Page): Promise<void> {
  await page.getByRole("button", { name: T.continuer }).click();
}

async function saisirMotsDePasse(page: Page, motDePasse: string, confirmation = motDePasse): Promise<void> {
  await page.getByLabel(T.motDePasse, { exact: true }).fill(motDePasse);
  await page.getByLabel(TEXTES.motDePasse.confirmation, { exact: true }).fill(confirmation);
}

async function cle(page: Page): Promise<string> {
  return (await page.locator(".cle code").textContent()) ?? "";
}

async function sansDefilementHorizontal(page: Page): Promise<void> {
  const largeurs = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  expect(largeurs[0]).toBeLessThanOrEqual(largeurs[1]!);
}

test.describe("Activer mon compte", () => {
  test("lien inconnu : le message du lien invalide et un chemin vers Se connecter (revue UX, B1)", async ({ page }) => {
    await ouvrirLeLien(page, "x".repeat(43));
    await expect(page.getByText(libelle("invitation.lien_invalide"))).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(T.titre);
    await expect(page.getByRole("textbox")).toHaveCount(0);
    await expect(page.getByText(T.dejaActive)).toBeVisible();
    await expect(page.getByRole("link", { name: TEXTES.connexion.titre })).toHaveAttribute("href", "/connexion");
    await verifierAccessibilite(page);
  });

  test("accès sans le lien de l'e-mail : invitation à l'ouvrir, jamais « lien invalide »", async ({ page }) => {
    await page.goto("/activation");
    await expect(page.getByText(T.sansLien)).toBeVisible();
    await expect(page.getByText(libelle("invitation.lien_invalide"))).toHaveCount(0);
    await expect(page.getByRole("textbox")).toHaveCount(0);
    await verifierAccessibilite(page);
  });

  test("trois étapes accessibles, cibles de 44 px, aucun défilement horizontal ; rechargement à l'étape 3 : même clé", async ({
    page,
    isMobile,
  }, infos) => {
    const jeton = jetonInvitation(infos.project.name);
    if (!isMobile) await page.setViewportSize({ width: 640, height: 600 });
    await ouvrirLeLien(page, jeton);
    await expect(page).toHaveTitle("Activer mon compte — LePalier");
    await expect(titreEtape(page, 0)).toBeVisible();
    expect(new URL(page.url()).hash).toBe(`#${jeton}`);
    await expect(page.getByText(T.avantDeCommencer)).toBeVisible();
    await expect(page.getByLabel(T.nomAffiche)).toHaveValue("M. Essai");
    await verifierAccessibilite(page);
    await sansDefilementHorizontal(page);

    await continuer(page);
    await expect(titreEtape(page, 1)).toBeFocused();
    // confirmation différente : message sous le second champ, on reste à l'étape 2
    await saisirMotsDePasse(page, MOT_DE_PASSE, "le chat dort sur le toit vert");
    await continuer(page);
    const confirmation = page.getByLabel(TEXTES.motDePasse.confirmation, { exact: true });
    await expect(confirmation).toHaveAccessibleDescription(TEXTES.motDePasse.differents);
    await expect(confirmation).toBeFocused();
    await verifierAccessibilite(page);
    await sansDefilementHorizontal(page);
    await saisirMotsDePasse(page, MOT_DE_PASSE);

    await continuer(page);
    await expect(titreEtape(page, 2)).toBeFocused();
    await expect(page.getByRole("img", { name: T.altQr })).toBeVisible();
    // revue UX (M2) : le lien qui ouvre l'application du téléphone n'apparaît que sur un écran tactile
    const ajouter = page.getByRole("link", { name: T.ajouter });
    if (isMobile) await expect(ajouter).toBeVisible();
    else await expect(ajouter).toBeHidden();
    await expect(page.getByLabel(T.libelleCode)).toHaveAttribute("inputmode", "numeric");
    await verifierAccessibilite(page);
    await sansDefilementHorizontal(page);
    for (const cible of await page.locator("input:not([hidden]), button, a.bouton, a.lien").filter({ visible: true }).all()) {
      const boite = await cible.boundingBox();
      expect(boite?.height ?? 0).toBeGreaterThanOrEqual(44);
    }
    const premiereCle = await cle(page);
    expect(premiereCle).toMatch(/^[A-Z2-7]{4}( [A-Z2-7]{1,4})+$/);

    // B1 : au retour de l'App Store, le téléphone recharge la page ; l'activation reprend sans erreur
    await page.reload();
    await expect(titreEtape(page, 0)).toBeVisible();
    await expect(page.getByText(libelle("invitation.lien_invalide"))).toHaveCount(0);
    await continuer(page);
    await saisirMotsDePasse(page, MOT_DE_PASSE);
    await continuer(page);
    expect(await cle(page)).toBe(premiereCle);
  });

  test("mot de passe refusé : retour à l'étape 2 ; code faux : message ; compte activé puis codes de secours (R0-05)", async ({
    page,
  }, infos) => {
    await ouvrirLeLien(page, jetonInvitation(infos.project.name));
    await page.getByLabel(T.nomAffiche).fill("M. Essai Activé");
    await continuer(page);
    await saisirMotsDePasse(page, "le palier du chat noir");
    await continuer(page);
    const secret = base32EnHex(await cle(page));
    await page.getByLabel(T.libelleCode).fill(codeTotp(secret));
    await page.getByRole("button", { name: T.bouton }).click();

    const motDePasse = page.getByLabel(T.motDePasse, { exact: true });
    await expect(titreEtape(page, 1)).toBeVisible();
    await expect(motDePasse).toHaveAccessibleDescription(`${T.aideMotDePasse} ${messageMotDePasse("nom_application")}`);
    await expect(motDePasse).toBeFocused();
    // les deux champs sont à retaper
    await expect(motDePasse).toHaveValue("");
    await expect(page.getByLabel(TEXTES.motDePasse.confirmation, { exact: true })).toHaveValue("");

    await saisirMotsDePasse(page, MOT_DE_PASSE);
    await continuer(page);
    const code = page.getByLabel(T.libelleCode);
    await code.fill(codeFaux(secret));
    await page.getByRole("button", { name: T.bouton }).click();
    await expect(code).toHaveAccessibleDescription(libelle("activation.code_incorrect"));
    await expect(code).toBeFocused();

    await code.fill(codeTotp(secret));
    await page.getByRole("button", { name: T.bouton }).click();
    // le lien ne quitte la barre d'adresse qu'une fois le compte activé
    await expect(page).toHaveURL(/\/activation\/codes$/);
    expect((await page.context().cookies()).map((c) => c.name)).toContain("lp_session");

    // écran 4 : codes de secours, une seule fois
    const C = TEXTES.codes;
    await expect(page).toHaveTitle("Vos codes de secours — LePalier");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(C.titre);
    await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
    await expect(page.getByRole("list", { name: C.titre }).getByRole("listitem")).toHaveCount(10);
    await verifierAccessibilite(page);
    await page.getByRole("button", { name: C.continuer }).click();
    const caseNotes = page.getByRole("checkbox", { name: C.caseNotes });
    await expect(caseNotes).toHaveAccessibleDescription(C.caseNonCochee);
    await expect(caseNotes).toBeFocused();
    await expect(page).toHaveURL(/\/activation\/codes$/);

    // case non cochée : le navigateur demande confirmation avant de recharger ; « Rester » garde les codes
    // rechargement différé : evaluate rend la main avant que la boîte de confirmation ne bloque la page
    const [confirmation] = await Promise.all([
      page.waitForEvent("dialog"),
      page.evaluate(() => {
        setTimeout(() => window.location.reload(), 0);
      }),
    ]);
    expect(confirmation.type()).toBe("beforeunload");
    await confirmation.dismiss();
    await expect(page.getByRole("list", { name: C.titre }).getByRole("listitem")).toHaveCount(10);

    // feuille imprimée : seule visible à l'impression
    await page.emulateMedia({ media: "print" });
    await expect(page.locator(".feuille-impression")).toBeVisible();
    await expect(page.locator(".feuille-impression")).toContainText("M. Essai Activé");
    await expect(page.locator(".feuille-impression")).toContainText(C.barrezApresUsage);
    await expect(page.locator(".feuille-impression")).toContainText(/Imprimé le \S+ \d+/);
    await expect(page.getByRole("heading", { level: 1 })).toBeHidden();
    await page.emulateMedia({ media: "screen" });

    await caseNotes.check();
    await page.getByRole("button", { name: C.continuer }).click();
    await expect(page).toHaveURL(/\/\?motif=compte_active$/);
    // accueil (écran 5) : bandeau « Fait » et la façon de se connecter la prochaine fois (N19)
    await expect(page.getByRole("status")).toContainText(TEXTES.accueil.compteActive);
  });

  test("/activation/codes rechargée : codes perdus, accueil avec le bandeau qui le dit (via Se connecter sans session)", async ({
    page,
  }) => {
    await page.goto("/activation/codes");
    // sans session dans cet essai : Se connecter, avec l'accueil et son bandeau comme page demandée
    await expect(page).toHaveURL(/\/connexion\?retour=%2F%3Fmotif%3Dcodes_perdus$/);
  });
});
