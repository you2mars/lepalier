"use client";
// Gérer l'accès d'une personne (maquettes v3, écran 6.3 ; APP-USR-01, ADR 0006) : adresse, rôle, statut, dates de
// l'invitation ; actions selon le statut, jamais suspendre ni réinitialiser sa propre fiche ; confirmation
// récapitulative pour les actions irréversibles ou qui touchent la personne (UX-3), sans pour réactiver et renvoyer ;
// chaque écriture avec sa clé d'idempotence ; bandeau qui dit ce qui s'est passé, puis fiche relue (UX-4).
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { useAnnonce } from "@/components/cadre/MessageFlash";
import { Actions } from "@/components/ui/Actions";
import { AdresseEmail } from "@/components/ui/AdresseEmail";
import { Bandeau, type EtatBandeau } from "@/components/ui/Bandeau";
import { BoiteDeConfirmation } from "@/components/ui/BoiteDeConfirmation";
import { Bouton } from "@/components/ui/Bouton";
import { LienBouton } from "@/components/ui/LienBouton";
import { envoyer } from "@/lib/api";
import { dateEnToutesLettres } from "@/lib/format";
import { libelle } from "@/lib/libelles";
import { remplir, remplirAvec } from "@/lib/modele";
import { reprendreSession } from "@/lib/navigation";
import type { Role } from "@/lib/session";
import { TEXTES } from "@/textes";

const F = TEXTES.utilisateurs.fiche;
// au plus, attente de la fiche relue avant de permettre de nouveau les actions (relecture qui n'arrive pas)
const RELECTURE_MAX_MS = 5000;

export type Fiche = {
  id: string;
  email: string;
  nom_affiche: string;
  role: Role;
  statut: "actif" | "suspendu" | "invite";
  statut_libelle: string;
  invitation_envoyee_le: string | null;
  invitation_expire_le: string | null;
};

type Action = "suspendre" | "reactiver" | "reinitialiser" | "renvoyer" | "annulerInvitation";
type Message = { etat: EtatBandeau; texte: ReactNode };

// adresse, méthode et corps de chaque écriture d'identity
function requete(action: Action, id: string): { chemin: string; methode: "POST" | "PATCH"; corps: unknown } {
  const base = `/identity/utilisateurs/${id}`;
  switch (action) {
    case "suspendre":
      return { chemin: base, methode: "PATCH", corps: { statut: "suspendu" } };
    case "reactiver":
      return { chemin: base, methode: "PATCH", corps: { statut: "actif" } };
    case "reinitialiser":
      return { chemin: `${base}/reinitialiser-acces`, methode: "POST", corps: {} };
    case "renvoyer":
      return { chemin: `${base}/renvoyer-invitation`, methode: "POST", corps: {} };
    case "annulerInvitation":
      return { chemin: `${base}/annuler-invitation`, methode: "POST", corps: {} };
  }
}

export function GestionAcces({ fiche, estMoi }: { fiche: Fiche; estMoi: boolean }) {
  const routeur = useRouter();
  const annoncer = useAnnonce();
  const [confirmation, setConfirmation] = useState<Action | null>(null);
  const [enCours, setEnCours] = useState<Action | null>(null);
  const [message, setMessage] = useState<Message | null>(null);
  // fiche en cours de relecture après une action : aucune autre action ne part avant, sinon la réponse de la
  // relecture, arrivée après, pourrait défaire la navigation ou l'état de l'action suivante
  const [relecture, setRelecture] = useState(false);
  useEffect(() => {
    setRelecture(false);
  }, [fiche]);
  useEffect(() => {
    if (!relecture) return;
    const attente = setTimeout(() => setRelecture(false), RELECTURE_MAX_MS);
    return () => clearTimeout(attente);
  }, [relecture]);

  function relire() {
    setRelecture(true);
    routeur.refresh();
  }
  const valeurs = { nom: fiche.nom_affiche, adresse: fiche.email };
  // adresse e-mail jamais coupée à un trait d'union (revue UX, M3)
  const avecAdresse = { nom: fiche.nom_affiche, adresse: <AdresseEmail>{fiche.email}</AdresseEmail> };

  async function agir(action: Action) {
    setEnCours(action);
    setMessage(null);
    const { chemin, methode, corps } = requete(action, fiche.id);
    const resultat = await envoyer(chemin, corps, { methode, cleIdempotence: crypto.randomUUID() });
    setEnCours(null);
    setConfirmation(null);
    if (resultat.ok) {
      const texte = remplir(F[action].succes, valeurs);
      if (action === "annulerInvitation") {
        // la fiche n'existe plus : la liste dit ce qui a été fait
        annoncer({ etat: "fait", texte, pour: "/administration/utilisateurs" });
        routeur.push("/administration/utilisateurs");
        return;
      }
      setMessage({ etat: "fait", texte: remplirAvec(F[action].succes, avecAdresse) });
      relire();
      return;
    }
    if (resultat.statut === 401) {
      await reprendreSession();
      return;
    }
    // refus d'identity (409 : dernier gérant, compte non activé…) ; la fiche a pu changer entre-temps
    setMessage({ etat: resultat.statut === 409 ? "attention" : "erreur", texte: resultat.erreur.message });
    if (resultat.statut === 409) relire();
  }

  function bouton(action: Action, avecConfirmation: boolean) {
    return (
      <Bouton
        key={action}
        variante="secondaire"
        envoiEnCours={enCours === action && confirmation === null}
        disabled={relecture || (enCours !== null && enCours !== action)}
        onClick={() => (avecConfirmation ? setConfirmation(action) : agir(action))}
      >
        {F[action].bouton}
      </Bouton>
    );
  }

  const expiree = fiche.statut_libelle === libelle("statut.invitation_expiree");
  const invitation =
    fiche.statut === "invite" && fiche.invitation_envoyee_le && fiche.invitation_expire_le
      ? remplir(expiree ? F.invitationExpiree : F.invitationValable, {
          envoi: dateEnToutesLettres(fiche.invitation_envoyee_le),
          fin: dateEnToutesLettres(fiche.invitation_expire_le),
        })
      : null;

  const confirmations: Record<"suspendre" | "reinitialiser" | "annulerInvitation", { explication: ReactNode; annuler: string }> =
    {
      suspendre: { explication: F.suspendre.explication, annuler: F.annuler },
      reinitialiser: {
        // sans date (décision du 7 octobre 2026) : la date exacte vient d'identity dans la fiche relue
        explication: remplirAvec(F.reinitialiser.explication, avecAdresse),
        annuler: F.annuler,
      },
      annulerInvitation: {
        explication: remplirAvec(F.annulerInvitation.explication, avecAdresse),
        annuler: F.annulerInvitation.garder,
      },
    };
  const enConfirmation =
    confirmation === "suspendre" || confirmation === "reinitialiser" || confirmation === "annulerInvitation"
      ? confirmation
      : null;

  return (
    <>
      {message ? <Bandeau etat={message.etat} message={message.texte} /> : null}
      <p>{remplirAvec(F.adresse, avecAdresse)}</p>
      <p>{remplir(F.role, { role: TEXTES.roles[fiche.role] })}</p>
      <p>
        <LienBouton href={`/administration/utilisateurs/${fiche.id}/role`}>{F.changerRole}</LienBouton>
      </p>
      <p>{remplir(F.statut, { statut: fiche.statut_libelle })}</p>
      {invitation ? <p>{invitation}</p> : null}

      <h2>{F.actions}</h2>
      {fiche.statut === "actif" && estMoi ? <p>{F.soiMeme}</p> : null}
      <Actions>
        {fiche.statut === "actif" && !estMoi ? [bouton("suspendre", true), bouton("reinitialiser", true)] : null}
        {fiche.statut === "suspendu" ? bouton("reactiver", false) : null}
        {fiche.statut === "invite" ? [bouton("renvoyer", false), bouton("annulerInvitation", true)] : null}
      </Actions>

      <BoiteDeConfirmation
        ouverte={enConfirmation !== null}
        titre={enConfirmation ? remplir(F[enConfirmation].question, valeurs) : ""}
        libelleConfirmer={enConfirmation ? F[enConfirmation].bouton : ""}
        libelleAnnuler={enConfirmation ? confirmations[enConfirmation].annuler : ""}
        envoiEnCours={enCours !== null}
        surConfirmer={() => enConfirmation && agir(enConfirmation)}
        surAnnuler={() => setConfirmation(null)}
      >
        <p>{enConfirmation ? confirmations[enConfirmation].explication : null}</p>
      </BoiteDeConfirmation>
    </>
  );
}
