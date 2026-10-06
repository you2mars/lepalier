// Rappel visible en permanence, même pendant le défilement (« Ne fermez pas cette page… »).
import type { ReactNode } from "react";

export function RappelPermanent({ children }: { children: ReactNode }) {
  return <p className="rappel-permanent">{children}</p>;
}
