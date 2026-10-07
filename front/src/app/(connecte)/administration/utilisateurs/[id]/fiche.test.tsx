import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MessageFlashProvider } from "@/components/cadre/MessageFlash";
import { dateEnToutesLettres } from "@/lib/format";
import { libelle } from "@/lib/libelles";
import type { Personne } from "@/lib/session";
import { TEXTES } from "@/textes";
import { type Fiche, GestionAcces } from "./GestionAcces";
import Page, { generateMetadata } from "./page";

const F = TEXTES.utilisateurs.fiche;
const pousser = vi.fn();
const rafraichir = vi.fn();
const reprendreSession = vi.fn();
const lireConnecte = vi.fn();
const introuvable = vi.fn(() => {
  throw new Error("introuvable");
});
const GERANT: Personne = { id: "g", email: "gerant@exemple.fr", nom_affiche: "M. Martin", role: "gerant" };
let personne: Personne | null = GERANT;
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pousser, refresh: rafraichir }),
  usePathname: () => "/administration/utilisateurs/0192-b",
  notFound: () => introuvable(),
}));
vi.mock("@/lib/navigation", () => ({ reprendreSession: () => reprendreSession() }));
vi.mock("@/lib/session", () => ({
  personneConnectee: async () => personne,
  lireConnecte: (chemin: string) => lireConnecte(chemin),
}));

const ACTIF: Fiche = {
  id: "0192-b",
  email: "marie.durand@exemple.fr",
  nom_affiche: "Mme Durand",
  role: "associe",
  statut: "actif",
  statut_libelle: "Accès actif",
  invitation_envoyee_le: null,
  invitation_expire_le: null,
};
const SUSPENDU: Fiche = { ...ACTIF, statut: "suspendu", statut_libelle: "Accès suspendu" };
const INVITE: Fiche = {
  ...ACTIF,
  statut: "invite",
  statut_libelle: "Invitation envoyée",
  invitation_envoyee_le: "2026-10-03T08:00:00+00:00",
  invitation_expire_le: "2026-10-10T08:00:00+00:00",
};
const EXPIRE: Fiche = {
  ...INVITE,
  statut_libelle: libelle("statut.invitation_expiree"),
  invitation_envoyee_le: "2026-09-20T08:00:00+00:00",
  invitation_expire_le: "2026-09-27T08:00:00+00:00",
};

function reponse(statut: number, corps: unknown = null): Response {
  return corps === null
    ? new Response(null, { status: statut })
    : new Response(JSON.stringify(corps), { status: statut, headers: { "Content-Type": "application/json" } });
}

function refus(statut: number, code: string, message: string): Response {
  return reponse(statut, { code, message, details: {}, trace_id: "t" });
}

function afficher(fiche: Fiche, estMoi = false) {
  return render(
    <MessageFlashProvider>
      <GestionAcces fiche={fiche} estMoi={estMoi} />
    </MessageFlashProvider>,
  );
}

const bouton = (nom: string) => screen.getByRole("button", { name: nom });
const boutons = () => screen.queryAllByRole("button").map((b) => b.textContent);

beforeEach(() => {
  personne = GERANT;
  pousser.mockReset();
  rafraichir.mockReset();
  reprendreSession.mockReset();
  lireConnecte.mockReset();
  lireConnecte.mockResolvedValue({ ok: true, statut: 200, donnees: ACTIF });
});
afterEach(() => vi.unstubAllGlobals());

describe("Gérer l'accès : page (maquettes v3, écran 6.3)", () => {
  it("titre « Accès de {nom} », onglet, fil d'Ariane avec lien vers la liste, fiche lue chez identity", async () => {
    const parametres = { params: Promise.resolve({ id: "0192-b" }) };
    render(await Page(parametres));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Accès de Mme Durand");
    expect((await generateMetadata(parametres)).title).toBe("Accès de Mme Durand — LePalier");
    const fil = screen.getByRole("navigation", { name: TEXTES.cadre.filAriane });
    expect(within(fil).getAllByRole("listitem").map((e) => e.textContent)).toEqual([
      TEXTES.cadre.administration,
      TEXTES.utilisateurs.liste.titre,
      "Mme Durand",
    ]);
    expect(lireConnecte).toHaveBeenCalledWith("/identity/utilisateurs/0192-b");
  });

  it("personne inconnue ou invitation annulée (404) : page introuvable", async () => {
    lireConnecte.mockResolvedValue({ ok: false, statut: 404 });
    await expect(Page({ params: Promise.resolve({ id: "x" }) })).rejects.toThrow("introuvable");
  });

  it("associé : page réservée au gérant, sans lecture", async () => {
    personne = { ...GERANT, role: "associe" };
    render(await Page({ params: Promise.resolve({ id: "0192-b" }) }));
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(TEXTES.reservee.titre);
    expect(lireConnecte).not.toHaveBeenCalled();
  });

  it("identity en panne : « Information momentanément indisponible »", async () => {
    lireConnecte.mockResolvedValue({ ok: false, statut: 502 });
    render(await Page({ params: Promise.resolve({ id: "0192-b" }) }));
    expect(screen.getByText(TEXTES.indisponible)).toBeInTheDocument();
  });
});

describe("Gérer l'accès : fiche", () => {
  it("adresse, rôle en mots du lexique avec « Changer le rôle », statut en mots d'identity", () => {
    afficher(ACTIF);
    expect(screen.getByText("Adresse e-mail : marie.durand@exemple.fr")).toBeInTheDocument();
    expect(screen.getByText("Rôle : Associé")).toBeInTheDocument();
    expect(screen.getByText("Statut : Accès actif")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: F.changerRole })).toHaveAttribute(
      "href",
      "/administration/utilisateurs/0192-b/role",
    );
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(F.actions);
  });

  it("invitation en cours : date d'envoi et fin de validité en toutes lettres (Q6)", () => {
    afficher(INVITE);
    expect(
      screen.getByText(
        `Invitation envoyée le ${dateEnToutesLettres(INVITE.invitation_envoyee_le!)}, valable jusqu'au ${dateEnToutesLettres(INVITE.invitation_expire_le!)}.`,
      ),
    ).toBeInTheDocument();
  });

  it("invitation expirée : date de fin passée et ce qu'il faut faire (A6)", () => {
    afficher(EXPIRE);
    expect(
      screen.getByText(
        `Invitation envoyée le ${dateEnToutesLettres(EXPIRE.invitation_envoyee_le!)} ; le lien a expiré le ${dateEnToutesLettres(EXPIRE.invitation_expire_le!)}. Pour en envoyer un nouveau, touchez « Renvoyer l'invitation ».`,
      ),
    ).toBeInTheDocument();
  });

  it.each([
    ["actif", ACTIF, false, [F.suspendre.bouton, F.reinitialiser.bouton]],
    ["suspendu", SUSPENDU, false, [F.reactiver.bouton]],
    ["invité", INVITE, false, [F.renvoyer.bouton, F.annulerInvitation.bouton]],
    ["sa propre fiche", ACTIF, true, []],
  ] as const)("actions selon le statut : %s", (_, fiche, estMoi, attendus) => {
    afficher(fiche, estMoi);
    expect(boutons()).toEqual(attendus);
  });

  it("sa propre fiche : la phrase qui explique, à la place de « Suspendre » et « Réinitialiser »", () => {
    afficher(ACTIF, true);
    expect(screen.getByText(F.soiMeme)).toBeInTheDocument();
  });
});

describe("Gérer l'accès : actions avec confirmation (UX-3)", () => {
  it("suspendre : confirmation au neutre, focus sur « Annuler » ; « Annuler » ne fait rien", async () => {
    const appel = vi.fn();
    vi.stubGlobal("fetch", appel);
    afficher(ACTIF);
    await userEvent.click(bouton(F.suspendre.bouton));
    const boite = screen.getByRole("dialog", { name: "Suspendre l'accès de Mme Durand ?" });
    expect(boite).toHaveTextContent(F.suspendre.explication);
    expect(within(boite).getByRole("button", { name: F.annuler })).toHaveFocus();
    await userEvent.click(within(boite).getByRole("button", { name: F.annuler }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(appel).not.toHaveBeenCalled();
  });

  it("suspendre confirmé : PATCH statut suspendu avec clé d'idempotence ; bandeau « Fait » ; fiche relue", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(200, { ...SUSPENDU }));
    vi.stubGlobal("fetch", appel);
    afficher(ACTIF);
    await userEvent.click(bouton(F.suspendre.bouton));
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: F.suspendre.bouton }));
    const message = await screen.findByRole("status");
    expect(message).toHaveTextContent("Accès de Mme Durand suspendu.");
    const [chemin, options] = appel.mock.calls[0] as [string, RequestInit];
    expect(chemin).toBe("/api/identity/utilisateurs/0192-b");
    expect(options.method).toBe("PATCH");
    expect(JSON.parse(options.body as string)).toEqual({ statut: "suspendu" });
    expect((options.headers as Record<string, string>)["Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(rafraichir).toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("réinitialiser : confirmation sans date (la date exacte vient d'identity dans la fiche relue) ; POST reinitialiser-acces", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(202));
    vi.stubGlobal("fetch", appel);
    afficher(ACTIF);
    await userEvent.click(bouton(F.reinitialiser.bouton));
    const boite = screen.getByRole("dialog", { name: "Réinitialiser l'accès de Mme Durand ?" });
    expect(boite).toHaveTextContent(
      "Le mot de passe, les codes de secours et l'application d'authentification de ce compte ne fonctionneront plus. Un e-mail avec un nouveau lien, valable 7 jours, sera envoyé à marie.durand@exemple.fr.",
    );
    expect(boite).not.toHaveTextContent(/jusqu'au/);
    await userEvent.click(within(boite).getByRole("button", { name: F.reinitialiser.bouton }));
    expect(await screen.findByRole("status")).toHaveTextContent("Accès de Mme Durand réinitialisé ; un e-mail lui a été envoyé.");
    expect(appel.mock.calls[0]![0]).toBe("/api/identity/utilisateurs/0192-b/reinitialiser-acces");
  });

  it("annuler l'invitation : « Garder l'invitation » en premier ; confirmé, retour à la liste qui dit ce qui a été fait", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(204));
    vi.stubGlobal("fetch", appel);
    afficher(INVITE);
    await userEvent.click(bouton(F.annulerInvitation.bouton));
    const boite = screen.getByRole("dialog", { name: "Annuler l'invitation de Mme Durand ?" });
    expect(boite).toHaveTextContent(
      "Le lien envoyé à marie.durand@exemple.fr ne fonctionnera plus et cette personne disparaîtra de la liste.",
    );
    expect(within(boite).getByRole("button", { name: F.annulerInvitation.garder })).toHaveFocus();
    await userEvent.click(within(boite).getByRole("button", { name: F.annulerInvitation.bouton }));
    await waitFor(() => expect(pousser).toHaveBeenCalledWith("/administration/utilisateurs"));
    expect(appel.mock.calls[0]![0]).toBe("/api/identity/utilisateurs/0192-b/annuler-invitation");
  });
});

describe("Gérer l'accès : actions sans confirmation (réversibles)", () => {
  it("réactiver : PATCH statut actif ; bandeau « Fait »", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(200, { ...ACTIF }));
    vi.stubGlobal("fetch", appel);
    afficher(SUSPENDU);
    await userEvent.click(bouton(F.reactiver.bouton));
    expect(await screen.findByRole("status")).toHaveTextContent("Accès de Mme Durand réactivé.");
    expect(JSON.parse((appel.mock.calls[0] as [string, RequestInit])[1].body as string)).toEqual({ statut: "actif" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renvoyer l'invitation : POST renvoyer-invitation ; bandeau « Fait »", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(202));
    vi.stubGlobal("fetch", appel);
    afficher(EXPIRE);
    await userEvent.click(bouton(F.renvoyer.bouton));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Invitation renvoyée à Mme Durand (marie.durand@exemple.fr). Le nouveau lien est valable 7 jours ; l'ancien ne fonctionne plus.",
    );
    expect(appel.mock.calls[0]![0]).toBe("/api/identity/utilisateurs/0192-b/renvoyer-invitation");
  });
});

describe("Gérer l'accès : fiche relue après une action", () => {
  it("jusqu'à l'arrivée de la fiche relue, aucune autre action ne part (sinon la relecture pourrait défaire la suivante)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(202)));
    const { rerender } = afficher(INVITE);
    await userEvent.click(bouton(F.renvoyer.bouton));
    await screen.findByRole("status");
    expect(rafraichir).toHaveBeenCalled();
    expect(bouton(F.annulerInvitation.bouton)).toBeDisabled();
    expect(bouton(F.renvoyer.bouton)).toBeDisabled();
    // fiche relue par le serveur : nouvel objet, actions de nouveau possibles
    rerender(
      <MessageFlashProvider>
        <GestionAcces fiche={{ ...INVITE }} estMoi={false} />
      </MessageFlashProvider>,
    );
    expect(bouton(F.annulerInvitation.bouton)).toBeEnabled();
  });

  it("relecture qui n'arrive pas : actions de nouveau possibles après 5 secondes", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(202)));
    afficher(INVITE);
    await userEvent.click(bouton(F.renvoyer.bouton));
    await screen.findByRole("status");
    expect(bouton(F.renvoyer.bouton)).toBeDisabled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(bouton(F.renvoyer.bouton)).toBeEnabled();
    vi.useRealTimers();
  });
});

describe("Gérer l'accès : refus et pannes", () => {
  it.each([
    ["utilisateurs.dernier_gerant", "dernier_gerant"],
    ["utilisateurs.compte_non_active", "compte_non_active"],
    ["invitation.deja_activee", "deja_activee"],
  ] as const)("refus d'identity (%s) : bandeau « Attention » avec son message, fiche relue", async (cle, code) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(refus(409, code, libelle(cle))));
    afficher(SUSPENDU);
    await userEvent.click(bouton(F.reactiver.bouton));
    const bandeau = await screen.findByRole("alert");
    expect(bandeau).toHaveTextContent(TEXTES.etats.attention);
    expect(bandeau).toHaveTextContent(libelle(cle));
    expect(rafraichir).toHaveBeenCalled();
  });

  it("401 : reprise de session", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(refus(401, "unauthenticated", "x")));
    afficher(SUSPENDU);
    await userEvent.click(bouton(F.reactiver.bouton));
    await waitFor(() => expect(reprendreSession).toHaveBeenCalledOnce());
  });

  it("panne : bandeau « Erreur » avec le message de commun", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    afficher(SUSPENDU);
    await userEvent.click(bouton(F.reactiver.bouton));
    const bandeau = await screen.findByRole("alert");
    expect(bandeau).toHaveTextContent(TEXTES.etats.erreur);
    expect(bandeau).toHaveTextContent(TEXTES.commun.erreurInattendue);
  });

  it("pendant l'envoi : le bouton de l'action est désactivé, « Envoi en cours… » (UX-22)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => undefined)));
    afficher(SUSPENDU);
    await userEvent.click(bouton(F.reactiver.bouton));
    expect(screen.getByRole("button", { name: TEXTES.envoiEnCours })).toBeDisabled();
  });
});
