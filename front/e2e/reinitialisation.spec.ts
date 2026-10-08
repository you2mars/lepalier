// Mot de passe oublié (écran 8) et Choisir un nouveau mot de passe (écran 9) : ADR 0006, R0-20 à R0-23 ; politique
// de sécurité vérifiée par aides.ts. Un compte et un lien par projet ; le changement réussi consomme le lien.
import type { Page } from "@playwright/test";
import { libelle, messageMotDePasse } from "../src/lib/libelles";
import { TEXTES } from "../src/textes";
import {
  codeFaux,
  codeTotp,
  expect,
  reinitialisation,
  sansDefilementHorizontal,
  test,
  verifierAccessibilite,
} from "./aides";

const D = TEXTES.reinitialisation.demande;
const C = TEXTES.reinitialisation.choix;
const M = TEXTES.motDePasse;
const NOUVEAU = "la mer est calme ce matin";

async function ouvrirLeLien(page: Page, jeton: string): Promise<void> {
  // depuis une autre page : sinon le seul changement de « # » ne recharge pas l'écran
  await page.goto("about:blank");
  await page.goto(`/reinitialisation#${jeton}`);
}

async function saisir(page: Page, motDePasse: string, confirmation: string, code: string): Promise<void> {
  await page.getByLabel(C.motDePasse, { exact: true }).fill(motDePasse);
  await page.getByLabel(M.confirmation, { exact: true }).fill(confirmation);
  await page.getByLabel(C.code, { exact: true }).fill(code);
  await page.getByRole("button", { name: C.bouton }).click();
}

test.describe("Mot de passe oublié", () => {
  test("demande : le formulaire disparaît, même message que le compte existe ou non ; accessibilité, 360 px", async ({
    page,
  }) => {
    await page.goto("/mot-de-passe-oublie");
    await expect(page).toHaveTitle("Mot de passe oublié — LePalier");
    await verifierAccessibilite(page);
    await sansDefilementHorizontal(page);
    await page.getByLabel(D.adresse).fill("personne@essai.local");
    await page.getByRole("button", { name: D.bouton }).click();
    await expect(page.getByRole("status")).toContainText(libelle("reinitialisation.demande_envoyee"));
    await expect(page.getByRole("textbox")).toHaveCount(0);
    await expect(page.getByRole("link", { name: D.retour })).toBeVisible();
    // revue UX (M5) : l'adresse saisie est rappelée, une autre peut être saisie
    await expect(page.getByText(D.adresseSaisie)).toContainText("personne@essai.local");
    await page.getByRole("button", { name: D.autreAdresse }).click();
    await expect(page.getByLabel(D.adresse)).toHaveValue("personne@essai.local");
  });
});

test.describe("Choisir un nouveau mot de passe", () => {
  test("sans le lien : invitation à l'ouvrir et lien « Mot de passe oublié »", async ({ page }) => {
    await page.goto("/reinitialisation");
    await expect(page.getByText(C.sansLien)).toBeVisible();
    await expect(page.getByRole("link", { name: TEXTES.connexion.oublie })).toBeVisible();
  });

  test("confirmation différente, mot de passe refusé, code faux ; puis changement réussi ; lien ensuite invalide", async ({
    page,
  }, infos) => {
    const lien = reinitialisation(infos.project.name);
    await ouvrirLeLien(page, lien.jeton);
    await expect(page).toHaveTitle("Choisir un nouveau mot de passe — LePalier");
    await verifierAccessibilite(page);
    await sansDefilementHorizontal(page);

    await saisir(page, NOUVEAU, "la mer est calme ce soir", "000000");
    const confirmation = page.getByLabel(M.confirmation, { exact: true });
    await expect(confirmation).toHaveAccessibleDescription(M.differents);
    await expect(confirmation).toBeFocused();

    await saisir(page, "le palier est calme ce matin", "le palier est calme ce matin", codeFaux(lien.secret));
    const motDePasse = page.getByLabel(C.motDePasse, { exact: true });
    await expect(motDePasse).toHaveAccessibleDescription(
      `${TEXTES.activation.aideMotDePasse} ${messageMotDePasse("nom_application")}`,
    );
    await expect(motDePasse).toHaveValue("");
    await expect(motDePasse).toBeFocused();

    await saisir(page, NOUVEAU, NOUVEAU, codeFaux(lien.secret));
    const code = page.getByLabel(C.code, { exact: true });
    await expect(code).toHaveAccessibleDescription(`${C.aideCode} ${libelle("code.incorrect")}`);
    await expect(motDePasse).toHaveValue(NOUVEAU);
    await verifierAccessibilite(page);

    await code.fill(codeTotp(lien.secret));
    await page.getByRole("button", { name: C.bouton }).click();
    await expect(page).toHaveURL(/\/connexion\?motif=mot_de_passe_change$/);
    await expect(page.getByRole("status")).toContainText(TEXTES.connexion.motDePasseChange);

    // le lien a servi : la page ne montre que le message d'identity
    await ouvrirLeLien(page, lien.jeton);
    await saisir(page, NOUVEAU, NOUVEAU, "000000");
    await expect(page.getByText(libelle("reinitialisation.lien_invalide"))).toBeVisible();
    await expect(page.getByRole("textbox")).toHaveCount(0);
  });
});
