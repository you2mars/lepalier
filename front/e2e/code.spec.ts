// Écran Code de vérification (maquettes v3, écran 2) : R0-02, R0-14, R0-20 à R0-23 ; politique de sécurité
// vérifiée par aides.ts. Un compte par projet : un seul code TOTP accepté par compte et par passage.
import type { Page } from "@playwright/test";
import { libelle } from "../src/lib/libelles";
import { TEXTES } from "../src/textes";
import { codeFaux, codeTotp, compteCode, expect, test, verifierAccessibilite } from "./aides";

const MOT_DE_PASSE = process.env.LEPALIER_E2E_MOT_DE_PASSE ?? "";

async function jusquAuCode(page: Page, email: string, retour?: string): Promise<void> {
  await page.goto(retour ? `/connexion?retour=${encodeURIComponent(retour)}` : "/connexion");
  await page.getByLabel(TEXTES.connexion.adresse).fill(email);
  await page.getByLabel(TEXTES.connexion.motDePasse, { exact: true }).fill(MOT_DE_PASSE);
  await page.getByRole("button", { name: TEXTES.connexion.bouton }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(TEXTES.code.titre);
}

async function cookies(page: Page): Promise<string[]> {
  return (await page.context().cookies()).map((c) => c.name);
}

test.describe("Code de vérification", () => {
  test("sans pré-session : retour à Se connecter, sans message, page demandée gardée", async ({ page }) => {
    await page.goto("/connexion/code?retour=%2Fadministration%2Futilisateurs");
    await expect(page).toHaveURL(/\/connexion\?retour=%2Fadministration%2Futilisateurs$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(TEXTES.connexion.titre);
    // aucun bandeau ; getByRole("alert") trouverait aussi l'annonceur de navigation de Next (next-route-announcer)
    await expect(page.locator(".bandeau")).toHaveCount(0);
  });

  test("titre, champ au clavier numérique, accessibilité des deux modes, clavier, cibles, zoom (R0-02, R0-20 à R0-23)", async ({
    page,
    isMobile,
  }, infos) => {
    await jusquAuCode(page, compteCode(infos.project.name).email);
    await expect(page).toHaveTitle("Code de vérification — LePalier");
    const code = page.getByLabel(TEXTES.code.libelle);
    await expect(code).toHaveAttribute("inputmode", "numeric");
    await expect(code).toHaveAttribute("autocomplete", "one-time-code");
    await expect(page.getByRole("button", { name: TEXTES.connexion.bouton })).toHaveCount(1);
    await verifierAccessibilite(page);
    for (const cible of await page.locator("input, button, a.lien").filter({ visible: true }).all()) {
      const boite = await cible.boundingBox();
      expect(boite?.height ?? 0).toBeGreaterThanOrEqual(44);
    }
    if (!isMobile) {
      // clavier seul : code, code de secours, Se connecter, Recommencer la connexion
      await code.focus();
      const ordre: (string | null)[] = [];
      for (let i = 0; i < 3; i++) {
        await page.keyboard.press("Tab");
        ordre.push(await page.evaluate(() => document.activeElement?.textContent ?? null));
      }
      expect(ordre).toEqual([TEXTES.code.utiliserSecours, TEXTES.connexion.bouton, TEXTES.code.recommencer]);
      // zoom 200 % sur un écran de 1 280 px
      await page.setViewportSize({ width: 640, height: 400 });
    }
    const largeurs = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
    expect(largeurs[0]).toBeLessThanOrEqual(largeurs[1]!);
    await page.getByRole("button", { name: TEXTES.code.utiliserSecours }).click();
    await expect(page.getByLabel(TEXTES.code.libelleSecours)).toBeFocused();
    await verifierAccessibilite(page);
  });

  test("code faux : message sous le champ, champ vidé, focus ; puis code de secours en minuscules : connecté (R0-14)", async ({
    page,
  }, infos) => {
    const compte = compteCode(infos.project.name);
    await jusquAuCode(page, compte.email);
    const code = page.getByLabel(TEXTES.code.libelle);
    await code.fill(codeFaux(compte.secret));
    await page.getByRole("button", { name: TEXTES.connexion.bouton }).click();
    await expect(code).toHaveAccessibleDescription(`${TEXTES.code.aide} ${libelle("code.incorrect")}`);
    await expect(code).toHaveValue("");
    await expect(code).toBeFocused();
    await verifierAccessibilite(page);
    await page.getByRole("button", { name: TEXTES.code.utiliserSecours }).click();
    await page.getByLabel(TEXTES.code.libelleSecours).fill(compte.secours[0]!.toLowerCase().replaceAll("-", " "));
    await page.getByRole("button", { name: TEXTES.connexion.bouton }).click();
    await expect(page).toHaveURL(/\/$/);
    expect(await cookies(page)).toContain("lp_session");
    expect(await cookies(page)).not.toContain("lp_pre");
  });

  test("code juste : connecté, retour à la page demandée (R0-02, § 0.3)", async ({ page }, infos) => {
    const compte = compteCode(infos.project.name);
    await jusquAuCode(page, compte.email, "/administration/utilisateurs");
    await page.getByLabel(TEXTES.code.libelle).fill(codeTotp(compte.secret));
    await page.getByRole("button", { name: TEXTES.connexion.bouton }).click();
    await expect(page).toHaveURL(/\/administration\/utilisateurs$/);
    expect(await cookies(page)).toContain("lp_session");
  });
});
