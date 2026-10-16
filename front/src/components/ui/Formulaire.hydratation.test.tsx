import { act, Suspense, useState } from "react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import { Formulaire } from "./Formulaire";

// Constat UX (18) : sur un téléphone lent, la personne tape avant la prise en main du formulaire par React ; les
// champs restent affichés remplis, mais l'état de React les croyait vides (connexion envoyée avec une adresse vide,
// invitation refusée puis vidée).
let vu: { adresse: string; motDePasse: string } = { adresse: "", motDePasse: "" };

function Ecran() {
  const [adresse, setAdresse] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  vu = { adresse, motDePasse };
  return (
    <Formulaire onSubmit={() => {}}>
      <input id="adresse" type="email" value={adresse} onChange={(e) => setAdresse(e.target.value)} />
      <input id="mdp" type="password" value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)} />
      <input id="cache" type="hidden" value="fixe" readOnly />
    </Formulaire>
  );
}

// comme une page arrivée en flux : le formulaire dans une limite Suspense
function Page() {
  return (
    <Suspense fallback={<p>Chargement</p>}>
      <Ecran />
    </Suspense>
  );
}

afterEach(() => {
  document.body.innerHTML = "";
  vu = { adresse: "", motDePasse: "" };
});

async function hydrater(avant: (conteneur: HTMLElement) => void): Promise<HTMLElement> {
  const conteneur = document.createElement("div");
  conteneur.innerHTML = renderToString(<Page />);
  document.body.append(conteneur);
  avant(conteneur);
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  await act(async () => {
    hydrateRoot(conteneur, <Page />);
  });
  return conteneur;
}

const champ = (conteneur: HTMLElement, id: string) => conteneur.querySelector<HTMLInputElement>(`#${id}`)!;

describe("Formulaire : prise en main (constat UX (18))", () => {
  it("avant la prise en main : pas de data-pret", () => {
    const conteneur = document.createElement("div");
    conteneur.innerHTML = renderToString(<Page />);
    expect(conteneur.querySelector("form")?.hasAttribute("data-pret")).toBe(false);
  });

  it("saisies faites avant : reprises par React, champs inchangés, puis data-pret", async () => {
    const conteneur = await hydrater((c) => {
      champ(c, "adresse").value = "marie.durand@exemple.fr";
      champ(c, "mdp").value = "le chat dort sur le toit";
    });
    expect(vu).toEqual({ adresse: "marie.durand@exemple.fr", motDePasse: "le chat dort sur le toit" });
    expect(champ(conteneur, "adresse").value).toBe("marie.durand@exemple.fr");
    expect(champ(conteneur, "cache").value).toBe("fixe");
    expect(conteneur.querySelector("form")?.hasAttribute("data-pret")).toBe(true);
  });

  it("rien de saisi : état et champs vides, data-pret", async () => {
    const conteneur = await hydrater(() => {});
    expect(vu).toEqual({ adresse: "", motDePasse: "" });
    expect(conteneur.querySelector("form")?.hasAttribute("data-pret")).toBe(true);
  });
});
