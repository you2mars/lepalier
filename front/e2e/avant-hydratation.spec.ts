// Formulaire envoyé avant la prise en main de la page par React : JavaScript de Next bloqué, chaque champ visible
// rempli d'un marqueur distinct, bouton d'envoi cliqué. Le navigateur envoie alors lui-même le formulaire : la
// requête partie est relevée (méthode, adresse, corps) ; aucun marqueur (mot de passe, code, adresse saisie) ne doit
// apparaître dans une adresse. Le journal d'accès de nginx est vérifié par scripts/tests/test_plateforme.py.
import type { Page, Request } from "@playwright/test";
import { COMPTE, expect, test } from "./aides";

const URL_ESSAI = process.env.LEPALIER_E2E_URL ?? "";
// jeton de forme valable, inconnu d'identity : la page servie est la même pour tout jeton (fragment jamais envoyé)
const FAUX_JETON = "A".repeat(43);

type Releve = {
  formulaire: string;
  champs: number;
  methode: string;
  adresse: string;
  corps: string;
  statut?: number;
  titreApres?: string;
};

async function sansJavaScript(page: Page): Promise<void> {
  await page.route("**/_next/static/chunks/**", (route) => route.abort());
}

async function envoyerAvantHydratation(page: Page, formulaire: string, adresse: string): Promise<Releve> {
  await page.goto(adresse, { waitUntil: "domcontentloaded" });
  expect(await page.locator("html[data-hydrate]").count(), "page prise en main malgré le blocage").toBe(0);
  const champs = page.locator("form input:visible:not([readonly]):not([type=radio]):not([type=checkbox])");
  const nombre = await champs.count();
  for (let i = 0; i < nombre; i++) await champs.nth(i).fill(`MARQUEUR${i}SECRET`);
  const bouton = page.locator("form button[type=submit]").first();
  if ((await bouton.count()) === 0) {
    const releve = { formulaire, champs: nombre, methode: "aucun bouton d'envoi", adresse: "", corps: "" };
    console.log(`AVANT-HYDRATATION ${JSON.stringify(releve)}`);
    return releve;
  }
  const requete: Request | null = await Promise.all([
    page.waitForRequest((r) => r.isNavigationRequest() && r.frame() === page.mainFrame(), { timeout: 5000 }),
    bouton.click(),
  ])
    .then(([r]) => r)
    .catch(() => null);
  const reponse = await requete?.response();
  await page.waitForLoadState("domcontentloaded");
  const releve = {
    formulaire,
    champs: nombre,
    methode: requete?.method() ?? "aucune requête",
    adresse: requete?.url().replace(URL_ESSAI, "") ?? "",
    corps: requete?.postData() ?? "",
    statut: reponse?.status(),
    titreApres: await page.title(),
  };
  console.log(`AVANT-HYDRATATION ${JSON.stringify(releve)}`);
  expect(releve.adresse, `${formulaire} : marqueur dans l'adresse`).not.toContain("MARQUEUR");
  expect(releve.adresse, `${formulaire} : paramètres dans l'adresse`).not.toContain("?");
  return releve;
}

test.describe("Formulaires envoyés avant la prise en main par React", () => {
  test.skip(({ isMobile }) => isMobile, "même page servie ; un seul projet suffit");

  test("connexion, code, mot de passe oublié, activation, réinitialisation", async ({ context }) => {
    const page = await context.newPage();
    await sansJavaScript(page);
    await envoyerAvantHydratation(page, "connexion", "/connexion");
    await envoyerAvantHydratation(page, "mot de passe oublié", "/mot-de-passe-oublie");
    await envoyerAvantHydratation(page, "activation", `/activation#${FAUX_JETON}`);
    await envoyerAvantHydratation(page, "réinitialisation", `/reinitialisation#${FAUX_JETON}`);
    // écran du code : pré-session ouverte par l'étape du mot de passe, sans le navigateur
    const reponse = await page.request.post("/api/identity/auth/connexion", {
      data: { email: COMPTE.email, mot_de_passe: COMPTE.motDePasse },
      headers: { Origin: URL_ESSAI },
    });
    expect(reponse.status()).toBe(200);
    await envoyerAvantHydratation(page, "code", "/connexion/code");
  });

  test.describe("gérant", () => {
    test.use({ sessionAdmin: "gerant" });

    test("invitation", async ({ context }) => {
      const page = await context.newPage();
      await sansJavaScript(page);
      await envoyerAvantHydratation(page, "invitation", "/administration/utilisateurs/inviter");
    });
  });
});
