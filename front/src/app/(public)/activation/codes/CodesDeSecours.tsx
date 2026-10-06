"use client";
// Codes de secours (maquettes v3, écran 4 ; ADR 0006, R0-05) : affichés une seule fois, juste après l'activation ;
// ils ne vivent que dans la mémoire de la page. La case « J'ai noté mes codes » est contrôlée au clic, le bouton
// reste actif ; tant qu'elle n'est pas cochée, le navigateur avertit avant de quitter ou recharger la page. La feuille
// imprimée (UX-10) n'existe qu'à l'impression.
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { Bouton } from "@/components/ui/Bouton";
import { CaseACocher } from "@/components/ui/CaseACocher";
import { FeuilleImpression, HorsImpression } from "@/components/ui/Impression";
import { ListeCodes } from "@/components/ui/ListeCodes";
import { RappelPermanent } from "@/components/ui/RappelPermanent";
import { dateEnToutesLettres } from "@/lib/format";
import { TEXTES } from "@/textes";

const T = TEXTES.codes;

export function CodesDeSecours({ codes, nomAffiche }: { codes: string[]; nomAffiche: string }) {
  const routeur = useRouter();
  const titre = useRef<HTMLHeadingElement>(null);
  const caseRef = useRef<HTMLInputElement>(null);
  const [notes, setNotes] = useState(false);
  const [erreur, setErreur] = useState<string>();

  // changement d'écran sans navigation : titre de l'onglet et focus sur le titre (maquettes v3, § 0.5)
  useEffect(() => {
    document.title = `${T.titre} — ${TEXTES.application}`;
    titre.current?.focus();
  }, []);

  // tant que la case n'est pas cochée, le navigateur demande confirmation avant de quitter ou recharger la page
  useEffect(() => {
    if (notes) return;
    function retenir(evenement: BeforeUnloadEvent) {
      evenement.preventDefault();
      // anciens navigateurs : la valeur de retour déclenche la demande de confirmation
      evenement.returnValue = "";
    }
    window.addEventListener("beforeunload", retenir);
    return () => window.removeEventListener("beforeunload", retenir);
  }, [notes]);

  function continuer(evenement: FormEvent<HTMLFormElement>) {
    evenement.preventDefault();
    if (!notes) {
      setErreur(T.caseNonCochee);
      caseRef.current?.focus();
      return;
    }
    // remplacer : le bouton « Retour » ne ramène pas sur les codes
    routeur.replace("/?motif=compte_active");
  }

  return (
    <>
      <HorsImpression>
        <h1 ref={titre} tabIndex={-1}>
          {T.titre}
        </h1>
        {T.consigne.map((phrase) => (
          <p key={phrase}>{phrase}</p>
        ))}
        <RappelPermanent>{T.neFermezPas}</RappelPermanent>
        <ListeCodes codes={codes} libelle={T.titre} />
        <p>
          <Bouton variante="secondaire" onClick={() => window.print()}>
            {T.imprimer}
          </Bouton>
        </p>
        <form method="post" onSubmit={continuer} noValidate>
          <CaseACocher
            id="codes_notes"
            libelle={T.caseNotes}
            erreur={erreur}
            ref={caseRef}
            checked={notes}
            onChange={(e) => {
              setNotes(e.target.checked);
              if (e.target.checked) setErreur(undefined);
            }}
          />
          <Bouton>{T.continuer}</Bouton>
        </form>
      </HorsImpression>
      <FeuilleImpression>
        <h2>{T.titre}</h2>
        <p>{nomAffiche}</p>
        <p>{`${T.imprimeLe} ${dateEnToutesLettres(new Date())}`}</p>
        <ListeCodes codes={codes} />
        <p>{T.barrezApresUsage}</p>
      </FeuilleImpression>
    </>
  );
}
