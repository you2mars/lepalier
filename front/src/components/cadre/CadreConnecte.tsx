// Cadre des écrans connectés (maquettes v3, § 0.2 ; R0-03) : lien d'évitement, nom de l'application, nom affiché et
// rôle en mots du lexique, « Se déconnecter », menu, puis le contenu.
import type { ReactNode } from "react";
import type { Personne } from "@/lib/session";
import { TEXTES } from "@/textes";
import { Menu } from "./Menu";
import { SeDeconnecter } from "./SeDeconnecter";

export function CadreConnecte({ personne, children }: { personne: Personne; children: ReactNode }) {
  return (
    <div className="cadre-connecte">
      <a className="aller-au-contenu" href="#contenu">
        {TEXTES.allerAuContenu}
      </a>
      <header className="entete-connecte">
        <p className="nom-application">{TEXTES.application}</p>
        <SeDeconnecter />
        <p className="personne">{`${personne.nom_affiche} · ${TEXTES.cadre.role} ${TEXTES.roles[personne.role]}`}</p>
      </header>
      <Menu role={personne.role} />
      <main id="contenu" className="contenu-connecte" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
