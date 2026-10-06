import { afterEach, describe, expect, it, vi } from "vitest";
import { TEXTES } from "@/textes";
import { envoyer } from "./api";

function reponse(statut: number, corps: unknown, type = "application/json"): Response {
  return new Response(typeof corps === "string" ? corps : JSON.stringify(corps), {
    status: statut,
    headers: { "Content-Type": type },
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("envoyer (écritures depuis le navigateur, via nginx)", () => {
  it("POST JSON vers /api/<service>, cookies du même site, sans clé d'idempotence par défaut", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(200, { etape: "code" }));
    vi.stubGlobal("fetch", appel);
    const resultat = await envoyer("/identity/auth/connexion", { email: "a@b.fr" });
    expect(resultat).toEqual({ ok: true, statut: 200, donnees: { etape: "code" } });
    const [url, options] = appel.mock.calls[0]!;
    expect(url).toBe("/api/identity/auth/connexion");
    expect(options.method).toBe("POST");
    expect(options.credentials).toBe("same-origin");
    expect(options.headers["Content-Type"]).toBe("application/json");
    expect(options.headers["Idempotency-Key"]).toBeUndefined();
    expect(JSON.parse(options.body)).toEqual({ email: "a@b.fr" });
  });

  it("clé d'idempotence fournie par le formulaire (UX-22)", async () => {
    const appel = vi.fn().mockResolvedValue(reponse(201, { id: "x" }));
    vi.stubGlobal("fetch", appel);
    await envoyer("/identity/utilisateurs/inviter", {}, { cleIdempotence: "0192f3a4-5b6c-7d8e-9f01-234567890c00" });
    expect(appel.mock.calls[0]![1].headers["Idempotency-Key"]).toBe("0192f3a4-5b6c-7d8e-9f01-234567890c00");
  });

  it("réponse sans corps (204)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    expect(await envoyer("/identity/auth/deconnexion", {})).toEqual({ ok: true, statut: 204, donnees: null });
  });

  it("erreur au format de commun : message et messages par champ", async () => {
    const corps = {
      code: "identifiants_incorrects",
      message: "Message général.",
      details: { champs: [{ champ: "mot_de_passe", message: "Message du champ." }] },
      trace_id: "t",
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(401, corps)));
    expect(await envoyer("/identity/auth/connexion", {})).toEqual({
      ok: false,
      statut: 401,
      erreur: { code: "identifiants_incorrects", message: "Message général.", champs: { mot_de_passe: "Message du champ." } },
    });
  });

  it("erreur sans corps JSON (502 de nginx) ou panne réseau : message d'erreur inattendue de commun", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reponse(502, "<html>", "text/html")));
    const attendu = { code: "inattendue", message: TEXTES.commun.erreurInattendue, champs: {} };
    expect(await envoyer("/identity/auth/connexion", {})).toEqual({ ok: false, statut: 502, erreur: attendu });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    expect(await envoyer("/identity/auth/connexion", {})).toEqual({ ok: false, statut: 0, erreur: attendu });
  });
});
