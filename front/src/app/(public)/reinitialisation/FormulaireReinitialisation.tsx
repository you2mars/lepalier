"use client";
// Choisir un nouveau mot de passe (maquettes v3, écran 9 ; ADR 0006) : le jeton est lu après « # » et reste dans
// l'adresse jusqu'à la réussite (un rechargement garde le lien, comme à l'activation) ; mot de passe et confirmation
// (vérifiée par le front seul), code de l'application ou code de secours ; puis Se connecter avec le bandeau.
import { useEffect, useRef, useState } from "react";
import { Bandeau, type EtatBandeau } from "@/components/ui/Bandeau";
import { Bouton } from "@/components/ui/Bouton";
import { BoutonLien } from "@/components/ui/BoutonLien";
import { Champ } from "@/components/ui/Champ";
import { ChampMotDePasse } from "@/components/ui/ChampMotDePasse";
import { Formulaire } from "@/components/ui/Formulaire";
import { Squelette } from "@/components/ui/Squelette";
import { Lien } from "@/components/ui/Lien";
import { envoyer } from "@/lib/api";
import { quitterVers } from "@/lib/navigation";
import { erreurLongueurMotDePasse } from "@/lib/saisie";
import { TEXTES } from "@/textes";

const C = TEXTES.reinitialisation.choix;
const M = TEXTES.motDePasse;

type Cible = "motDePasse" | "confirmation" | "code";
type Erreurs = Partial<Record<Cible, string>>;

export function FormulaireReinitialisation() {
  // lu une fois la page prise en main par le navigateur (le serveur ne voit jamais ce qui suit « # ») ; null : pas
  // encore lu
  const [jeton, setJeton] = useState<string | null>(null);
  useEffect(() => {
    setJeton(window.location.hash.slice(1));
  }, []);
  const refs = {
    motDePasse: useRef<HTMLInputElement>(null),
    confirmation: useRef<HTMLInputElement>(null),
    code: useRef<HTMLInputElement>(null),
  };
  const [motDePasse, setMotDePasse] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [code, setCode] = useState("");
  const [secours, setSecours] = useState(false);
  const [erreurs, setErreurs] = useState<Erreurs>({});
  const [fin, setFin] = useState<string | null>(null);
  const [bandeau, setBandeau] = useState<{ etat: EtatBandeau; texte: string } | null>(null);
  const [envoiEnCours, setEnvoiEnCours] = useState(false);
  const [focus, setFocus] = useState<{ cible: Cible; n: number } | null>(null);

  useEffect(() => {
    if (focus) refs[focus.cible].current?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- les références ne changent pas
  }, [focus]);

  function signaler(cible: Cible, message: string) {
    setErreurs({ [cible]: message });
    setFocus((precedent) => ({ cible, n: (precedent?.n ?? 0) + 1 }));
  }

  function changerDeMode() {
    setSecours((s) => !s);
    setCode("");
    setErreurs((e) => ({ ...e, code: undefined }));
    setFocus((precedent) => ({ cible: "code", n: (precedent?.n ?? 0) + 1 }));
  }

  async function changer() {
    const longueur = erreurLongueurMotDePasse(motDePasse);
    if (longueur) return signaler("motDePasse", longueur);
    if (confirmation !== motDePasse) return signaler("confirmation", M.differents);
    setErreurs({});
    setBandeau(null);
    setEnvoiEnCours(true);
    const resultat = await envoyer("/identity/auth/reinitialisation/fin", { jeton, mot_de_passe: motDePasse, code });
    setEnvoiEnCours(false);
    if (resultat.ok) {
      // le jeton ne sert plus : retiré de l'adresse et de l'historique
      window.history.replaceState(window.history.state, "", window.location.pathname);
      quitterVers("/connexion?motif=mot_de_passe_change");
      return;
    }
    const { statut, erreur } = resultat;
    if (statut === 410 || erreur.code === "trop_de_codes") return setFin(erreur.message);
    if (statut === 422 && erreur.champs.mot_de_passe) {
      // le code aura souvent changé avant le nouvel envoi
      setMotDePasse("");
      setConfirmation("");
      setCode("");
      return signaler("motDePasse", erreur.champs.mot_de_passe);
    }
    if (statut === 400 && erreur.code === "code_incorrect") {
      setCode("");
      return signaler("code", erreur.champs.code ?? erreur.message);
    }
    setBandeau({ etat: statut === 429 ? "attention" : "erreur", texte: erreur.message });
  }

  const lienOubli = (
    <p>
      <Lien href="/mot-de-passe-oublie">{TEXTES.connexion.oublie}</Lien>
    </p>
  );
  // constat UX (14) : chemin de retour vers Se connecter sur chaque état de l'écran
  const lienRetour = (
    <p>
      <Lien href="/connexion">{TEXTES.reinitialisation.demande.retour}</Lien>
    </p>
  );
  if (jeton === null) {
    return (
      <>
        <h1>{C.titre}</h1>
        <Squelette />
      </>
    );
  }
  if (!jeton || fin) {
    return (
      <>
        {fin ? <Bandeau etat="attention" message={fin} /> : null}
        <h1>{C.titre}</h1>
        {fin ? null : <p>{C.sansLien}</p>}
        {lienOubli}
        {lienRetour}
      </>
    );
  }

  return (
    <>
      {bandeau ? <Bandeau etat={bandeau.etat} message={bandeau.texte} /> : null}
      <h1>{C.titre}</h1>
      <Formulaire onSubmit={changer}>
        <ChampMotDePasse
          id="mot_de_passe"
          libelle={C.motDePasse}
          aide={TEXTES.activation.aideMotDePasse}
          erreur={erreurs.motDePasse}
          autoComplete="new-password"
          ref={refs.motDePasse}
          value={motDePasse}
          onChange={(e) => setMotDePasse(e.target.value)}
          verifierALaSortie={() =>
            setErreurs((e) => ({ ...e, motDePasse: motDePasse ? erreurLongueurMotDePasse(motDePasse) : undefined }))
          }
        />
        <ChampMotDePasse
          id="confirmation_mot_de_passe"
          libelle={M.confirmation}
          erreur={erreurs.confirmation}
          autoComplete="new-password"
          nomsAccessibles={{ afficher: M.afficherConfirmationAccessible, masquer: M.masquerConfirmationAccessible }}
          ref={refs.confirmation}
          value={confirmation}
          onChange={(e) => setConfirmation(e.target.value)}
          verifierALaSortie={() =>
            setErreurs((e) => ({
              ...e,
              confirmation: confirmation && confirmation !== motDePasse ? M.differents : undefined,
            }))
          }
        />
        <Champ
          id="code"
          libelle={secours ? TEXTES.code.libelleSecours : C.code}
          aide={secours ? TEXTES.code.aideSecours : C.aideCode}
          erreur={erreurs.code}
          ref={refs.code}
          type="text"
          inputMode={secours ? "text" : "numeric"}
          autoComplete={secours ? "off" : "one-time-code"}
          autoCapitalize={secours ? "characters" : "none"}
          autoCorrect="off"
          spellCheck={false}
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <BoutonLien sousChamp onClick={changerDeMode}>
          {secours ? TEXTES.code.utiliserApplication : TEXTES.code.utiliserSecours}
        </BoutonLien>
        <Bouton envoiEnCours={envoiEnCours}>{C.bouton}</Bouton>
      </Formulaire>
      <p>{TEXTES.code.sansTelephone}</p>
      {lienRetour}
    </>
  );
}
