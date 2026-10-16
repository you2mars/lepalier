// Essai de charge (diagnostic, seulement si LEPALIER_E2E_CHARGE est posé) : processeur de Chromium ralenti (×4, par
// le protocole de débogage), puis l'invitation et l'annulation d'une invitation, comme dans administration.spec.ts.
// À répéter avec LEPALIER_E2E_ARGS="--grep=processeur.ralenti --repeat-each=40" (arguments séparés par des espaces,
// donc sans espace dans le motif) ; trace gardée à chaque échec.
import { TEXTES } from "../src/textes";
import { attendreAdresse, expect, pret, test } from "./aides";

const L = TEXTES.utilisateurs.liste;
const I = TEXTES.utilisateurs.inviter;
const F = TEXTES.utilisateurs.fiche;

test.describe("Essai de charge : écriture puis changement de page", () => {
  test.skip(
    !process.env.LEPALIER_E2E_CHARGE,
    "diagnostic seulement (LEPALIER_E2E_CHARGE)",
  );
  test.use({ sessionAdmin: "gerant" });

  test("charge : inviter puis annuler l'invitation, processeur ralenti ×4", async ({
    page,
  }, infos) => {
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
    const suffixe = `${infos.project.name}-${infos.repeatEachIndex}-${Date.now()}`;
    const nom = `Mme Charge ${suffixe}`;
    const adresse = `charge-${suffixe}@essai.local`;

    // invitation : même déroulé que l'essai de l'écran 6.2
    await page.goto("/administration/utilisateurs");
    await page.getByRole("link", { name: L.inviter }).click();
    await expect(page).toHaveTitle("Inviter une personne — LePalier");
    await pret(page);
    await page.getByLabel(I.nomAffiche).fill(nom);
    await page.getByLabel(I.adresse).fill(adresse);
    const envoyer = page.getByRole("button", { name: I.envoyer });
    await envoyer.click();
    const boite = page.getByRole("dialog");
    await expect(
      boite.getByRole("button", { name: I.confirmation.modifier }),
    ).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(boite).toBeHidden();
    await envoyer.click();
    await boite.getByRole("button", { name: I.confirmation.modifier }).click();
    await expect(boite).toBeHidden();
    await envoyer.click();
    await boite.getByRole("button", { name: I.envoyer }).click();
    await attendreAdresse(page, /\/administration\/utilisateurs\?invitee=/);
    await expect(page.getByRole("status")).toContainText(
      `Invitation envoyée à ${nom}`,
    );

    // annulation : même déroulé que l'essai de l'écran 6.3
    await page
      .getByRole("link", { name: `${L.gererAcces} ${L.gererAccesDe} ${nom}` })
      .first()
      .click();
    await pret(page);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      `Accès de ${nom}`,
    );
    await page.getByRole("button", { name: F.renvoyer.bouton }).click();
    await expect(page.getByRole("status")).toContainText(
      `Invitation renvoyée à ${nom}`,
    );
    await page
      .getByRole("button", { name: F.annulerInvitation.bouton })
      .click();
    const annulation = page.getByRole("dialog", {
      name: `Annuler l'invitation de ${nom} ?`,
    });
    await annulation
      .getByRole("button", { name: F.annulerInvitation.bouton })
      .click();
    await attendreAdresse(page, /\/administration\/utilisateurs$/);
    await expect(page.getByRole("status")).toContainText(
      `Invitation de ${nom} annulée.`,
    );
  });
});
