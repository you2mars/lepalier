// Administration › Utilisateurs (maquettes v3, écran 6.1 ; R0-04) : liste des personnes, triée par nom par identity,
// statut en mots ; « Inviter une personne » en bouton principal ; réservée au gérant (écran 7 sinon).
import type { Metadata } from "next";
import { PageReservee } from "@/components/cadre/PageReservee";
import { Bandeau } from "@/components/ui/Bandeau";
import { FilAriane } from "@/components/ui/FilAriane";
import { LienBouton } from "@/components/ui/LienBouton";
import { TableauResponsive } from "@/components/ui/TableauResponsive";
import { TexteMasque } from "@/components/ui/TexteMasque";
import { remplir } from "@/lib/modele";
import { type Parametres, premier } from "@/lib/parametres";
import { lireConnecte, personneConnectee, type Role } from "@/lib/session";
import { TEXTES } from "@/textes";

export const metadata: Metadata = { title: "Utilisateurs — LePalier" };

const L = TEXTES.utilisateurs.liste;

type Utilisateur = { id: string; email: string; nom_affiche: string; role: Role; statut_libelle: string };

export default async function Page({ searchParams }: { searchParams: Parametres }) {
  // après une invitation : l'identifiant seul dans l'adresse ; nom et adresse lus dans la liste
  const invitee = premier((await searchParams).invitee);
  const personne = await personneConnectee();
  if (personne?.role !== "gerant") return <PageReservee />;
  const lecture = await lireConnecte<{ utilisateurs: Utilisateur[] }>("/identity/utilisateurs");
  if (!lecture.ok && lecture.statut === 403) return <PageReservee />;

  const lignes = lecture.ok
    ? lecture.donnees.utilisateurs.map((u) => {
        const href = `/administration/utilisateurs/${u.id}`;
        const nom = `${L.gererAcces} ${L.gererAccesDe} ${u.nom_affiche}`;
        return {
          cle: u.id,
          cellules: [
            u.nom_affiche,
            u.email,
            TEXTES.roles[u.role],
            u.statut_libelle,
            <LienBouton key="gerer" href={href}>
              {L.gererAcces}{" "}
              <TexteMasque>{`${L.gererAccesDe} ${u.nom_affiche}`}</TexteMasque>
            </LienBouton>,
          ],
          carte: { href, nom, contenu: [u.nom_affiche, TEXTES.roles[u.role], u.statut_libelle] },
        };
      })
    : null;
  const nouvelle = lecture.ok ? lecture.donnees.utilisateurs.find((u) => u.id === invitee) : undefined;

  return (
    <>
      {nouvelle ? (
        <Bandeau
          etat="fait"
          message={remplir(TEXTES.utilisateurs.inviter.succes, { nom: nouvelle.nom_affiche, adresse: nouvelle.email })}
        />
      ) : null}
      <FilAriane etapes={[{ libelle: TEXTES.cadre.administration }, { libelle: L.titre }]} />
      <h1>{L.titre}</h1>
      <p>
        <LienBouton href="/administration/utilisateurs/inviter" variante="principal">
          {L.inviter}
        </LienBouton>
      </p>
      {lignes ? (
        <TableauResponsive
          libelle={L.titre}
          colonnes={[
            { titre: L.colonnes.nom },
            { titre: L.colonnes.adresse },
            { titre: L.colonnes.role },
            { titre: L.colonnes.statut },
            { titre: L.colonnes.actions, masque: true },
          ]}
          lignes={lignes}
        />
      ) : (
        <p>{TEXTES.indisponible}</p>
      )}
    </>
  );
}
