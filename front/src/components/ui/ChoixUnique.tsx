// Choix unique (boutons radio) : groupe nommé par sa légende, un libellé par choix, cible de 44 px (UX-8, UX-17).
export type Choix = { valeur: string; libelle: string };

export function ChoixUnique({
  nom,
  legende,
  choix,
  valeur,
  surChoix,
}: {
  nom: string;
  legende: string;
  choix: Choix[];
  valeur: string;
  surChoix: (valeur: string) => void;
}) {
  return (
    <fieldset className="choix-unique">
      <legend>{legende}</legend>
      {choix.map((c) => {
        const id = `${nom}-${c.valeur}`;
        return (
          <label key={c.valeur} htmlFor={id}>
            <input
              id={id}
              type="radio"
              name={nom}
              value={c.valeur}
              checked={valeur === c.valeur}
              onChange={() => surChoix(c.valeur)}
            />
            <span>{c.libelle}</span>
          </label>
        );
      })}
    </fieldset>
  );
}
