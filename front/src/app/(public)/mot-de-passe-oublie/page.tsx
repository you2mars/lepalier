import type { Metadata } from "next";
import { FormulaireOubli } from "./FormulaireOubli";

export const metadata: Metadata = { title: "Mot de passe oublié — LePalier" };

export default function Page() {
  return <FormulaireOubli />;
}
