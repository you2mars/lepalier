"use client";
// Inviter une personne (maquettes v3, écran 6.2 ; R0-04, APP-USR-01) : nom affiché, adresse, rôle (Associé par
// défaut), vérifiés à la sortie du champ ; confirmation récapitulative avant l'envoi (UX-3) ; écriture avec une clé
// d'idempotence, la même pour chaque nouvel essai d'une même confirmation (UX-22) ; puis la liste, qui dit ce qui a
// été fait (UX-4, UX-24).
import { useEffect, useRef, useState } from "react";
import { Actions } from "@/components/ui/Actions";
import { AdresseEmail } from "@/components/ui/AdresseEmail";
import { Bandeau } from "@/components/ui/Bandeau";
import { BoiteDeConfirmation } from "@/components/ui/BoiteDeConfirmation";
import { Bouton } from "@/components/ui/Bouton";
import { Champ } from "@/components/ui/Champ";
import { ChoixUnique } from "@/components/ui/ChoixUnique";
import { Formulaire } from "@/components/ui/Formulaire";
import { LienBouton } from "@/components/ui/LienBouton";
import { ValeurEnGrand } from "@/components/ui/ValeurEnGrand";
import { envoyer } from "@/lib/api";
import { libelle } from "@/lib/libelles";
import { remplir, remplirAvec } from "@/lib/modele";
import { allerVers, reprendreSession } from "@/lib/navigation";
import { emailValide, nomAfficheValide } from "@/lib/saisie";
import type { Role } from "@/lib/session";
import { TEXTES } from "@/textes";

const I = TEXTES.utilisateurs.inviter;
const ROLES: Role[] = ["associe", "operateur", "gerant"];

type Erreurs = { nom?: string; adresse?: string };
type Cible = keyof Erreurs;

const erreurNom = (valeur: string) => (nomAfficheValide(valeur) ? undefined : libelle("nom_affiche.invalide"));
const erreurAdresse = (valeur: string) => (emailValide(valeur) ? undefined : libelle("utilisateurs.email_invalide"));

function description(role: Role): Record<string, string> {
  return { role: TEXTES.roles[role], description: TEXTES.descriptionsRoles[role] };
}

export function FormulaireInvitation() {
  const champNom = useRef<HTMLInputElement>(null);
  const champAdresse = useRef<HTMLInputElement>(null);
  const [nom, setNom] = useState("");
  const [adresse, setAdresse] = useState("");
  const [role, setRole] = useState<Role>("associe");
  // erreurs vérifiées par la page (à la sortie du champ, à l'envoi) et refus d'identity, gardés jusqu'au changement
  const [erreurs, setErreurs] = useState<Erreurs>({});
  const [serveur, setServeur] = useState<Erreurs>({});
  const [focus, setFocus] = useState<{ cible: Cible; n: number } | null>(null);
  const [confirmation, setConfirmation] = useState(false);
  const [cle, setCle] = useState("");
  const [envoiEnCours, setEnvoiEnCours] = useState(false);
  const [panne, setPanne] = useState<string>();

  // focus sur le premier champ en erreur, après le rendu : l'effet de la page passe après celui de la boîte de
  // confirmation, qui rend d'abord le focus au bouton qui l'a ouverte
  useEffect(() => {
    if (focus) (focus.cible === "nom" ? champNom : champAdresse).current?.focus();
  }, [focus]);

  function focaliserPremiereErreur(e: Erreurs) {
    const cible: Cible | null = e.nom ? "nom" : e.adresse ? "adresse" : null;
    if (cible) setFocus((precedent) => ({ cible, n: (precedent?.n ?? 0) + 1 }));
  }

  function demanderConfirmation() {
    const locales = { nom: erreurNom(nom), adresse: erreurAdresse(adresse) };
    const toutes = { nom: locales.nom ?? serveur.nom, adresse: locales.adresse ?? serveur.adresse };
    setErreurs(locales);
    // un refus d'identity sur une valeur inchangée se reproduirait : pas de nouvelle confirmation
    if (toutes.nom || toutes.adresse) return focaliserPremiereErreur(toutes);
    setPanne(undefined);
    // une clé par confirmation : un nouvel essai après une panne ne crée jamais une seconde invitation
    if (!confirmation && !cle) setCle(crypto.randomUUID());
    setConfirmation(true);
  }

  async function inviter() {
    setEnvoiEnCours(true);
    const resultat = await envoyer<{ id: string }>(
      "/identity/utilisateurs/inviter",
      { nom_affiche: nom, email: adresse, role },
      { cleIdempotence: cle },
    );
    setEnvoiEnCours(false);
    if (resultat.ok && resultat.donnees) {
      allerVers(`/administration/utilisateurs?invitee=${encodeURIComponent(resultat.donnees.id)}`);
      return;
    }
    setConfirmation(false);
    if (!resultat.ok && resultat.statut === 401) {
      await reprendreSession();
      return;
    }
    const champs = resultat.ok ? {} : resultat.erreur.champs;
    if (champs.nom_affiche || champs.email) {
      // la saisie devra changer : une nouvelle confirmation aura sa propre clé
      setCle("");
      const refus = { nom: champs.nom_affiche, adresse: champs.email };
      setServeur(refus);
      return focaliserPremiereErreur(refus);
    }
    setPanne(resultat.ok ? TEXTES.commun.erreurInattendue : resultat.erreur.message);
  }

  return (
    <>
      {panne ? <Bandeau etat="erreur" message={panne} /> : null}
      <Formulaire onSubmit={demanderConfirmation}>
        <Champ
          id="nom_affiche"
          libelle={I.nomAffiche}
          aide={I.aideNom}
          erreur={erreurs.nom ?? serveur.nom}
          ref={champNom}
          autoComplete="off"
          value={nom}
          onChange={(e) => {
            setNom(e.target.value);
            setServeur((s) => ({ ...s, nom: undefined }));
            setCle("");
          }}
          verifierALaSortie={() => setErreurs((e) => ({ ...e, nom: erreurNom(nom) }))}
        />
        <Champ
          id="email"
          libelle={I.adresse}
          aide={I.aideAdresse}
          erreur={erreurs.adresse ?? serveur.adresse}
          ref={champAdresse}
          type="email"
          autoComplete="off"
          inputMode="email"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          value={adresse}
          onChange={(e) => {
            setAdresse(e.target.value);
            setServeur((s) => ({ ...s, adresse: undefined }));
            setCle("");
          }}
          verifierALaSortie={() => setErreurs((e) => ({ ...e, adresse: erreurAdresse(adresse) }))}
        />
        <ChoixUnique
          nom="role"
          legende={I.role}
          choix={ROLES.map((r) => ({ valeur: r, libelle: remplir(I.optionRole, description(r)) }))}
          valeur={role}
          surChoix={(r) => {
            setRole(r as Role);
            setCle("");
          }}
        />
        <Actions>
          <Bouton>{I.envoyer}</Bouton>
          <LienBouton href="/administration/utilisateurs">{I.annuler}</LienBouton>
        </Actions>
      </Formulaire>
      <BoiteDeConfirmation
        ouverte={confirmation}
        titre={remplir(I.confirmation.question, { nom: nom.trim() })}
        libelleConfirmer={I.envoyer}
        libelleAnnuler={I.confirmation.modifier}
        envoiEnCours={envoiEnCours}
        surConfirmer={inviter}
        surAnnuler={() => setConfirmation(false)}
      >
        <ValeurEnGrand>
          {remplirAvec(I.confirmation.adresse, { adresse: <AdresseEmail seule>{adresse.trim()}</AdresseEmail> })}
        </ValeurEnGrand>
        <p>{remplir(I.confirmation.role, description(role))}</p>
        <p>{I.confirmation.validite}</p>
      </BoiteDeConfirmation>
    </>
  );
}
