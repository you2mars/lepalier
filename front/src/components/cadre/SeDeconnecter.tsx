"use client";
// Se déconnecter (R0-03, R0-08) : session fermée par identity, puis Se connecter avec « Déconnexion effectuée. » ;
// une session déjà expirée (401) mène au même écran ; une panne laisse la personne connectée et le dit.
import { useState } from "react";
import { Bandeau } from "@/components/ui/Bandeau";
import { Bouton } from "@/components/ui/Bouton";
import { envoyer } from "@/lib/api";
import { quitterVers } from "@/lib/navigation";
import { TEXTES } from "@/textes";

export function SeDeconnecter() {
  const [envoiEnCours, setEnvoiEnCours] = useState(false);
  const [erreur, setErreur] = useState<string>();

  async function seDeconnecter() {
    setEnvoiEnCours(true);
    setErreur(undefined);
    const resultat = await envoyer("/identity/auth/deconnexion", {});
    if (resultat.ok || resultat.statut === 401) {
      quitterVers("/connexion?motif=deconnexion");
      return;
    }
    setEnvoiEnCours(false);
    setErreur(resultat.erreur.message);
  }

  return (
    <div className="se-deconnecter">
      <Bouton variante="secondaire" envoiEnCours={envoiEnCours} onClick={seDeconnecter}>
        {TEXTES.cadre.seDeconnecter}
      </Bouton>
      {erreur ? <Bandeau etat="erreur" message={erreur} /> : null}
    </div>
  );
}
