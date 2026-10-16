import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { lireConnecte, personneConnectee, personneSiConnectee } from "./session";

// Personne connectée, lue par le BFF dans /moi (identity) ; après un 401, retour à Se connecter avec le bon
// bandeau (etat-session) et la page demandée (maquettes v3, § 0.3).
const cookies = new Map<string, string>();
let chemin: string | null = "/administration/utilisateurs";
vi.mock("next/headers", () => ({
  cookies: async () => ({ get: (nom: string) => (cookies.has(nom) ? { value: cookies.get(nom) } : undefined) }),
  headers: async () => ({ get: (nom: string) => (nom === "x-lepalier-chemin" ? chemin : null) }),
}));
vi.mock("next/navigation", () => ({
  redirect: (adresse: string) => {
    throw new Error(`redirection ${adresse}`);
  },
}));

const MOI = { id: "0192", email: "marie.durand@exemple.fr", nom_affiche: "Mme Durand", role: "associe" };

function reponse(statut: number, corps: unknown): Response {
  return new Response(JSON.stringify(corps), { status: statut, headers: { "Content-Type": "application/json" } });
}

// réponses par adresse appelée sur l'écoute interne
function api(reponses: Record<string, Response>) {
  const appel = vi.fn((adresse: string) => Promise.resolve(reponses[adresse.replace("http://nginx:8081", "")]!));
  vi.stubGlobal("fetch", appel);
  return appel;
}

beforeEach(() => {
  vi.stubEnv("LEPALIER_BFF", "http://nginx:8081");
  cookies.clear();
  cookies.set("lp_session", "jeton");
  chemin = "/administration/utilisateurs";
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("personneConnectee", () => {
  it("session valide : nom affiché, rôle et adresse lus dans /moi", async () => {
    api({ "/api/identity/moi": reponse(200, MOI) });
    expect(await personneConnectee()).toEqual(MOI);
  });

  it("aucun cookie de session (première visite) : Se connecter sans message, page demandée gardée", async () => {
    cookies.clear();
    const appel = api({});
    await expect(personneConnectee()).rejects.toThrow(
      "redirection /connexion?retour=%2Fadministration%2Futilisateurs",
    );
    expect(appel).not.toHaveBeenCalled();
  });

  it("401 : session expirée, Se connecter avec le bandeau et la page demandée", async () => {
    api({
      "/api/identity/moi": reponse(401, { code: "unauthenticated" }),
      "/api/identity/auth/etat-session": reponse(200, { code: "session_expiree" }),
    });
    await expect(personneConnectee()).rejects.toThrow(
      "redirection /connexion?motif=session_expiree&retour=%2Fadministration%2Futilisateurs",
    );
  });

  it("401 après une suspension : bandeau « accès suspendu » (R0-07)", async () => {
    chemin = "/";
    api({
      "/api/identity/moi": reponse(401, { code: "unauthenticated" }),
      "/api/identity/auth/etat-session": reponse(200, { code: "compte_suspendu" }),
    });
    await expect(personneConnectee()).rejects.toThrow("redirection /connexion?motif=compte_suspendu");
  });

  it("chemin demandé absent ou extérieur : jamais transmis", async () => {
    chemin = "//pirate.example";
    api({
      "/api/identity/moi": reponse(401, {}),
      "/api/identity/auth/etat-session": reponse(200, { code: "session_expiree" }),
    });
    await expect(personneConnectee()).rejects.toThrow(/^redirection \/connexion\?motif=session_expiree$/);
  });

  it("identity en panne : null (information momentanément indisponible), pas de déconnexion", async () => {
    api({ "/api/identity/moi": reponse(502, {}) });
    expect(await personneConnectee()).toBeNull();
  });

  it("503 au format commun de nginx (base d'identity arrêtée) : null comme pour un 502", async () => {
    api({ "/api/identity/moi": reponse(503, { code: "service_indisponible" }) });
    expect(await personneConnectee()).toBeNull();
  });
});

describe("lireConnecte (lectures d'un écran connecté)", () => {
  it("lecture réussie : données", async () => {
    api({ "/api/identity/utilisateurs": reponse(200, { utilisateurs: [] }) });
    expect(await lireConnecte("/identity/utilisateurs")).toEqual({ ok: true, statut: 200, donnees: { utilisateurs: [] } });
  });

  it("403 (réservé au gérant) et pannes : rendus à l'écran, qui choisit quoi afficher", async () => {
    api({ "/api/identity/utilisateurs": reponse(403, { code: "forbidden" }) });
    expect(await lireConnecte("/identity/utilisateurs")).toEqual({ ok: false, statut: 403 });
    api({ "/api/identity/utilisateurs": reponse(502, {}) });
    expect(await lireConnecte("/identity/utilisateurs")).toEqual({ ok: false, statut: 502 });
  });

  it("401 en cours de navigation : Se connecter avec le bon bandeau et la page demandée", async () => {
    api({
      "/api/identity/utilisateurs": reponse(401, {}),
      "/api/identity/auth/etat-session": reponse(200, { code: "compte_suspendu" }),
    });
    await expect(lireConnecte("/identity/utilisateurs")).rejects.toThrow(
      "redirection /connexion?motif=compte_suspendu&retour=%2Fadministration%2Futilisateurs",
    );
  });

  it("sans cookie de session : Se connecter sans message, aucun appel", async () => {
    cookies.clear();
    const appel = api({});
    await expect(lireConnecte("/identity/utilisateurs")).rejects.toThrow(
      "redirection /connexion?retour=%2Fadministration%2Futilisateurs",
    );
    expect(appel).not.toHaveBeenCalled();
  });
});

describe("personneSiConnectee (page introuvable : jamais de redirection)", () => {
  it("session valide : la personne", async () => {
    api({ "/api/identity/moi": reponse(200, MOI) });
    expect(await personneSiConnectee()).toEqual(MOI);
  });

  it("sans cookie : null, aucun appel", async () => {
    cookies.clear();
    const appel = api({});
    expect(await personneSiConnectee()).toBeNull();
    expect(appel).not.toHaveBeenCalled();
  });

  it.each([401, 503])("refus %i : null, sans redirection vers Se connecter", async (statut) => {
    api({ "/api/identity/moi": reponse(statut, {}) });
    expect(await personneSiConnectee()).toBeNull();
  });
});
