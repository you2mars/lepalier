// Liste en tableau (UX-26) : tableau nommé sur ordinateur (7 colonnes au plus) ; sur mobile et sous 48 rem de
// largeur utile, une carte par ligne (3 informations au plus), dont la carte entière est le lien vers le détail ; tout
// le contenu de la carte est lu, précédé d'un début masqué à l'écran (« Gérer l'accès de »).
import { Fragment, type ReactNode } from "react";
import { TexteMasque } from "./TexteMasque";

export type Colonne = { titre: string; masque?: boolean };
export type Ligne = {
  cle: string;
  cellules: ReactNode[];
  carte: { href: string; prefixeMasque: string; contenu: ReactNode[] };
};

export function TableauResponsive({
  libelle,
  colonnes,
  lignes,
}: {
  libelle: string;
  colonnes: Colonne[];
  lignes: Ligne[];
}) {
  return (
    <>
      <table className="tableau" aria-label={libelle}>
        <thead>
          <tr>
            {colonnes.map((c) => (
              <th key={c.titre} scope="col">
                {c.masque ? <TexteMasque>{c.titre}</TexteMasque> : c.titre}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lignes.map((ligne) => (
            <tr key={ligne.cle}>
              {ligne.cellules.map((cellule, i) => (
                <td key={colonnes[i]?.titre ?? i}>{cellule}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="cartes" aria-label={libelle}>
        {lignes.map((ligne) => (
          <li key={ligne.cle}>
            <a className="carte" href={ligne.carte.href}>
              {/* espaces entre les parties : sans eux, le nom lu les collerait ; sans effet sur l'affichage (flex) */}
              <TexteMasque>{ligne.carte.prefixeMasque}</TexteMasque>{" "}
              {ligne.carte.contenu.map((element, i) => (
                <Fragment key={i}>
                  <span className="carte-ligne">{element}</span>{" "}
                </Fragment>
              ))}
            </a>
          </li>
        ))}
      </ul>
    </>
  );
}
