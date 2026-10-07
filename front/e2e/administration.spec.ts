// Administration › Utilisateurs (maquettes v3, écran 6.1) et page réservée au gérant (écran 7) : R0-04, R0-06,
// R0-20 à R0-23 ; politique de sécurité vérifiée par aides.ts. Un gérant et un associé par projet.
import { libelle } from "../src/lib/libelles";
import { TEXTES } from "../src/textes";
import { compteAdmin, expect, sansDefilementHorizontal, test, verifierAccessibilite } from "./aides";

const L = TEXTES.utilisateurs.liste;
const I = TEXTES.utilisateurs.inviter;

test.describe("Administration › Utilisateurs, gérant", () => {
  test.use({ sessionAdmin: "gerant" });

  test("gérant : depuis le menu, liste des utilisateurs, fil d'Ariane, accessibilité, 360 px et zoom 200 % (R0-04)", async ({
    page,
    isMobile,
  }, infos) => {
    const compte = compteAdmin("gerant", infos.project.name);
    await page.goto("/");
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

  test("inviter : confirmation récapitulative (Échap, « Modifier »), envoi, bandeau et nouvelle ligne ; adresse déjà utilisée (R0-04)", async ({
    page,
  }, infos) => {
    await page.goto("/administration/utilisateurs");
    await page.getByRole("link", { name: L.inviter }).click();
    await expect(page).toHaveTitle("Inviter une personne — LePalier");
    const nom = `Mme Invitée ${infos.project.name}`;
    const adresse = `invitee-${infos.project.name}@essai.local`;
    await page.getByLabel(I.nomAffiche).fill(nom);
    await page.getByLabel(I.adresse).fill(adresse);
    await page.getByRole("radio", { name: `${TEXTES.roles.operateur} — ${TEXTES.descriptionsRoles.operateur}.` }).check();
    await verifierAccessibilite(page);
    await sansDefilementHorizontal(page);

    const envoyer = page.getByRole("button", { name: I.envoyer });
    await envoyer.click();
    const boite = page.getByRole("dialog", { name: `Envoyer l'invitation à ${nom} ?` });
    await expect(boite).toContainText(`Adresse : ${adresse}`);
    await expect(boite).toContainText(`Rôle : Opérateur — ${TEXTES.descriptionsRoles.operateur}.`);
    await expect(boite).toContainText(I.confirmation.validite);
    await expect(boite.getByRole("button", { name: I.confirmation.modifier })).toBeFocused();
    await verifierAccessibilite(page);
    // Échap : boîte fermée, focus rendu au bouton qui l'a ouverte, rien d'envoyé
    await page.keyboard.press("Escape");
    await expect(boite).toBeHidden();
    await expect(envoyer).toBeFocused();
    await envoyer.click();
    await boite.getByRole("button", { name: I.confirmation.modifier }).click();
    await expect(boite).toBeHidden();
    await envoyer.click();
    await boite.getByRole("button", { name: I.envoyer }).click();

    await expect(page).toHaveURL(/\/administration\/utilisateurs\?invitee=/);
    await expect(page.getByRole("status")).toContainText(
      `Invitation envoyée à ${nom} (${adresse}). Le lien est valable 7 jours.`,
    );
    await expect(page.getByRole("link", { name: `${L.gererAcces} ${L.gererAccesDe} ${nom}` }).first()).toBeAttached();

    // même adresse une seconde fois : refus d'identity sous le champ, curseur dedans
    await page.goto("/administration/utilisateurs/inviter");
    await page.getByLabel(I.nomAffiche).fill(`${nom} bis`);
    await page.getByLabel(I.adresse).fill(adresse);
    await page.getByRole("button", { name: I.envoyer }).click();
    await page.getByRole("dialog").getByRole("button", { name: I.envoyer }).click();
    const champ = page.getByLabel(I.adresse);
    await expect(champ).toHaveAccessibleDescription(`${I.aideAdresse} ${libelle("utilisateurs.email_deja_utilise")}`);
    await expect(champ).toBeFocused();
  });

});

test.describe("Administration › Utilisateurs, associé", () => {
  test.use({ sessionAdmin: "associe" });

  test("associé : pas d'« Administration » au menu ; l'adresse ouverte quand même donne la page réservée (R0-06)", async ({
    page,
  }) => {
    await page.goto("/");
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
