"use client";
// Code de vérification (maquettes v3, écran 2 ; R0-02, R0-14) : code de l'application ou code de secours, dans
// un seul champ ; le lien vers le code de secours suit le champ et son erreur (M4), car code.incorrect les cite.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { Bandeau, type EtatBandeau } from "@/components/ui/Bandeau";
import { Bouton } from "@/components/ui/Bouton";
import { BoutonLien } from "@/components/ui/BoutonLien";
import { Champ } from "@/components/ui/Champ";
import { envoyer } from "@/lib/api";
import { adresseConnexion, cheminDeRetour } from "@/lib/retour";
import { TEXTES } from "@/textes";

type Mode = "application" | "secours";
type Message = { etat: EtatBandeau; texte: string };

// refus qui mettent fin à la pré-session : retour à Se connecter, bandeau choisi par le motif
const RETOUR_A_LA_CONNEXION = new Set(["delai_depasse", "trop_de_codes", "compte_suspendu"]);

export function FormulaireCode({ retour }: { retour?: string | null }) {
  const routeur = useRouter();
  const champRef = useRef<HTMLInputElement>(null);
  const changementDeMode = useRef(false);
  const [mode, setMode] = useState<Mode>("application");
  const [code, setCode] = useState("");
  const [erreur, setErreur] = useState<string>();
  const [bandeau, setBandeau] = useState<Message | null>(null);
  const [envoiEnCours, setEnvoiEnCours] = useState(false);

  useEffect(() => {
    if (changementDeMode.current) champRef.current?.focus();
  }, [mode]);

  function changerDeMode(suivant: Mode) {
    changementDeMode.current = true;
    setMode(suivant);
    setCode("");
    setErreur(undefined);
  }

  async function soumettre(evenement: FormEvent<HTMLFormElement>) {
    evenement.preventDefault();
    setEnvoiEnCours(true);
    setErreur(undefined);
    setBandeau(null);
    const resultat = await envoyer("/identity/auth/code", { code });
    setEnvoiEnCours(false);
    if (resultat.ok) {
      // remplacer : le bouton « Retour » ne ramène pas sur cet écran
      routeur.replace(cheminDeRetour(retour));
      return;
    }
    const { statut, erreur: refus } = resultat;
    if (RETOUR_A_LA_CONNEXION.has(refus.code)) {
      routeur.replace(adresseConnexion(refus.code, retour));
      return;
    }
    if (statut === 401) {
      setCode("");
      setErreur(refus.message);
      champRef.current?.focus();
      return;
    }
    setBandeau({ etat: statut === 429 ? "attention" : "erreur", texte: refus.message });
  }

  const secours = mode === "secours";
  return (
    <>
      {bandeau ? <Bandeau etat={bandeau.etat} message={bandeau.texte} /> : null}
      <h1>{TEXTES.code.titre}</h1>
      <p>{TEXTES.code.consigne}</p>
      <form method="post" onSubmit={soumettre} noValidate>
        <Champ
          id="code"
          libelle={secours ? TEXTES.code.libelleSecours : TEXTES.code.libelle}
          aide={secours ? TEXTES.code.aideSecours : TEXTES.code.aide}
          erreur={erreur}
          ref={champRef}
          type="text"
          inputMode={secours ? "text" : "numeric"}
          autoComplete={secours ? "off" : "one-time-code"}
          autoCapitalize={secours ? "characters" : "none"}
          autoCorrect="off"
          spellCheck={false}
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <BoutonLien sousChamp onClick={() => changerDeMode(secours ? "application" : "secours")}>
          {secours ? TEXTES.code.utiliserApplication : TEXTES.code.utiliserSecours}
        </BoutonLien>
        <Bouton envoiEnCours={envoiEnCours}>{TEXTES.connexion.bouton}</Bouton>
      </form>
      <p>
        <Link href={adresseConnexion(null, retour)}>{TEXTES.code.recommencer}</Link>
      </p>
      <p>{TEXTES.code.sansTelephone}</p>
    </>
  );
}
