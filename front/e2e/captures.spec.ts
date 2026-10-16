// Captures pour la revue UX des écrans construits (lot 0) : chaque écran et ses états principaux, sur ordinateur et
// à 360 px (un projet chacun). Seulement si LEPALIER_E2E_CAPTURES est posé (dossier de l'hôte monté) ; comptes
// propres aux captures (créés par scripts/tests/test_plateforme.py), sans toucher aux données des autres essais.
import type { Page, TestInfo } from "@playwright/test";
import { TEXTES } from "../src/textes";
import { base32EnHex, codeFaux, codeTotp, compteVise, expect, pret, test } from "./aides";

const DOSSIER = process.env.LEPALIER_E2E_CAPTURES ?? "";
const MOT_DE_PASSE = process.env.LEPALIER_E2E_MOT_DE_PASSE ?? "";

type CompteCaptures = { email: string; secret: string; invitation: string; reinitialisation: string };

function compte(projet: string): CompteCaptures {
  const comptes = JSON.parse(process.env.LEPALIER_E2E_COMPTES_CAPTURES ?? "{}") as Record<string, CompteCaptures>;
  return comptes[projet]!;
}

async function capturer(page: Page, infos: TestInfo, nom: string): Promise<void> {
  await page.screenshot({ path: `${DOSSIER}/${infos.project.name}/${nom}.png`, fullPage: true });
}

async function ouvrir(page: Page, adresse: string): Promise<void> {
  await page.goto("about:blank");
  await page.goto(adresse);
}

test.describe("Captures de la revue UX", () => {
  test.skip(!DOSSIER, "captures seulement sur demande (LEPALIER_E2E_CAPTURES)");

  test("écrans hors connexion", async ({ page }, infos) => {
    const c = compte(infos.project.name);
    await page.goto("/connexion");
    await capturer(page, infos, "01-se-connecter");
    await page.getByLabel(TEXTES.connexion.adresse).fill(c.email);
    await page.getByLabel(TEXTES.connexion.motDePasse, { exact: true }).fill("un mot de passe faux");
    await page.getByRole("button", { name: TEXTES.connexion.bouton }).click();
    await expect(page.getByLabel(TEXTES.connexion.motDePasse, { exact: true })).toBeFocused();
    await capturer(page, infos, "02-se-connecter-mot-de-passe-faux");
    await page.getByLabel(TEXTES.connexion.motDePasse, { exact: true }).fill(MOT_DE_PASSE);
    await page.getByRole("button", { name: TEXTES.connexion.bouton }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(TEXTES.code.titre);
    await pret(page);
    await capturer(page, infos, "03-code");
    await page.getByLabel(TEXTES.code.libelle).fill(codeFaux(c.secret));
    await page.getByRole("button", { name: TEXTES.connexion.bouton }).click();
    await expect(page.getByLabel(TEXTES.code.libelle)).toBeFocused();
    await capturer(page, infos, "04-code-faux");
    await page.getByRole("button", { name: TEXTES.code.utiliserSecours }).click();
    await capturer(page, infos, "05-code-de-secours");
    await page.getByRole("button", { name: TEXTES.code.utiliserApplication }).click();
    await page.getByLabel(TEXTES.code.libelle).fill(codeTotp(c.secret));
    await page.getByRole("button", { name: TEXTES.connexion.bouton }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(TEXTES.accueil.titre);
    await capturer(page, infos, "06-accueil");

    await ouvrir(page, "/mot-de-passe-oublie");
    await capturer(page, infos, "07-mot-de-passe-oublie");
    await page.getByLabel(TEXTES.reinitialisation.demande.adresse).fill("personne@essai.local");
    await page.getByRole("button", { name: TEXTES.reinitialisation.demande.bouton }).click();
    await expect(page.getByRole("status")).toBeVisible();
    await capturer(page, infos, "08-mot-de-passe-oublie-envoye");

    await ouvrir(page, "/reinitialisation");
    await capturer(page, infos, "09-nouveau-mot-de-passe-sans-lien");
    await ouvrir(page, `/reinitialisation#${c.reinitialisation}`);
    await expect(page.getByLabel(TEXTES.reinitialisation.choix.motDePasse, { exact: true })).toBeVisible();
    await capturer(page, infos, "10-nouveau-mot-de-passe");
    await page.getByLabel(TEXTES.reinitialisation.choix.motDePasse, { exact: true }).fill("la mer est calme");
    await page.getByLabel(TEXTES.motDePasse.confirmation, { exact: true }).fill("la mer est calme ce soir");
    await page.getByRole("button", { name: TEXTES.reinitialisation.choix.bouton }).click();
    await expect(page.getByLabel(TEXTES.motDePasse.confirmation, { exact: true })).toBeFocused();
    await capturer(page, infos, "11-nouveau-mot-de-passe-confirmation-differente");

    await ouvrir(page, "/activation");
    await capturer(page, infos, "12-activation-sans-lien");
    await ouvrir(page, "/cette-page-n-existe-pas");
    await capturer(page, infos, "13-page-introuvable");
  });

  test("activation, codes de secours, accueil après activation", async ({ page }, infos) => {
    const c = compte(infos.project.name);
    await ouvrir(page, `/activation#${c.invitation}`);
    await expect(page.getByRole("heading", { level: 2, name: TEXTES.activation.etapes[0] })).toBeVisible();
    await capturer(page, infos, "20-activation-etape-1");
    await page.getByRole("button", { name: TEXTES.activation.continuer }).click();
    await page.getByLabel(TEXTES.activation.motDePasse, { exact: true }).fill("le chat dort sur le toit");
    await page.getByLabel(TEXTES.motDePasse.confirmation, { exact: true }).fill("le chat dort sur le toi");
    await page.getByRole("button", { name: TEXTES.activation.continuer }).click();
    await expect(page.getByLabel(TEXTES.motDePasse.confirmation, { exact: true })).toBeFocused();
    await capturer(page, infos, "21-activation-etape-2-confirmation-differente");
    await page.getByLabel(TEXTES.motDePasse.confirmation, { exact: true }).fill("le chat dort sur le toit");
    await page.getByRole("button", { name: TEXTES.activation.continuer }).click();
    await expect(page.getByRole("img", { name: TEXTES.activation.altQr })).toBeVisible();
    await capturer(page, infos, "22-activation-etape-3");
    const cle = (await page.locator(".cle code").textContent()) ?? "";
    await page.getByLabel(TEXTES.activation.libelleCode).fill(codeTotp(base32EnHex(cle)));
    await page.getByRole("button", { name: TEXTES.activation.bouton }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(TEXTES.codes.titre);
    await capturer(page, infos, "23-codes-de-secours");
    await page.getByRole("button", { name: TEXTES.codes.continuer }).click();
    await capturer(page, infos, "24-codes-de-secours-case-non-cochee");
    await page.emulateMedia({ media: "print" });
    await capturer(page, infos, "25-codes-de-secours-impression");
    await page.emulateMedia({ media: "screen" });
    await page.getByRole("checkbox", { name: TEXTES.codes.caseNotes }).check();
    await page.getByRole("button", { name: TEXTES.codes.continuer }).click();
    await expect(page.getByRole("status")).toContainText(TEXTES.accueil.compteActive);
    await capturer(page, infos, "26-accueil-compte-active");
  });
});

test.describe("Captures de la revue UX, gérant", () => {
  test.skip(!DOSSIER, "captures seulement sur demande (LEPALIER_E2E_CAPTURES)");
  test.use({ sessionAdmin: "gerant" });

  test("administration", async ({ page }, infos) => {
    const L = TEXTES.utilisateurs.liste;
    await page.goto("/administration/utilisateurs");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(L.titre);
    await capturer(page, infos, "30-utilisateurs");
    await page.goto("/administration/utilisateurs/inviter");
    await capturer(page, infos, "31-inviter");
    await page.getByLabel(TEXTES.utilisateurs.inviter.nomAffiche).fill("Mme Exemple");
    await page.getByLabel(TEXTES.utilisateurs.inviter.adresse).fill("adresse-incorrecte");
    await page.getByLabel(TEXTES.utilisateurs.inviter.nomAffiche).focus();
    await capturer(page, infos, "32-inviter-adresse-incorrecte");
    await page.getByLabel(TEXTES.utilisateurs.inviter.adresse).fill(`exemple-${infos.project.name}@essai.local`);
    await page.getByRole("button", { name: TEXTES.utilisateurs.inviter.envoyer }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await capturer(page, infos, "33-inviter-confirmation");
    await page.keyboard.press("Escape");

    const vise = compteVise("role", infos.project.name);
    await page.goto("/administration/utilisateurs");
    await page.getByRole("link", { name: `${L.gererAcces} ${L.gererAccesDe} ${vise.nom}` }).first().click();
    await pret(page);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Accès de ${vise.nom}`);
    await capturer(page, infos, "34-gerer-l-acces");
    await page.getByRole("button", { name: TEXTES.utilisateurs.fiche.suspendre.bouton }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await capturer(page, infos, "35-gerer-l-acces-confirmation-suspension");
    await page.keyboard.press("Escape");
    await page.getByRole("link", { name: TEXTES.utilisateurs.fiche.changerRole }).click();
    await pret(page);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Changer le rôle de ${vise.nom}`);
    await capturer(page, infos, "36-changer-le-role");
    await page.getByRole("radio", { name: new RegExp(`^${TEXTES.roles.gerant} — `) }).check();
    await page.getByRole("button", { name: TEXTES.utilisateurs.role.enregistrer }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await capturer(page, infos, "37-changer-le-role-confirmation");
  });
});

test.describe("Captures de la revue UX, associé", () => {
  test.skip(!DOSSIER, "captures seulement sur demande (LEPALIER_E2E_CAPTURES)");
  test.use({ sessionAdmin: "associe" });

  test("page réservée au gérant", async ({ page }, infos) => {
    await page.goto("/administration/utilisateurs");
    await capturer(page, infos, "40-page-reservee");
  });
});
