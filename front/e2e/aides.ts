// Aides des essais de bout en bout : toute violation de la politique de sécurité (CSP) signalée par le
// navigateur ou dans la console fait échouer l'essai ; contrôle d'accessibilité axe-core (WCAG 2.1 AA).
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test as base } from "@playwright/test";

declare global {
  interface Window {
    __violationsCsp: string[];
  }
}

export const test = base.extend<{ violationsCsp: string[] }>({
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
