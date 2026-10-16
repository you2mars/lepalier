// Bloc encadré (design system § 9) : information à lire avant de commencer.
import type { ReactNode } from "react";

export function Encadre({ children }: { children: ReactNode }) {
  return <div className="encadre">{children}</div>;
}
