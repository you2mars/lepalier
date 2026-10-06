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

async function cle(page: Page): Promise<string> {
  return (await page.locator(".cle code").textContent()) ?? "";
}

async function sansDefilementHorizontal(page: Page): Promise<void> {
  const largeurs = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  expect(largeurs[0]).toBeLessThanOrEqual(largeurs[1]!);
}

test.describe("Activer mon compte", () => {
  test("lien inconnu : seulement le titre et le message, jeton retiré de l'adresse", async ({ page }) => {
    await ouvrirLeLien(page, "x".repeat(43));
    await expect(page.getByText(libelle("invitation.lien_invalide"))).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(T.titre);
    await expect(page.getByRole("textbox")).toHaveCount(0);
    expect(new URL(page.url()).hash).toBe("");
    await verifierAccessibilite(page);
  });

  test("trois étapes accessibles, cibles de 44 px, aucun défilement horizontal ; même clé à la réouverture du lien", async ({
    page,
    isMobile,
  }, infos) => {
    const jeton = jetonInvitation(infos.project.name);
    if (!isMobile) await page.setViewportSize({ width: 640, height: 600 });
    await ouvrirLeLien(page, jeton);
    await expect(page).toHaveTitle("Activer mon compte — LePalier");
    await expect(titreEtape(page, 0)).toBeVisible();
    expect(new URL(page.url()).hash).toBe("");
    await expect(page.getByText(T.avantDeCommencer)).toBeVisible();
    await expect(page.getByLabel(T.nomAffiche)).toHaveValue("M. Essai");
    await verifierAccessibilite(page);
    await sansDefilementHorizontal(page);

    await continuer(page);
    await expect(titreEtape(page, 1)).toBeFocused();
    await page.getByLabel(T.motDePasse, { exact: true }).fill(MOT_DE_PASSE);
    await verifierAccessibilite(page);

    await continuer(page);
    await expect(titreEtape(page, 2)).toBeFocused();
    await expect(page.getByRole("img", { name: T.altQr })).toBeVisible();
    await expect(page.getByLabel(T.libelleCode)).toHaveAttribute("inputmode", "numeric");
    await verifierAccessibilite(page);
    await sansDefilementHorizontal(page);
    for (const cible of await page.locator("input:not([hidden]), button, a.bouton").all()) {
      const boite = await cible.boundingBox();
      expect(boite?.height ?? 0).toBeGreaterThanOrEqual(44);
    }
    const premiereCle = await cle(page);
    expect(premiereCle).toMatch(/^[A-Z2-7]{4}( [A-Z2-7]{1,4})+$/);

    // B1 : la personne quitte la page pour installer l'application, puis rouvre le lien de l'e-mail
    await ouvrirLeLien(page, jeton);
    await continuer(page);
    await page.getByLabel(T.motDePasse, { exact: true }).fill(MOT_DE_PASSE);
    await continuer(page);
    expect(await cle(page)).toBe(premiereCle);
  });

  test("mot de passe refusé : retour à l'étape 2 ; code faux : message ; puis compte activé (R0-05)", async ({
    page,
  }, infos) => {
    await ouvrirLeLien(page, jetonInvitation(infos.project.name));
    await page.getByLabel(T.nomAffiche).fill("M. Essai Activé");
    await continuer(page);
    await page.getByLabel(T.motDePasse, { exact: true }).fill("le palier du chat noir");
    await continuer(page);
    const secret = base32EnHex(await cle(page));
    await page.getByLabel(T.libelleCode).fill(codeTotp(secret));
    await page.getByRole("button", { name: T.bouton }).click();

    const motDePasse = page.getByLabel(T.motDePasse, { exact: true });
    await expect(titreEtape(page, 1)).toBeVisible();
    await expect(motDePasse).toHaveAccessibleDescription(`${T.aideMotDePasse} ${messageMotDePasse("nom_application")}`);
    await expect(motDePasse).toBeFocused();

    await motDePasse.fill(MOT_DE_PASSE);
    await continuer(page);
    const code = page.getByLabel(T.libelleCode);
    await code.fill(codeFaux(secret));
    await page.getByRole("button", { name: T.bouton }).click();
    await expect(code).toHaveAccessibleDescription(libelle("activation.code_incorrect"));
    await expect(code).toBeFocused();

    await code.fill(codeTotp(secret));
    await page.getByRole("button", { name: T.bouton }).click();
    await expect(page.getByRole("heading", { level: 1, name: T.titre })).toHaveCount(0);
    expect((await page.context().cookies()).map((c) => c.name)).toContain("lp_session");
  });
});
