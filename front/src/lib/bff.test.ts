import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { lire, motifSession } from "./bff";

// Lectures du BFF (front côté serveur) par l'écoute interne de nginx (8081) : cookie de session relayé, jamais
// mis en cache ; une panne devient un résultat, jamais une exception (dégradation par bloc, UX-30).
function reponse(statut: number, corps: unknown): Response {
  return new Response(JSON.stringify(corps), { status: statut, headers: { "Content-Type": "application/json" } });
}

beforeEach(() => vi.stubEnv("LEPALIER_BFF", "http://nginx:8081"));
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("lire", () => {
  it("GET vers l'écoute interne, seul le cookie de session relayé, sans cache", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(200, { id: "1" }));
    vi.stubGlobal("fetch", appel);
    expect(await lire("/identity/moi", "jeton-de-session")).toEqual({ ok: true, statut: 200, donnees: { id: "1" } });
    const [adresse, options] = appel.mock.calls[0] as [string, RequestInit];
    expect(adresse).toBe("http://nginx:8081/api/identity/moi");
    expect(options.method ?? "GET").toBe("GET");
    expect(options.cache).toBe("no-store");
    expect(options.headers).toEqual({ Cookie: "lp_session=jeton-de-session" });
  });

  it("sans cookie : aucun en-tête Cookie", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(401, { code: "unauthenticated" }));
    vi.stubGlobal("fetch", appel);
    expect(await lire("/identity/moi", undefined)).toEqual({ ok: false, statut: 401 });
    expect((appel.mock.calls[0] as [string, RequestInit])[1].headers).toEqual({});
  });

  it("service en panne ou injoignable : statut, jamais d'exception", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(502, { code: "unavailable" })));
    expect(await lire("/identity/moi", "j")).toEqual({ ok: false, statut: 502 });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));
    expect(await lire("/identity/moi", "j")).toEqual({ ok: false, statut: 0 });
  });

  it("service qui ne répond pas : abandon après le délai, traité comme une panne", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_: string, options: RequestInit) =>
          new Promise((_resolu, rejete) => options.signal?.addEventListener("abort", () => rejete(options.signal?.reason))),
      ),
    );
    expect(await lire("/identity/moi", "j", { delaiMs: 20 })).toEqual({ ok: false, statut: 0 });
  });

  it("délai par défaut : 5 secondes", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(200, {}));
    vi.stubGlobal("fetch", appel);
    const delai = vi.spyOn(AbortSignal, "timeout");
    await lire("/identity/moi", "j");
    expect(delai).toHaveBeenCalledWith(5000);
    expect((appel.mock.calls[0] as [string, RequestInit])[1].signal).toBeInstanceOf(AbortSignal);
  });

  it("réponse illisible : traitée comme une panne", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>", { status: 200 })));
    expect(await lire("/identity/moi", "j")).toEqual({ ok: false, statut: 0 });
  });
});

describe("motifSession (après un 401)", () => {
  it("accès suspendu : compte_suspendu, demandé à etat-session avec le cookie", async () => {
    const appel = vi
      .fn()
      .mockResolvedValue(reponse(200, { code: "compte_suspendu", message: "Votre accès a été suspendu." }));
    vi.stubGlobal("fetch", appel);
    expect(await motifSession("j")).toBe("compte_suspendu");
    expect(appel.mock.calls[0]![0]).toBe("http://nginx:8081/api/identity/auth/etat-session");
  });

  it.each([
    ["réponse « session expirée »", reponse(200, { code: "session_expiree", message: "…" })],
    ["code inconnu", reponse(200, { code: "autre" })],
    ["panne", reponse(502, {})],
  ])("%s : session_expiree", async (_, r) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(r));
    expect(await motifSession("j")).toBe("session_expiree");
  });
});
