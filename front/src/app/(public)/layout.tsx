// Écrans hors connexion (maquettes v3, § 0.1) : nom de l'application, puis le contenu ; pas de menu.
import type { ReactNode } from "react";
import { CadrePublic } from "@/components/cadre/CadrePublic";

export default function MiseEnPagePublique({ children }: { children: ReactNode }) {
  return <CadrePublic>{children}</CadrePublic>;
}
