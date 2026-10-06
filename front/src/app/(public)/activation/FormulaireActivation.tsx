"use client";
// Activer mon compte (maquettes v3, écran 3 ; ADR 0006, R0-05) : le jeton est lu après « # » et envoyé en POST à
// activation/debut (au chargement) et activation/fin (à la dernière étape). Il reste dans l'adresse jusqu'à la
// réussite, pour qu'un rechargement (au retour de l'App Store, par exemple) reprenne l'activation ; il n'en est
// retiré qu'à ce moment-là. Les trois étapes restent dans la mémoire de la page ; rien n'est stocké ailleurs.
import QRCode from "qrcode";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { Bandeau, type EtatBandeau } from "@/components/ui/Bandeau";
import { Bouton } from "@/components/ui/Bouton";
import { Champ } from "@/components/ui/Champ";
import { ChampMotDePasse } from "@/components/ui/ChampMotDePasse";
import { envoyer } from "@/lib/api";
import { libelle } from "@/lib/libelles";
import { cleDeLUri } from "@/lib/otpauth";
import { erreurLongueurMotDePasse, nomAfficheValide } from "@/lib/saisie";
import { TEXTES } from "@/textes";

const T = TEXTES.activation;

type Debut = { uri_otpauth: string; nom_affiche: string; email: string };
export type Activee = { etape: string; codes_secours: string[]; nom_affiche: string; role: string };
type Etape = 0 | 1 | 2;
type Message = { etat: EtatBandeau; texte: string };
type Phase = "chargement" | "sansJeton" | "invalide" | "panne" | "saisie";
type Cible = "titre" | "nom" | "motDePasse" | "code";

function lireJeton(): string | null {
  return window.location.hash.slice(1) || null;
}

// une fois le compte activé, le jeton ne sert plus : retiré de l'adresse affichée et de l'historique
function retirerJeton(): void {
  window.history.replaceState(window.history.state, "", window.location.pathname + window.location.search);
}

export function FormulaireActivation({ surActivation }: { surActivation: (activee: Activee) => void }) {
  const jeton = useRef<string | null | undefined>(undefined);
  const titreEtape = useRef<HTMLHeadingElement>(null);
  const champNom = useRef<HTMLInputElement>(null);
  const champMotDePasse = useRef<HTMLInputElement>(null);
  const champCode = useRef<HTMLInputElement>(null);

  const [phase, setPhase] = useState<Phase>("chargement");
  const [debut, setDebut] = useState<Debut | null>(null);
  const [qr, setQr] = useState<string>();
  const [etape, setEtape] = useState<Etape>(0);
  const [nom, setNom] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [code, setCode] = useState("");
  const [erreurs, setErreurs] = useState<{ nom?: string; motDePasse?: string; code?: string }>({});
  const [bandeau, setBandeau] = useState<Message | null>(null);
  const [cleCopiee, setCleCopiee] = useState(false);
  const [envoiEnCours, setEnvoiEnCours] = useState(false);
  // élément à focaliser après le rendu (titre de l'étape ou champ à corriger) ; n relance la demande
  const [focus, setFocus] = useState<{ cible: Cible; n: number } | null>(null);

  useEffect(() => {
    // lu une seule fois, même si l'effet est rejoué (mode strict de React)
    if (jeton.current === undefined) jeton.current = lireJeton();
    const lien = jeton.current;
    if (!lien) {
      setPhase("sansJeton");
      return;
    }
    let actif = true;
    void envoyer<Debut>("/identity/auth/activation/debut", { jeton: lien }).then((resultat) => {
      if (!actif) return;
      if (resultat.ok && resultat.donnees) {
        setDebut(resultat.donnees);
        setNom(resultat.donnees.nom_affiche);
        setPhase("saisie");
      } else if (!resultat.ok && resultat.statut === 410) {
        setPhase("invalide");
      } else {
        const message = resultat.ok ? TEXTES.commun.erreurInattendue : resultat.erreur.message;
        setBandeau({ etat: !resultat.ok && resultat.statut === 429 ? "attention" : "erreur", texte: message });
        setPhase("panne");
      }
    });
    return () => {
      actif = false;
    };
  }, []);

  useEffect(() => {
    if (!debut) return;
    let actif = true;
    void QRCode.toString(debut.uri_otpauth, { type: "svg", errorCorrectionLevel: "M", margin: 2 }).then((svg) => {
      if (actif) setQr(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`);
    });
    return () => {
      actif = false;
    };
  }, [debut]);

  useEffect(() => {
    if (!focus) return;
    const refs = { titre: titreEtape, nom: champNom, motDePasse: champMotDePasse, code: champCode };
    refs[focus.cible].current?.focus();
  }, [focus]);

  function focaliser(cible: Cible) {
    setFocus((precedent) => ({ cible, n: (precedent?.n ?? 0) + 1 }));
  }

  // changement d'étape : l'étape est annoncée en texte et reçoit le focus
  function allerA(suivante: Etape) {
    setBandeau(null);
    setEtape(suivante);
    focaliser("titre");
  }

  // erreur d'un champ : retour à son étape, message sous le champ, focus dessus
  function signaler(champ: "nom" | "motDePasse" | "code", message: string, aEtape: Etape) {
    setEtape(aEtape);
    setErreurs({ [champ]: message });
    focaliser(champ);
  }

  function erreurNom(valeur: string): string | undefined {
    return nomAfficheValide(valeur) ? undefined : libelle("nom_affiche.invalide");
  }

  function continuerNom(evenement: FormEvent<HTMLFormElement>) {
    evenement.preventDefault();
    const erreur = erreurNom(nom);
    if (erreur) return signaler("nom", erreur, 0);
    setErreurs({});
    allerA(1);
  }

  function continuerMotDePasse(evenement: FormEvent<HTMLFormElement>) {
    evenement.preventDefault();
    const erreur = erreurLongueurMotDePasse(motDePasse);
    if (erreur) return signaler("motDePasse", erreur, 1);
    setErreurs({});
    allerA(2);
  }

  async function activer(evenement: FormEvent<HTMLFormElement>) {
    evenement.preventDefault();
    setEnvoiEnCours(true);
    setBandeau(null);
    setErreurs({});
    const resultat = await envoyer<Activee>("/identity/auth/activation/fin", {
      jeton: jeton.current,
      nom_affiche: nom,
      mot_de_passe: motDePasse,
      code,
    });
    setEnvoiEnCours(false);
    if (resultat.ok && resultat.donnees) {
      retirerJeton();
      surActivation(resultat.donnees);
      return;
    }
    if (resultat.ok) {
      setBandeau({ etat: "erreur", texte: TEXTES.commun.erreurInattendue });
      return;
    }
    const { statut, erreur } = resultat;
    if (statut === 410) {
      setPhase("invalide");
    } else if (statut === 422 && erreur.champs.nom_affiche) {
      signaler("nom", erreur.champs.nom_affiche, 0);
    } else if (statut === 422 && erreur.champs.mot_de_passe) {
      signaler("motDePasse", erreur.champs.mot_de_passe, 1);
    } else if (statut === 400 && erreur.code === "code_incorrect") {
      setCode("");
      signaler("code", erreur.champs.code ?? erreur.message, 2);
    } else {
      setBandeau({ etat: statut === 429 ? "attention" : "erreur", texte: erreur.message });
    }
  }

  async function copierCle(cle: string) {
    try {
      await navigator.clipboard.writeText(cle);
      setCleCopiee(true);
    } catch {
      // presse-papiers indisponible : la clé reste affichée pour être recopiée
    }
  }

  if (phase === "sansJeton") {
    return (
      <>
        <h1>{T.titre}</h1>
        <p>{T.sansLien}</p>
      </>
    );
  }
  if (phase === "invalide") {
    return (
      <>
        <Bandeau etat="attention" message={libelle("invitation.lien_invalide")} />
        <h1>{T.titre}</h1>
      </>
    );
  }
  if (phase !== "saisie" || !debut) {
    return (
      <>
        {bandeau ? <Bandeau etat={bandeau.etat} message={bandeau.texte} /> : null}
        <h1>{T.titre}</h1>
        {phase === "chargement" ? <div className="squelette" aria-busy="true" /> : null}
      </>
    );
  }

  const groupes = cleDeLUri(debut.uri_otpauth);
  const etapePrecedente =
    etape > 0 ? (
      <p>
        <button type="button" className="bouton-lien" onClick={() => allerA((etape - 1) as Etape)}>
          {T.etapePrecedente}
        </button>
      </p>
    ) : null;

  return (
    <>
      {bandeau ? <Bandeau etat={bandeau.etat} message={bandeau.texte} /> : null}
      <h1>{T.titre}</h1>
      <div className="encadre">
        <p>{T.avantDeCommencer}</p>
        <details>
          <summary>{T.autresApplications}</summary>
          <ul>
            {T.autresApplicationsListe.map((application) => (
              <li key={application}>{application}</li>
            ))}
          </ul>
        </details>
      </div>
      <p>{`${T.adresseDeConnexion} ${debut.email}`}</p>
      <h2 ref={titreEtape} tabIndex={-1}>
        {T.etapes[etape]}
      </h2>

      {etape === 0 ? (
        <form method="post" onSubmit={continuerNom} noValidate>
          <Champ
            id="nom_affiche"
            libelle={T.nomAffiche}
            aide={T.aideNom}
            erreur={erreurs.nom}
            ref={champNom}
            autoComplete="name"
            value={nom}
            onChange={(e) => setNom(e.target.value)}
            onBlur={() => setErreurs({ nom: erreurNom(nom) })}
          />
          <Bouton>{T.continuer}</Bouton>
        </form>
      ) : null}

      {etape === 1 ? (
        <form method="post" onSubmit={continuerMotDePasse} noValidate>
          {/* identifiant du compte pour le gestionnaire de mots de passe, déjà affiché plus haut */}
          <input type="email" name="username" autoComplete="username" value={debut.email} readOnly hidden />
          <ChampMotDePasse
            id="mot_de_passe"
            libelle={T.motDePasse}
            aide={T.aideMotDePasse}
            erreur={erreurs.motDePasse}
            autoComplete="new-password"
            ref={champMotDePasse}
            value={motDePasse}
            onChange={(e) => setMotDePasse(e.target.value)}
            onBlur={() => setErreurs({ motDePasse: motDePasse ? erreurLongueurMotDePasse(motDePasse) : undefined })}
          />
          <Bouton>{T.continuer}</Bouton>
        </form>
      ) : null}

      {etape === 2 ? (
        <>
          <p>{T.consigneApplication}</p>
          <ul>
            <li>{T.consigneTelephone}</li>
            <li>{T.consigneOrdinateur}</li>
          </ul>
          <p>
            <a className="bouton bouton-secondaire" href={debut.uri_otpauth}>
              {T.ajouter}
            </a>
          </p>
          <p>{T.rienNeSouvre}</p>
          {qr ? <img className="qr" src={qr} alt={T.altQr} width={200} height={200} /> : null}
          <p>{T.cleManuelle}</p>
          <p className="cle">
            <code aria-label={groupes.join(" ")}>{groupes.join(" ")}</code>{" "}
            <button type="button" className="bouton bouton-secondaire" onClick={() => copierCle(groupes.join(""))}>
              {T.copierCle}
            </button>
          </p>
          <p role="status">{cleCopiee ? T.cleCopiee : ""}</p>
          <form method="post" onSubmit={activer} noValidate>
            <Champ
              id="code"
              libelle={T.libelleCode}
              erreur={erreurs.code}
              ref={champCode}
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              autoCorrect="off"
              spellCheck={false}
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
            <Bouton envoiEnCours={envoiEnCours}>{T.bouton}</Bouton>
          </form>
        </>
      ) : null}
      {etapePrecedente}
    </>
  );
}
