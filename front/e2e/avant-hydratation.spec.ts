// Formulaire envoyé avant la prise en main de la page par React (constat UX (18), téléphone lent) : le JavaScript
// de Next est retardé, jamais bloqué, pour que le script en ligne EnvoiApresPriseEnMain tourne. Clic trop tôt :
// aucune requête ne part et les champs restent remplis ; une fois la page prête, le même bouton envoie normalement
// (appel de l'API par React). Aucun marqueur saisi ne doit apparaître dans une adresse ; le journal d'accès de nginx
// est vérifié par scripts/tests/test_plateforme.py. Pages ouvertes par context.newPage() : la page du fixture
// attend la prise en main après chaque goto.
import type { Locator, Page, Request } from "@playwright/test";
import { COMPTE, compteAdmin, expect, pret, test } from "./aides";

const URL_ESSAI = process.env.LEPALIER_E2E_URL ?? "";
// jeton de forme valable, inconnu d'identity : la page servie est la même pour tout jeton (fragment jamais envoyé)
const FAUX_JETON = "A".repeat(43);

// JavaScript de Next retenu jusqu'à l'appel de la fonction renvoyée
async function retarderJavaScript(page: Page): Promise<() => void> {
  let liberer!: () => void;
  const porte = new Promise<void>((resolu) => {
    liberer = resolu;
  });
  await page.route("**/_next/static/chunks/**", async (route) => {
    await porte;
    await route.continue();
  });
  return liberer;
}

function champs(page: Page): Locator {
  return page.locator("form input:visible:not([readonly]):not([type=radio]):not([type=checkbox])");
}

// valeurs acceptées par les vérifications du front, chacune portant un marqueur : adresse, mot de passe (même
// valeur dans la confirmation), code à 6 chiffres
async function remplir(page: Page, email: string): Promise<string[]> {
  const liste = champs(page);
  const valeurs: string[] = [];
  for (let i = 0; i < (await liste.count()); i++) {
    const champ = liste.nth(i);
    const type = await champ.getAttribute("type");
    const mode = await champ.getAttribute("inputmode");
    const valeur =
      type === "email" ? email : type === "password" ? "MARQUEUR phrase de passe assez longue" : mode === "numeric" ? "123456" : "M. Marqueur";
    await champ.fill(valeur);
    valeurs.push(valeur);
  }
  return valeurs;
}

async function navigationPartie(page: Page, action: () => Promise<void>): Promise<Request | null> {
  const attente = page
    .waitForRequest((r) => r.isNavigationRequest() && r.frame() === page.mainFrame(), { timeout: 2000 })
    .catch(() => null);
  await action();
  return attente;
}

async function clicTropTot(page: Page, formulaire: string, adresse: string, email: string): Promise<string[]> {
  await page.goto(adresse, { waitUntil: "domcontentloaded" });
  expect(await page.locator("html[data-hydrate]").count(), "page prise en main malgré le retard").toBe(0);
  expect(await page.locator("form[data-pret]").count(), "formulaire pris en main malgré le retard").toBe(0);
  const valeurs = await remplir(page, email);
  expect(valeurs.length, `${formulaire} : aucun champ`).toBeGreaterThan(0);
  const requete = await navigationPartie(page, () => page.locator("form button[type=submit]").first().click());
  console.log(`AVANT-HYDRATATION ${JSON.stringify({ formulaire, champs: valeurs.length, requete: requete?.url() ?? null })}`);
  expect(requete?.url().replace(URL_ESSAI, "") ?? null, `${formulaire} : requête partie avant la prise en main`).toBeNull();
  expect(await page.locator("html[data-hydrate]").count()).toBe(0);
  const apres = champs(page);
  for (let i = 0; i < valeurs.length; i++) await expect(apres.nth(i), `${formulaire} : champ vidé`).toHaveValue(valeurs[i]!);
  return valeurs;
}

// une fois la page prête, sans rien ressaisir : les valeurs tapées trop tôt sont celles envoyées par React
// confirmer : l'invitation passe par sa confirmation récapitulative (UX-3) avant l'appel de l'API
async function envoiNormalUnePagePrete(
  page: Page,
  formulaire: string,
  liberer: () => void,
  valeurs: string[],
  confirmer = false,
): Promise<void> {
  liberer();
  await pret(page);
  // formulaire pris en main (composant Formulaire) : arrivé en flux, il peut l'être après la page
  await page.locator("form[data-pret]").waitFor({ state: "attached" });
  const liste = champs(page);
  for (let i = 0; i < valeurs.length; i++) await expect(liste.nth(i), `${formulaire} : champ vidé à la prise en main`).toHaveValue(valeurs[i]!);
  const attente = page.waitForRequest((r) => r.url().includes("/api/") && r.method() !== "GET", { timeout: 10000 });
  await page.locator("form button[type=submit]").first().click();
  if (confirmer) await page.getByRole("dialog").getByRole("button").first().click();
  const appel = await attente;
  console.log(`APRES-HYDRATATION ${JSON.stringify({ formulaire, adresse: appel.url().replace(URL_ESSAI, ""), corps: appel.postData() })}`);
  expect(appel.url(), `${formulaire} : marqueur dans l'adresse`).not.toContain("MARQUEUR");
  expect(appel.isNavigationRequest(), `${formulaire} : envoi par le navigateur au lieu de React`).toBe(false);
  const corps = appel.postData() ?? "";
  for (const valeur of new Set(valeurs)) expect(corps, `${formulaire} : valeur saisie trop tôt perdue`).toContain(valeur);
}

test.describe("Formulaires envoyés avant la prise en main par React (constat UX (18))", () => {
  test.skip(({ isMobile }) => isMobile, "même page servie ; un seul projet suffit");

  for (const [formulaire, adresse] of [
    ["connexion", "/connexion"],
    ["mot de passe oublié", "/mot-de-passe-oublie"],
  ] as const) {
    test(`${formulaire} : clic trop tôt sans effet, puis envoi normal`, async ({ context }) => {
      const page = await context.newPage();
      const liberer = await retarderJavaScript(page);
      const valeurs = await clicTropTot(page, formulaire, adresse, "marqueur@essai.invalide");
      await envoiNormalUnePagePrete(page, formulaire, liberer, valeurs);
    });
  }

  // activation et réinitialisation : le jeton est lu après « # » par React ; avant la prise en main, la page ne
  // montre qu'un squelette, sans formulaire à envoyer
  for (const [formulaire, adresse] of [
    ["activation", `/activation#${FAUX_JETON}`],
    ["réinitialisation", `/reinitialisation#${FAUX_JETON}`],
  ] as const) {
    test(`${formulaire} : aucun formulaire avant la prise en main`, async ({ context }) => {
      const page = await context.newPage();
      const liberer = await retarderJavaScript(page);
      await page.goto(adresse, { waitUntil: "domcontentloaded" });
      expect(await page.locator("html[data-hydrate]").count()).toBe(0);
      expect(await page.locator("form").count(), `${formulaire} : formulaire avant la prise en main`).toBe(0);
      liberer();
    });
  }

  // code : un code faux compterait parmi les essais du compte partagé ; seul le clic trop tôt est vérifié
  test("code : clic trop tôt sans effet", async ({ context }) => {
    const page = await context.newPage();
    const liberer = await retarderJavaScript(page);
    const reponse = await page.request.post("/api/identity/auth/connexion", {
      data: { email: COMPTE.email, mot_de_passe: COMPTE.motDePasse },
      headers: { Origin: URL_ESSAI },
    });
    expect(reponse.status()).toBe(200);
    await clicTropTot(page, "code", "/connexion/code", "");
    liberer();
  });

  test.describe("gérant", () => {
    test.use({ sessionAdmin: "gerant" });

    // adresse du gérant connecté : l'invitation est refusée (compte existant), aucune personne n'est créée
    test("invitation : clic trop tôt sans effet, puis envoi normal", async ({ context }, infos) => {
      const page = await context.newPage();
      const email = compteAdmin("gerant", infos.project.name).email;
      const liberer = await retarderJavaScript(page);
      const valeurs = await clicTropTot(page, "invitation", "/administration/utilisateurs/inviter", email);
      await envoiNormalUnePagePrete(page, "invitation", liberer, valeurs, true);
    });
  });
});
