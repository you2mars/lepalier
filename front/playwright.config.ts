// Essais de bout en bout sur la plateforme d'essai (make test-plateforme) : nginx, front et identity réels.
// LEPALIER_E2E_URL est fourni par scripts/tests/test_plateforme.py ; certificat auto-signé de make dev-certs.
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  // envois vers /api/identity/auth/ espacés de 6 secondes (aides.ts) : délais allongés en conséquence
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  // dans l'image Playwright, le dépôt est en lecture seule : résultats ailleurs
  outputDir: process.env.LEPALIER_E2E_SORTIE ?? "test-results",
  use: {
    baseURL: process.env.LEPALIER_E2E_URL,
    ignoreHTTPSErrors: true,
    locale: "fr-FR",
    timezoneId: "Europe/Paris",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "ordinateur", use: { ...devices["Desktop Chrome"] } },
    {
      name: "mobile-360",
      use: { browserName: "chromium", viewport: { width: 360, height: 740 }, isMobile: true, hasTouch: true },
    },
  ],
});
