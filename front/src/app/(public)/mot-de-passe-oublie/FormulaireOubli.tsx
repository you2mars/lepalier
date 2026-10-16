"use client";
// Mot de passe oublié (maquettes v3, écran 8 ; ADR 0006) : l'adresse du compte, vérifiée à la sortie du champ ; après
// l'envoi, même réponse que le compte existe ou non (le formulaire disparaît, le bandeau d'identity s'affiche, le lien
// de retour reste).
import { useEffect, useRef, useState } from "react";
import { AdresseEmail } from "@/components/ui/AdresseEmail";
import { Bandeau, type EtatBandeau } from "@/components/ui/Bandeau";
import { Bouton } from "@/components/ui/Bouton";
import { BoutonLien } from "@/components/ui/BoutonLien";
import { Champ } from "@/components/ui/Champ";
import { Formulaire } from "@/components/ui/Formulaire";
import { Lien } from "@/components/ui/Lien";
import { envoyer } from "@/lib/api";
import { libelle } from "@/lib/libelles";
import { emailValide } from "@/lib/saisie";
import { TEXTES } from "@/textes";

const T = TEXTES.reinitialisation.demande;

const erreurAdresse = (valeur: string) => (emailValide(valeur) ? undefined : libelle("utilisateurs.email_invalide"));

export function FormulaireOubli() {
  const champ = useRef<HTMLInputElement>(null);
  const [adresse, setAdresse] = useState("");
  const [erreur, setErreur] = useState<string>();
  const [bandeau, setBandeau] = useState<{ etat: EtatBandeau; texte: string } | null>(null);
  const [envoyee, setEnvoyee] = useState(false);
  const [envoiEnCours, setEnvoiEnCours] = useState(false);
  const [reprise, setReprise] = useState(0);

  // « Saisir une autre adresse » : le formulaire revient, adresse gardée, curseur dedans
  useEffect(() => {
    if (reprise) champ.current?.focus();
  }, [reprise]);

  function autreAdresse() {
    setEnvoyee(false);
    setBandeau(null);
    setReprise((n) => n + 1);
  }

  async function demander() {
    const nouvelle = erreurAdresse(adresse);
    setErreur(nouvelle);
    if (nouvelle) {
      champ.current?.focus();
      return;
    }
    setBandeau(null);
    setEnvoiEnCours(true);
    const resultat = await envoyer<{ message: string }>("/identity/auth/reinitialisation/demande", {
      email: adresse.trim(),
    });
    setEnvoiEnCours(false);
    if (resultat.ok) {
      setEnvoyee(true);
      setBandeau({ etat: "fait", texte: resultat.donnees?.message ?? libelle("reinitialisation.demande_envoyee") });
      return;
    }
    setBandeau({ etat: resultat.statut === 429 ? "attention" : "erreur", texte: resultat.erreur.message });
  }

  return (
    <>
      {bandeau ? <Bandeau etat={bandeau.etat} message={bandeau.texte} /> : null}
      <h1>{T.titre}</h1>
      {envoyee ? (
        // revue UX (M5) : l'adresse saisie est rappelée, sans rien dire de l'existence du compte (ADR 0006)
        <>
          <p>
            {T.adresseSaisie} <AdresseEmail>{adresse.trim()}</AdresseEmail>
          </p>
          <BoutonLien onClick={autreAdresse}>{T.autreAdresse}</BoutonLien>
        </>
      ) : (
        <>
          <p>{T.consigne}</p>
          <Formulaire onSubmit={demander}>
            <Champ
              id="email"
              libelle={T.adresse}
              erreur={erreur}
              ref={champ}
              type="email"
              autoComplete="username"
              inputMode="email"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              value={adresse}
              onChange={(e) => setAdresse(e.target.value)}
              verifierALaSortie={() => setErreur(adresse ? erreurAdresse(adresse) : undefined)}
            />
            <Bouton envoiEnCours={envoiEnCours}>{T.bouton}</Bouton>
          </Formulaire>
        </>
      )}
      <p>
        <Lien href="/connexion">{T.retour}</Lien>
      </p>
    </>
  );
}
