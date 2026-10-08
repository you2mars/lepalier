// Écran Se connecter (maquettes v3, écran 1) : R0-01, R0-20 à R0-24 ; politique de sécurité vérifiée par aides.ts.
import { libelle } from "../src/lib/libelles";
import { TEXTES } from "../src/textes";
import { COMPTE, expect, test, verifierAccessibilite } from "./aides";

test.describe("Se connecter", () => {
  test("titre, un seul bouton principal, accessibilité (R0-01, R0-22)", async ({ page }) => {
    await page.goto("/connexion");
    await expect(page).toHaveTitle("Se connecter — LePalier");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(TEXTES.connexion.titre);
    await expect(page.getByRole("button", { name: TEXTES.connexion.bouton })).toHaveCount(1);
    await expect(page.getByLabel(TEXTES.connexion.adresse)).toBeVisible();
    await verifierAccessibilite(page);
  });

  test("politique de sécurité avec le nonce de nginx sur chaque script", async ({ page }) => {
    const reponse = await page.goto("/connexion");
    const csp = (await reponse?.headerValue("content-security-policy")) ?? "";
    const nonce = /'nonce-([^']+)'/.exec(csp)?.[1];
    expect(nonce).toMatch(/^[0-9a-f]{32}$/);
    const scripts = await page.locator("script").evaluateAll((elements) =>
      elements.map((e) => (e as HTMLScriptElement).nonce),
    );
    expect(scripts.length).toBeGreaterThan(0);
    expect(scripts.every((n) => n === nonce)).toBe(true);
  });

  test("mot de passe faux : message sous le champ, champ vidé, focus (R0-24)", async ({ page }) => {
    await page.goto("/connexion");
    await page.getByLabel(TEXTES.connexion.adresse).fill(COMPTE.email);
    await page.getByLabel(TEXTES.connexion.motDePasse, { exact: true }).fill("un autre mot de passe faux");
    await page.getByRole("button", { name: TEXTES.connexion.bouton }).click();
    const motDePasse = page.getByLabel(TEXTES.connexion.motDePasse, { exact: true });
    await expect(motDePasse).toHaveAccessibleDescription(libelle("connexion.identifiants_incorrects"));
    await expect(motDePasse).toHaveValue("");
    await expect(motDePasse).toBeFocused();
    await verifierAccessibilite(page);
  });

  test("bonnes informations : écran du code, page demandée transmise (R0-02)", async ({ page }) => {
    await page.goto("/connexion?retour=%2Fadministration%2Futilisateurs");
    await page.getByLabel(TEXTES.connexion.adresse).fill(COMPTE.email);
    await page.getByLabel(TEXTES.connexion.motDePasse, { exact: true }).fill(COMPTE.motDePasse);
    await page.getByRole("button", { name: TEXTES.connexion.bouton }).click();
    await expect(page).toHaveURL(/\/connexion\/code\?retour=%2Fadministration%2Futilisateurs$/);
  });

  test("bandeau d'arrivée après une déconnexion", async ({ page }) => {
    await page.goto("/connexion?motif=deconnexion");
    await expect(page.getByRole("status")).toContainText(TEXTES.connexion.deconnexionEffectuee);
  });

  test("clavier seul : adresse, mot de passe, Afficher, Se connecter, lien (R0-21)", async ({ page, isMobile }) => {
    test.skip(isMobile, "parcours au clavier : ordinateur");
    await page.goto("/connexion");
    await page.getByLabel(TEXTES.connexion.adresse).focus();
    const ordre: (string | null)[] = [];
    for (let i = 0; i < 4; i++) {
      await page.keyboard.press("Tab");
      ordre.push(await page.evaluate(() => document.activeElement?.getAttribute("aria-label") ?? document.activeElement?.textContent ?? null));
    }
    expect(ordre).toEqual([
      "",
      TEXTES.motDePasse.afficherAccessible,
      TEXTES.connexion.bouton,
      TEXTES.connexion.oublie,
    ]);
  });

  test("cibles d'au moins 44 px et aucun défilement horizontal (UX-8, R0-20, R0-23)", async ({ page }) => {
    await page.goto("/connexion");
    for (const cible of await page.locator("input, button, a.lien").filter({ visible: true }).all()) {
      const boite = await cible.boundingBox();
      expect(boite?.height ?? 0).toBeGreaterThanOrEqual(44);
    }
    const largeurs = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
    expect(largeurs[0]).toBeLessThanOrEqual(largeurs[1]!);
  });

  test("zoom 200 % sur un écran de 1 280 px : aucun défilement horizontal (R0-23)", async ({ page, isMobile }) => {
    test.skip(isMobile, "zoom : ordinateur");
    await page.setViewportSize({ width: 640, height: 400 });
    await page.goto("/connexion");
    const largeurs = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
    expect(largeurs[0]).toBeLessThanOrEqual(largeurs[1]!);
  });
});

test.describe("Page introuvable", () => {
  test("404, message de commun, accessibilité, aucune violation de la politique de sécurité", async ({ page }) => {
    const reponse = await page.goto("/cette-page-n-existe-pas");
    expect(reponse?.status()).toBe(404);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(TEXTES.commun.introuvable);
    await verifierAccessibilite(page);
  });
});
