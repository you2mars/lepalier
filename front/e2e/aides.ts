// Aides des essais de bout en bout : toute violation de la politique de sécurité (CSP) signalée par le
// navigateur ou dans la console fait échouer l'essai ; contrôle d'accessibilité axe-core (WCAG 2.1 AA).
import { createHmac } from "node:crypto";
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test as base } from "@playwright/test";

declare global {
  interface Window {
    __violationsCsp: string[];
  }
}

// nginx limite /api/identity/auth/ à 10 requêtes par minute et par adresse, rafale de 10 (N13) ; les deux projets
// partagent l'adresse 127.0.0.1 et la rafale a pu être consommée par les essais Python juste avant : un envoi
// toutes les 6 secondes au plus, dès le premier, et la limite n'est jamais atteinte.
const INTERVALLE_AUTH_MS = 6_000;
let prochainEnvoiAuth = Date.now() + INTERVALLE_AUTH_MS;

export const test = base.extend<{ violationsCsp: string[]; espacementAuth: void }>({
  espacementAuth: [
    async ({ page }, utiliser) => {
      await page.route("**/api/identity/auth/**", async (route) => {
        const attente = prochainEnvoiAuth - Date.now();
        prochainEnvoiAuth = Math.max(Date.now(), prochainEnvoiAuth) + INTERVALLE_AUTH_MS;
        if (attente > 0) await new Promise((fin) => setTimeout(fin, attente));
        await route.continue();
      });
      await utiliser();
    },
    { auto: true },
  ],
  violationsCsp: [
    async ({ page }, utiliser) => {
      const violations: string[] = [];
      await page.addInitScript(() => {
        window.__violationsCsp = [];
        document.addEventListener("securitypolicyviolation", (e) => {
          window.__violationsCsp.push(`${e.violatedDirective} ${e.blockedURI}`);
        });
      });
      page.on("console", (message) => {
        const texte = message.text();
        if (/Content Security Policy|Refused to (execute|load|apply|connect)/i.test(texte)) violations.push(texte);
      });
      await utiliser(violations);
      const signalees = await page.evaluate(() => window.__violationsCsp ?? []).catch(() => []);
      expect([...violations, ...signalees], "violations de la politique de sécurité (CSP)").toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };

export async function verifierAccessibilite(page: Page): Promise<void> {
  const resultat = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(resultat.violations.map((v) => `${v.id} : ${v.help}`)).toEqual([]);
}

export const COMPTE = {
  email: process.env.LEPALIER_E2E_EMAIL ?? "",
  motDePasse: process.env.LEPALIER_E2E_MOT_DE_PASSE ?? "",
};

// Comptes de l'écran du code, un par projet Playwright (l'anti-rejeu refuse deux fois un même code TOTP) :
// clé TOTP en hexadécimal et deux codes de secours, créés par scripts/tests/test_plateforme.py.
type CompteCode = { email: string; secret: string; secours: string[] };

export function compteCode(projet: string): CompteCode {
  const comptes = JSON.parse(process.env.LEPALIER_E2E_COMPTES_CODE ?? "{}") as Record<string, CompteCode>;
  const compte = comptes[projet];
  if (!compte) throw new Error(`compte de l'écran du code absent pour le projet ${projet}`);
  return compte;
}

// RFC 6238 (SHA-1, 6 chiffres, pas de 30 s), comme les applications d'authentification
export function codeTotp(secretHex: string, decalagePas = 0): string {
  const compteur = Buffer.alloc(8);
  compteur.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000) + decalagePas));
  const empreinte = createHmac("sha1", Buffer.from(secretHex, "hex")).update(compteur).digest();
  const decalage = empreinte[empreinte.length - 1]! & 0x0f;
  return String((empreinte.readUInt32BE(decalage) & 0x7fffffff) % 1_000_000).padStart(6, "0");
}

// un code à 6 chiffres qu'aucun pas proche n'accepte
export function codeFaux(secretHex: string): string {
  const proches = new Set([-2, -1, 0, 1, 2].map((d) => codeTotp(secretHex, d)));
  for (let n = 0; ; n++) {
    const code = String(n).padStart(6, "0");
    if (!proches.has(code)) return code;
  }
}
