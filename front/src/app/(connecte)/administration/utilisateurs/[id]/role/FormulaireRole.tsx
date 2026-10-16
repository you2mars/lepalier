"use client";
// Changer le rôle (maquettes v3, écran 6.4 ; M7, APP-USR-01) : rôle actuel coché et signalé ; rôle inchangé : rien
// d'envoyé (A7) ; donner le rôle de gérant à une autre personne, ou quitter soi-même ce rôle : confirmation
// récapitulative (UX-3) ; autres changements sans confirmation ; écriture avec une clé d'idempotence ; la fiche dit ce
// qui a été fait ; après avoir quitté soi-même le rôle de gérant, l'accueil est rechargé (menu et rôle à jour).
import { useState } from "react";
import { laisserMessage } from "@/components/cadre/MessageFlash";
import { Actions } from "@/components/ui/Actions";
import { Bandeau, type EtatBandeau } from "@/components/ui/Bandeau";
import { BoiteDeConfirmation } from "@/components/ui/BoiteDeConfirmation";
import { Bouton } from "@/components/ui/Bouton";
import { ChoixUnique } from "@/components/ui/ChoixUnique";
import { Formulaire } from "@/components/ui/Formulaire";
import { LienBouton } from "@/components/ui/LienBouton";
import { envoyer } from "@/lib/api";
import { remplir } from "@/lib/modele";
import { allerVers, quitterVers, reprendreSession } from "@/lib/navigation";
import type { Role } from "@/lib/session";
import { TEXTES } from "@/textes";
import type { Fiche } from "../GestionAcces";

const R = TEXTES.utilisateurs.role;
const ROLES: Role[] = ["associe", "operateur", "gerant"];

type Confirmation = "donnerGerant" | "quitterGerant";

export function FormulaireRole({ fiche, estMoi }: { fiche: Fiche; estMoi: boolean }) {
  const [role, setRole] = useState<Role>(fiche.role);
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const [envoiEnCours, setEnvoiEnCours] = useState(false);
  const [message, setMessage] = useState<{ etat: EtatBandeau; texte: string } | null>(null);
  const cheminFiche = `/administration/utilisateurs/${fiche.id}`;

  function libelleRole(r: Role): string {
    const option = remplir(TEXTES.utilisateurs.inviter.optionRole, {
      role: TEXTES.roles[r],
      description: TEXTES.descriptionsRoles[r],
    });
    return r === fiche.role ? `${option} ${R.roleActuel}` : option;
  }

  function retourALaFiche(texte: string) {
    laisserMessage({ etat: "fait", texte, pour: cheminFiche });
    allerVers(cheminFiche);
  }

  function demander() {
    setMessage(null);
    if (role === fiche.role) {
      return retourALaFiche(remplir(R.aucunChangement, { nom: fiche.nom_affiche, role: TEXTES.roles[role] }));
    }
    if (estMoi && fiche.role === "gerant") return setConfirmation("quitterGerant");
    if (role === "gerant") return setConfirmation("donnerGerant");
    void changer();
  }

  async function changer() {
    setEnvoiEnCours(true);
    const resultat = await envoyer(
      `/identity/utilisateurs/${fiche.id}`,
      { role },
      { methode: "PATCH", cleIdempotence: crypto.randomUUID() },
    );
    setEnvoiEnCours(false);
    setConfirmation(null);
    if (resultat.ok) {
      if (estMoi && fiche.role === "gerant") {
        // l'en-tête et le menu viennent du cadre connecté : rechargé, il relit le rôle chez identity
        quitterVers("/?motif=role_quitte");
        return;
      }
      retourALaFiche(
        remplir(R.succes, {
          nom: fiche.nom_affiche,
          nouveau: TEXTES.roles[role],
          ancien: TEXTES.roles[fiche.role],
        }),
      );
      return;
    }
    if (resultat.statut === 401) {
      await reprendreSession();
      return;
    }
    setMessage({ etat: resultat.statut === 409 ? "attention" : "erreur", texte: resultat.erreur.message });
  }

  return (
    <>
      {message ? <Bandeau etat={message.etat} message={message.texte} /> : null}
      <Formulaire onSubmit={demander}>
        <ChoixUnique
          nom="role"
          legende={TEXTES.utilisateurs.inviter.role}
          choix={ROLES.map((r) => ({ valeur: r, libelle: libelleRole(r) }))}
          valeur={role}
          surChoix={(r) => setRole(r as Role)}
        />
        <Actions>
          <Bouton envoiEnCours={envoiEnCours && confirmation === null}>{R.enregistrer}</Bouton>
          <LienBouton href={cheminFiche}>{R.annuler}</LienBouton>
        </Actions>
      </Formulaire>
      <BoiteDeConfirmation
        ouverte={confirmation !== null}
        titre={confirmation ? remplir(R[confirmation].question, { nom: fiche.nom_affiche }) : ""}
        libelleConfirmer={confirmation ? R[confirmation].bouton : ""}
        libelleAnnuler={R.annuler}
        envoiEnCours={envoiEnCours}
        surConfirmer={() => void changer()}
        surAnnuler={() => setConfirmation(null)}
      >
        <p>{confirmation ? R[confirmation].explication : null}</p>
      </BoiteDeConfirmation>
    </>
  );
}
