// Fil d'Ariane des pages profondes (UX-9) : navigation nommée ; lien seulement vers une page qui existe ; la page en
// cours est signalée (aria-current) et n'est pas un lien.
import { TEXTES } from "@/textes";

export type Etape = { libelle: string; href?: string };

export function FilAriane({ etapes }: { etapes: Etape[] }) {
  return (
    <nav className="fil-ariane" aria-label={TEXTES.cadre.filAriane}>
      <ol>
        {etapes.map((etape, i) => {
          const courante = i === etapes.length - 1;
          return (
            <li key={etape.libelle}>
              {courante ? (
                <span aria-current="page">{etape.libelle}</span>
              ) : etape.href ? (
                <a href={etape.href}>{etape.libelle}</a>
              ) : (
                etape.libelle
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
