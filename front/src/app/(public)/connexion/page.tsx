import type { Metadata } from "next";
import { type Parametres, premier } from "@/lib/parametres";
import { FormulaireConnexion } from "./FormulaireConnexion";

export const metadata: Metadata = { title: "Se connecter — LePalier" };

export default async function Page({ searchParams }: { searchParams: Parametres }) {
  const parametres = await searchParams;
  return <FormulaireConnexion motif={premier(parametres.motif)} retour={premier(parametres.retour)} />;
}
