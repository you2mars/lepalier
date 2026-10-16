import type { Metadata } from "next";
import { Activation } from "./Activation";

export const metadata: Metadata = { title: "Activer mon compte — LePalier" };

export default function Page() {
  return <Activation />;
}
