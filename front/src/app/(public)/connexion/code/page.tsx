import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { type Parametres, premier } from "@/lib/parametres";
import { adresseConnexion } from "@/lib/retour";
import { FormulaireCode } from "./FormulaireCode";

export const metadata: Metadata = { title: "Code de vérification — LePalier" };

// cookie de pré-session posé par identity après le mot de passe (5 minutes) ; illisible ici, seule sa présence compte
const COOKIE_PRE = "lp_pre";

export default async function Page({ searchParams }: { searchParams: Parametres }) {
  const retour = premier((await searchParams).retour);
  // accès direct sans pré-session : retour à Se connecter, sans message (maquettes v3, écran 2)
  if (!(await cookies()).has(COOKIE_PRE)) redirect(adresseConnexion(null, retour));
  return <FormulaireCode retour={retour} />;
}
