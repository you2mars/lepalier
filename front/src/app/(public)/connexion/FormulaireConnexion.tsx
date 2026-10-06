"use client";
// Se connecter (maquettes v3, écran 1 ; R0-01, R0-24) : adresse et mot de passe, un seul bouton principal ;
// le chemin de retour, contrôlé, suit jusqu'à l'écran du code.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useRef, useState } from "react";
import { Bandeau, type EtatBandeau } from "@/components/ui/Bandeau";
import { Bouton } from "@/components/ui/Bouton";
import { Champ } from "@/components/ui/Champ";
import { ChampMotDePasse } from "@/components/ui/ChampMotDePasse";
import { envoyer } from "@/lib/api";
import { libelle } from "@/lib/libelles";
import { cheminDeRetour } from "@/lib/retour";
import { TEXTES } from "@/textes";

type Message = { etat: EtatBandeau; texte: string };

// bandeau d'arrivée sur l'écran (déconnexion, session expirée, accès suspendu, délai du code dépassé…)
function bandeauArrivee(motif: string | null | undefined): Message | null {
  switch (motif) {
    case "deconnexion":
      return { etat: "fait", texte: TEXTES.connexion.deconnexionEffectuee };
    case "mot_de_passe_change":
      return { etat: "fait", texte: TEXTES.connexion.motDePasseChange };
    case "session_expiree":
      return { etat: "attention", texte: TEXTES.commun.sessionExpiree };
    case "compte_suspendu":
      return { etat: "attention", texte: libelle("connexion.compte_suspendu") };
    case "delai_depasse":
      return { etat: "attention", texte: libelle("code.delai_depasse") };
    case "trop_de_codes":
      return { etat: "attention", texte: libelle("code.trop_de_codes") };
    default:
      return null;
  }
}

export function FormulaireConnexion({ motif, retour }: { motif?: string | null; retour?: string | null }) {
  const routeur = useRouter();
  const motDePasseRef = useRef<HTMLInputElement>(null);
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreurMotDePasse, setErreurMotDePasse] = useState<string>();
  const [bandeau, setBandeau] = useState<Message | null>(bandeauArrivee(motif));
  const [envoiEnCours, setEnvoiEnCours] = useState(false);

  async function soumettre(evenement: FormEvent<HTMLFormElement>) {
    evenement.preventDefault();
    setEnvoiEnCours(true);
    setErreurMotDePasse(undefined);
    setBandeau(null);
    const resultat = await envoyer("/identity/auth/connexion", { email, mot_de_passe: motDePasse });
    setEnvoiEnCours(false);
    if (resultat.ok) {
      const chemin = cheminDeRetour(retour);
      routeur.push(chemin === "/" ? "/connexion/code" : `/connexion/code?retour=${encodeURIComponent(chemin)}`);
      return;
    }
    const { statut, erreur } = resultat;
    if (statut === 401) {
      setMotDePasse("");
      setErreurMotDePasse(erreur.champs.mot_de_passe ?? erreur.message);
      motDePasseRef.current?.focus();
      return;
    }
    setBandeau({ etat: statut === 429 ? "attention" : "erreur", texte: erreur.message });
  }

  return (
    <>
      {bandeau ? <Bandeau etat={bandeau.etat} message={bandeau.texte} /> : null}
      <h1>{TEXTES.connexion.titre}</h1>
      <form onSubmit={soumettre} noValidate>
        <Champ
          id="email"
          libelle={TEXTES.connexion.adresse}
          type="email"
          autoComplete="username"
          inputMode="email"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <ChampMotDePasse
          id="mot_de_passe"
          libelle={TEXTES.connexion.motDePasse}
          autoComplete="current-password"
          ref={motDePasseRef}
          value={motDePasse}
          erreur={erreurMotDePasse}
          onChange={(e) => setMotDePasse(e.target.value)}
        />
        <Bouton envoiEnCours={envoiEnCours}>{TEXTES.connexion.bouton}</Bouton>
      </form>
      <p>
        <Link href="/mot-de-passe-oublie">{TEXTES.connexion.oublie}</Link>
      </p>
    </>
  );
}
