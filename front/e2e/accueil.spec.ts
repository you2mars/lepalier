// Accueil « À faire » et cadre des écrans connectés (maquettes v3, écran 5 et § 0.2) : R0-03, R0-08, R0-20 à
// R0-23 ; politique de sécurité vérifiée par aides.ts. Un gérant par projet (anti-rejeu TOTP).
import { TEXTES } from "../src/textes";
import { compteAccueil, contenu, expect, sansDefilementHorizontal, seConnecter, test, verifierAccessibilite } from "./aides";

test.describe("Accueil « À faire »", () => {
  test("sans session : Se connecter, sans message, page demandée gardée", async ({ page }) => {
    await page.goto("/?motif=compte_active");
    await expect(page).toHaveURL(/\/connexion\?retour=%2F%3Fmotif%3Dcompte_active$/);
    await expect(page.locator(".bandeau")).toHaveCount(0);
  });

  test("session expirée ou inconnue : Se connecter avec le bandeau « Attention » (§ 0.3)", async ({ page }) => {
    const adresse = new URL(process.env.LEPALIER_E2E_URL ?? "https://localhost");
    await page.context().addCookies([
      { name: "lp_session", value: "inconnu", domain: adresse.hostname, path: "/", secure: true, httpOnly: true },
    ]);
    await page.goto("/");
    await expect(page).toHaveURL(/\/connexion\?motif=session_expiree$/);
    // .bandeau : getByRole("alert") trouverait aussi l'annonceur de navigation de Next (next-route-announcer)
    await expect(page.locator(".bandeau")).toContainText(TEXTES.commun.sessionExpiree);
  });

  test("après la connexion : nom, rôle, menu, état vide, accessibilité ; déconnexion sans retour possible (R0-03, R0-08)", async ({
    page,
    isMobile,
  }, infos) => {
    const compte = compteAccueil(infos.project.name);
    await seConnecter(page, compte.email, compte.secret);
    await expect(page).toHaveURL(/\/$/);
    await expect(page).toHaveTitle("À faire — LePalier");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(TEXTES.accueil.titre);
    await expect(page.getByText(`M. Essai · ${TEXTES.cadre.role} ${TEXTES.roles.gerant}`)).toBeVisible();
    await expect(contenu(page).getByText(TEXTES.accueil.videGestion)).toBeVisible();
    const menu = page.getByRole("navigation");
    await expect(menu.getByRole("link", { name: TEXTES.cadre.aFaire })).toHaveAttribute("aria-current", "page");
    await expect(menu.getByRole("link", { name: TEXTES.cadre.administration })).toBeVisible();
    await verifierAccessibilite(page);
    await sansDefilementHorizontal(page);
    for (const cible of await page.locator("button, nav a, a.lien").filter({ visible: true }).all()) {
      const boite = await cible.boundingBox();
      expect(boite?.height ?? 0).toBeGreaterThanOrEqual(44);
    }

    if (isMobile) {
      // menu en bas de l'écran sur mobile
      const boite = await menu.boundingBox();
      expect((boite?.y ?? 0) + (boite?.height ?? 0)).toBeGreaterThan(600);
    } else {
      // « Aller au contenu » : premier élément atteint au clavier
      await page.keyboard.press("Tab");
      await expect(page.getByRole("link", { name: TEXTES.allerAuContenu })).toBeFocused();
      await expect(page.getByRole("link", { name: TEXTES.allerAuContenu })).toBeInViewport();
      // zoom 200 % sur un écran de 1 280 px : menu en bas, aucun défilement horizontal
      await page.setViewportSize({ width: 640, height: 400 });
      await sansDefilementHorizontal(page);
    }

    await page.getByRole("button", { name: TEXTES.cadre.seDeconnecter }).click();
    await expect(page).toHaveURL(/\/connexion\?motif=deconnexion$/);
    await expect(page.getByRole("status")).toContainText(TEXTES.connexion.deconnexionEffectuee);
    expect((await page.context().cookies()).map((c) => c.name)).not.toContain("lp_session");
    // « Précédent » : aucune page connectée ne s'affiche
    await page.goBack();
    await expect(page.getByRole("heading", { level: 1 })).not.toHaveText(TEXTES.accueil.titre);
    await expect(contenu(page).getByText(TEXTES.accueil.videGestion)).toHaveCount(0);
  });
});
