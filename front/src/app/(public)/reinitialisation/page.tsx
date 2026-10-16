import type { Metadata } from "next";
import { FormulaireReinitialisation } from "./FormulaireReinitialisation";

export const metadata: Metadata = { title: "Choisir un nouveau mot de passe — LePalier" };

export default function Page() {
  return <FormulaireReinitialisation />;
}
