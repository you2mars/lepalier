import { afterEach, describe, expect, it, vi } from "vitest";
import { reprendreSession } from "./navigation";

// Un 401 sur une écriture, dans le navigateur : identity dit, par nginx 443, si la session a été coupée par une
// suspension (ADR 0006) ; puis Se connecter avec le bon bandeau et la page en cours.
const remplacer = vi.fn();

function reponse(statut: number, corps: unknown): Response {
  return new Response(JSON.stringify(corps), { status: statut, headers: { "Content-Type": "application/json" } });
}

afterEach(() => {
  vi.unstubAllGlobals();
  remplacer.mockReset();
});

describe("reprendreSession", () => {
  it.each([
    [{ code: "compte_suspendu" }, "compte_suspendu"],
    [{ code: "session_expiree" }, "session_expiree"],
  ])("réponse %o : Se connecter avec le motif %s et la page en cours", async (corps, motif) => {
    const appel = vi.fn().mockResolvedValue(reponse(200, corps));
    vi.stubGlobal("fetch", appel);
    window.history.replaceState(null, "", "/administration/utilisateurs/inviter");
    await reprendreSession(remplacer);
    expect(appel.mock.calls[0]![0]).toBe("/api/identity/auth/etat-session");
    expect(remplacer).toHaveBeenCalledWith(
      `/connexion?motif=${motif}&retour=%2Fadministration%2Futilisateurs%2Finviter`,
    );
  });

  it("panne : session expirée", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    window.history.replaceState(null, "", "/");
    await reprendreSession(remplacer);
    expect(remplacer).toHaveBeenCalledWith("/connexion?motif=session_expiree");
  });
});
