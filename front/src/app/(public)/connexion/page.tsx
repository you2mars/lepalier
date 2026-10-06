import type { Metadata } from "next";
import { FormulaireConnexion } from "./FormulaireConnexion";

export const metadata: Metadata = { title: "Se connecter — LePalier" };

type Parametres = Promise<Record<string, string | string[] | undefined>>;

function premier(valeur: string | string[] | undefined): string | null {
  return (Array.isArray(valeur) ? valeur[0] : valeur) ?? null;
}

export default async function Page({ searchParams }: { searchParams: Parametres }) {
  const parametres = await searchParams;
  return <FormulaireConnexion motif={premier(parametres.motif)} retour={premier(parametres.retour)} />;
}
