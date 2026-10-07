// Administration › Utilisateurs (maquettes v3, écran 6.1) et page réservée au gérant (écran 7) : R0-04, R0-06,
// R0-20 à R0-23 ; politique de sécurité vérifiée par aides.ts. Un gérant et un associé par projet.
import { TEXTES } from "../src/textes";
import { compteAdmin, expect, sansDefilementHorizontal, seConnecter, test, verifierAccessibilite } from "./aides";

const L = TEXTES.utilisateurs.liste;

test.describe("Administration › Utilisateurs", () => {
  test("gérant : depuis le menu, liste des utilisateurs, fil d'Ariane, accessibilité, 360 px et zoom 200 % (R0-04)", async ({
    page,
    isMobile,
  }, infos) => {
    const compte = compteAdmin("gerant", infos.project.name);
    await seConnecter(page, compte.email, compte.secret);
    await page.getByRole("navigation", { name: TEXTES.cadre.menuPrincipal }).getByRole("link", { name: TEXTES.cadre.administration }).click();
    await expect(page).toHaveURL(/\/administration\/utilisateurs$/);
    await expect(page).toHaveTitle("Utilisateurs — LePalier");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(L.titre);
    await expect(page.getByRole("navigation", { name: TEXTES.cadre.filAriane })).toContainText(TEXTES.cadre.administration);
    await expect(page.getByRole("link", { name: L.inviter })).toBeVisible();
    const nom = `${L.gererAcces} ${L.gererAccesDe} ${compte.nom}`;
    if (isMobile) {
      // une carte par personne, toute la carte est le lien
      await expect(page.getByRole("table")).toBeHidden();
      await expect(page.getByRole("link", { name: nom })).toBeVisible();
    } else {
      const tableau = page.getByRole("table", { name: L.titre });
      await expect(tableau.getByRole("row").filter({ hasText: compte.email })).toContainText(TEXTES.roles.gerant);
      await expect(tableau.getByRole("link", { name: nom })).toBeVisible();
    }
    await verifierAccessibilite(page);
    await sansDefilementHorizontal(page);
    if (!isMobile) {
      await page.setViewportSize({ width: 640, height: 400 });
      await expect(page.getByRole("link", { name: nom })).toBeVisible();
      await sansDefilementHorizontal(page);
    }
  });

  test("associé : pas d'« Administration » au menu ; l'adresse ouverte quand même donne la page réservée (R0-06)", async ({
    page,
  }, infos) => {
    const compte = compteAdmin("associe", infos.project.name);
    await seConnecter(page, compte.email, compte.secret);
    const menu = page.getByRole("navigation", { name: TEXTES.cadre.menuPrincipal });
    await expect(menu.getByRole("link", { name: TEXTES.cadre.administration })).toHaveCount(0);
    await page.goto("/administration/utilisateurs");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(TEXTES.reservee.titre);
    await expect(page.getByText(TEXTES.reservee.reservee)).toBeVisible();
    await expect(page.getByRole("table")).toHaveCount(0);
    await verifierAccessibilite(page);
    await page.getByRole("link", { name: TEXTES.retourAccueil }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(TEXTES.accueil.titre);
  });
});
