"use client";
// Menu stable (UX-9) : à gauche sur ordinateur, en bas sur mobile et sous 48 rem de largeur utile (zoom 200 %) ;
// « Administration » pour le gérant seulement ; page en cours signalée (aria-current).
import { usePathname } from "next/navigation";
import type { Role } from "@/lib/session";
import { TEXTES } from "@/textes";

const ENTREES = [
  { href: "/", libelle: TEXTES.cadre.aFaire, roles: ["gerant", "associe", "operateur"], prefixe: null },
  {
    href: "/administration/utilisateurs",
    libelle: TEXTES.cadre.administration,
    roles: ["gerant"],
    prefixe: "/administration",
  },
] as const;

export function Menu({ role }: { role: Role }) {
  const chemin = usePathname();
  return (
    <nav className="menu" aria-label={TEXTES.cadre.menuPrincipal}>
      <ul>
        {ENTREES.filter((e) => (e.roles as readonly string[]).includes(role)).map((e) => {
          const courante = e.prefixe ? chemin === e.prefixe || chemin.startsWith(`${e.prefixe}/`) : chemin === e.href;
          return (
            <li key={e.href}>
              <a href={e.href} aria-current={courante ? "page" : undefined}>
                {e.libelle}
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
