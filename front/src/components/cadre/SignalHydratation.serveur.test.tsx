// @vitest-environment node
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

// rendu côté serveur, sans document ni HTMLInputElement : ces modules ne doivent rien lire du navigateur au
// chargement (le front ne démarrait plus, 16 octobre 2026)
describe("rendu côté serveur, sans objet du navigateur", () => {
  it("SignalHydratation et Formulaire chargés et rendus", async () => {
    const { SignalHydratation } = await import("./SignalHydratation");
    const { Formulaire } = await import("../ui/Formulaire");
    expect(renderToString(<SignalHydratation />)).toBe("");
    expect(renderToString(<Formulaire onSubmit={() => {}}>contenu</Formulaire>)).toContain("<form");
  });
});
