// Administration › Utilisateurs (maquettes v3, écran 6.1) et page réservée au gérant (écran 7) : R0-04, R0-06,
// R0-20 à R0-23 ; politique de sécurité vérifiée par aides.ts. Un gérant et un associé par projet.
import { libelle } from "../src/lib/libelles";
import { TEXTES } from "../src/textes";
import { attendreAdresse, compteAdmin, compteVise, contenu, expect, pret, sansDefilementHorizontal, seConnecter, test, verifierAccessibilite } from "./aides";

const L = TEXTES.utilisateurs.liste;
const I = TEXTES.utilisateurs.inviter;
const F = TEXTES.utilisateurs.fiche;
const R = TEXTES.utilisateurs.role;
const D = TEXTES.descriptionsRoles;

test.describe("Administration › Utilisateurs, gérant", () => {
  test.use({ sessionAdmin: "gerant" });

  test("gérant : depuis le menu, liste des utilisateurs, fil d'Ariane, accessibilité, 360 px et zoom 200 % (R0-04)", async ({
    page,
    isMobile,
  }, infos) => {
    const compte = compteAdmin("gerant", infos.project.name);
    await page.goto("/");
    await page.getByRole("navigation", { name: TEXTES.cadre.menuPrincipal }).getByRole("link", { name: TEXTES.cadre.administration }).click();
    await attendreAdresse(page, /\/administration\/utilisateurs$/);
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
    await pret(page);
    // propres à chaque répétition (--repeat-each, diagnostic) : une adresse ne s'invite qu'une fois
    const suffixe = infos.repeatEachIndex ? `-${infos.repeatEachIndex}` : "";
    const nom = `Mme Invitée ${infos.project.name}${suffixe}`;
    const adresse = `invitee-${infos.project.name}${suffixe}@essai.local`;
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

    await attendreAdresse(page, /\/administration\/utilisateurs\?invitee=/);
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


  test("sa propre fiche : ni suspendre ni réinitialiser, la phrase qui explique ; accessibilité (6.3)", async ({
    page,
  }, infos) => {
    const moi = compteAdmin("gerant", infos.project.name);
    await page.goto("/administration/utilisateurs");
    await page.getByRole("link", { name: `${L.gererAcces} ${L.gererAccesDe} ${moi.nom}` }).first().click();
    await pret(page);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Accès de ${moi.nom}`);
    await expect(contenu(page).getByText(F.soiMeme)).toBeVisible();
    await expect(page.getByRole("button", { name: F.suspendre.bouton })).toHaveCount(0);
    await verifierAccessibilite(page);
    await sansDefilementHorizontal(page);
  });

  test("associé actif : suspendre (confirmation), réactiver, réinitialiser (confirmation) (6.3, R0-07)", async ({
    page,
  }, infos) => {
    const cible = compteVise("cible", infos.project.name);
    await page.goto("/administration/utilisateurs");
    await page.getByRole("link", { name: `${L.gererAcces} ${L.gererAccesDe} ${cible.nom}` }).first().click();
    await pret(page);
    await expect(contenu(page).getByText("Statut : Accès actif")).toBeVisible();

    await page.getByRole("button", { name: F.suspendre.bouton }).click();
    const boite = page.getByRole("dialog", { name: `Suspendre l'accès de ${cible.nom} ?` });
    await expect(boite.getByRole("button", { name: F.annuler })).toBeFocused();
    await verifierAccessibilite(page);
    await boite.getByRole("button", { name: F.suspendre.bouton }).click();
    await expect(page.getByRole("status")).toContainText(`Accès de ${cible.nom} suspendu.`);
    await expect(contenu(page).getByText("Statut : Accès suspendu")).toBeVisible();

    await page.getByRole("button", { name: F.reactiver.bouton }).click();
    await expect(page.getByRole("status")).toContainText(`Accès de ${cible.nom} réactivé.`);
    await expect(contenu(page).getByText("Statut : Accès actif")).toBeVisible();

    await page.getByRole("button", { name: F.reinitialiser.bouton }).click();
    const reinit = page.getByRole("dialog", { name: `Réinitialiser l'accès de ${cible.nom} ?` });
    await expect(reinit).toContainText(`sera envoyé à ${cible.email}.`);
    await reinit.getByRole("button", { name: F.reinitialiser.bouton }).click();
    await expect(page.getByRole("status")).toContainText(`Accès de ${cible.nom} réinitialisé ; un e-mail lui a été envoyé.`);
    // l'accès réinitialisé repart d'une invitation (ADR 0006)
    await expect(contenu(page).getByText("Statut : Invitation envoyée")).toBeVisible();
  });

  test("invitation : renvoyer, puis annuler (« Garder l'invitation » en premier) ; la liste dit ce qui a été fait (6.3)", async ({
    page,
  }, infos) => {
    const invite = compteVise("invite", infos.project.name);
    await page.goto("/administration/utilisateurs");
    await page.getByRole("link", { name: `${L.gererAcces} ${L.gererAccesDe} ${invite.nom}` }).first().click();
    await pret(page);
    await expect(contenu(page).getByText(/^Invitation envoyée le .+, valable jusqu'au .+\.$/)).toBeVisible();

    await page.getByRole("button", { name: F.renvoyer.bouton }).click();
    await expect(page.getByRole("status")).toContainText(`Invitation renvoyée à ${invite.nom} (${invite.email}).`);

    await page.getByRole("button", { name: F.annulerInvitation.bouton }).click();
    const boite = page.getByRole("dialog", { name: `Annuler l'invitation de ${invite.nom} ?` });
    await expect(boite.getByRole("button", { name: F.annulerInvitation.garder })).toBeFocused();
    await boite.getByRole("button", { name: F.annulerInvitation.bouton }).click();
    await attendreAdresse(page, /\/administration\/utilisateurs$/);
    await expect(page.getByRole("status")).toContainText(`Invitation de ${invite.nom} annulée.`);
    await expect(page.getByRole("link", { name: `${L.gererAcces} ${L.gererAccesDe} ${invite.nom}` })).toHaveCount(0);
  });

  test("changer le rôle : inchangé, opérateur, gérant (confirmation), de nouveau associé ; la fiche le dit (6.4)", async ({
    page,
  }, infos) => {
    const vise = compteVise("role", infos.project.name);
    const option = (r: "associe" | "operateur" | "gerant") => page.getByRole("radio", { name: new RegExp(`^${TEXTES.roles[r]} — `) });
    const ouvrir = async () => {
      await page.getByRole("link", { name: F.changerRole }).click();
      await pret(page);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Changer le rôle de ${vise.nom}`);
    };
    await page.goto("/administration/utilisateurs");
    await page.getByRole("link", { name: `${L.gererAcces} ${L.gererAccesDe} ${vise.nom}` }).first().click();
    await pret(page);
    await ouvrir();
    await expect(page.getByRole("radio", { name: `${TEXTES.roles.associe} — ${D.associe}. ${R.roleActuel}` })).toBeChecked();
    await verifierAccessibilite(page);
    await sansDefilementHorizontal(page);

    await page.getByRole("button", { name: R.enregistrer }).click();
    await expect(page.getByRole("status")).toContainText(`Aucun changement : ${vise.nom} a déjà le rôle Associé.`);

    await ouvrir();
    await option("operateur").check();
    await page.getByRole("button", { name: R.enregistrer }).click();
    await expect(page.getByRole("status")).toContainText(`Rôle de ${vise.nom} changé : Opérateur (auparavant Associé).`);
    await expect(contenu(page).getByText("Rôle : Opérateur")).toBeVisible();

    await ouvrir();
    await option("gerant").check();
    await page.getByRole("button", { name: R.enregistrer }).click();
    const boite = page.getByRole("dialog", { name: `Donner le rôle de gérant à ${vise.nom} ?` });
    await expect(boite.getByRole("button", { name: R.annuler })).toBeFocused();
    await verifierAccessibilite(page);
    await boite.getByRole("button", { name: R.donnerGerant.bouton }).click();
    await expect(page.getByRole("status")).toContainText(`Rôle de ${vise.nom} changé : Gérant (auparavant Opérateur).`);

    await ouvrir();
    await option("associe").check();
    await page.getByRole("button", { name: R.enregistrer }).click();
    await expect(page.getByRole("status")).toContainText(`Rôle de ${vise.nom} changé : Associé (auparavant Gérant).`);
  });
});

test.describe("Administration › Utilisateurs, gérant qui quitte son rôle", () => {
  test("quitter soi-même le rôle de gérant : confirmation, puis l'accueil sans « Administration » (6.4, A8)", async ({
    page,
  }, infos) => {
    const moi = compteVise("quitte", infos.project.name);
    await seConnecter(page, moi.email, moi.secret);
    await page.goto("/administration/utilisateurs");
    await page.getByRole("link", { name: `${L.gererAcces} ${L.gererAccesDe} ${moi.nom}` }).first().click();
    await pret(page);
    await page.getByRole("link", { name: F.changerRole }).click();
    await pret(page);
    await page.getByRole("radio", { name: new RegExp(`^${TEXTES.roles.associe} — `) }).check();
    await page.getByRole("button", { name: R.enregistrer }).click();
    const boite = page.getByRole("dialog", { name: R.quitterGerant.question });
    await expect(boite).toContainText(R.quitterGerant.explication);
    await boite.getByRole("button", { name: R.quitterGerant.bouton }).click();
    await attendreAdresse(page, /\/\?motif=role_quitte$/);
    await expect(page.getByRole("status")).toContainText(
      "Votre rôle est maintenant Associé. L'Administration n'est plus accessible depuis ce compte.",
    );
    await expect(page.getByText(`${moi.nom} · ${TEXTES.cadre.role} ${TEXTES.roles.associe}`)).toBeVisible();
    const menu = page.getByRole("navigation", { name: TEXTES.cadre.menuPrincipal });
    await expect(menu.getByRole("link", { name: TEXTES.cadre.administration })).toHaveCount(0);
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
    await expect(contenu(page).getByText(TEXTES.reservee.reservee)).toBeVisible();
    await expect(page.getByRole("table")).toHaveCount(0);
    await verifierAccessibilite(page);
    await page.getByRole("link", { name: TEXTES.retourAccueil }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(TEXTES.accueil.titre);
  });
});
