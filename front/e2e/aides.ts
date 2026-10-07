// Aides des essais de bout en bout : toute violation de la politique de sécurité (CSP) signalée par le
// navigateur ou dans la console fait échouer l'essai ; contrôle d'accessibilité axe-core (WCAG 2.1 AA).
import { createHmac } from "node:crypto";
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test as base } from "@playwright/test";
import { TEXTES } from "../src/textes";

declare global {
  interface Window {
    __violationsCsp: string[];
  }
}

// limite de débit de /api/identity/auth/ : haute dans le projet d'essai (compose.essai.yml), aucun espacement ici ;
// la vraie limite est vérifiée par N13 (scripts/tests/test_plateforme.py)
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

// Comptes de l'écran du code, un par projet Playwright (l'anti-rejeu refuse deux fois un même code TOTP) :
// clé TOTP en hexadécimal et deux codes de secours, créés par scripts/tests/test_plateforme.py.
type CompteCode = { email: string; secret: string; secours: string[]; nom?: string };

function lireCompte(variable: string, projet: string): CompteCode {
  const comptes = JSON.parse(process.env[variable] ?? "{}") as Record<string, CompteCode>;
  const compte = comptes[projet];
  if (!compte) throw new Error(`compte absent pour le projet ${projet} (${variable})`);
  return compte;
}

export function compteCode(projet: string): CompteCode {
  return lireCompte("LEPALIER_E2E_COMPTES_CODE", projet);
}

// gérant de l'essai de l'accueil, un par projet
export function compteAccueil(projet: string): CompteCode {
  return lireCompte("LEPALIER_E2E_COMPTES_ACCUEIL", projet);
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

// Jeton du lien d'invitation du projet (une invitation par projet : l'activation la consomme).
export function jetonInvitation(projet: string): string {
  const jetons = JSON.parse(process.env.LEPALIER_E2E_INVITATIONS ?? "{}") as Record<string, string>;
  const jeton = jetons[projet];
  if (!jeton) throw new Error(`invitation absente pour le projet ${projet}`);
  return jeton;
}

// Clé affichée à l'écran (base32, RFC 4648, espaces tolérés) en hexadécimal, pour codeTotp.
export function base32EnHex(cle: string): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const caractere of cle.replace(/\s+/g, "").toUpperCase()) {
    const valeur = alphabet.indexOf(caractere);
    if (valeur < 0) throw new Error(`caractère hors base32 : ${caractere}`);
    bits += valeur.toString(2).padStart(5, "0");
  }
  const octets = bits.match(/.{8}/g) ?? [];
  return octets.map((o) => parseInt(o, 2).toString(16).padStart(2, "0")).join("");
}

// gérant ou associé de l'essai de l'administration, un de chaque par projet
export function compteAdmin(role: "gerant" | "associe", projet: string): CompteCode {
  return lireCompte("LEPALIER_E2E_COMPTES_ADMIN", `${role}-${projet}`);
}

// dernier pas TOTP utilisé par clé : identity refuse deux fois le même code (anti-rejeu), y compris d'un essai à
// l'autre pour un même compte
const dernierPas = new Map<string, number>();

async function codeNeuf(secretHex: string): Promise<string> {
  const pas = Math.floor(Date.now() / 30000);
  if ((dernierPas.get(secretHex) ?? -1) >= pas) {
    await new Promise((fin) => setTimeout(fin, (pas + 1) * 30000 - Date.now() + 200));
  }
  dernierPas.set(secretHex, Math.floor(Date.now() / 30000));
  return codeTotp(secretHex);
}

// connexion complète : adresse, mot de passe (MOT_DE_PASSE de l'essai), puis code de l'application
export async function seConnecter(page: Page, email: string, secretHex: string): Promise<void> {
  await page.goto("/connexion");
  await page.getByLabel(TEXTES.connexion.adresse).fill(email);
  await page.getByLabel(TEXTES.connexion.motDePasse, { exact: true }).fill(COMPTE.motDePasse);
  await page.getByRole("button", { name: TEXTES.connexion.bouton }).click();
  await page.getByLabel(TEXTES.code.libelle).fill(await codeNeuf(secretHex));
  await page.getByRole("button", { name: TEXTES.connexion.bouton }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(TEXTES.accueil.titre);
}

export async function sansDefilementHorizontal(page: Page): Promise<void> {
  const largeurs = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth]);
  expect(largeurs[0]).toBeLessThanOrEqual(largeurs[1]!);
}
