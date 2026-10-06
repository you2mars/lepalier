// Paramètres d'adresse des pages (searchParams de Next) : la première valeur seulement, jamais une liste.
export type Parametres = Promise<Record<string, string | string[] | undefined>>;

export function premier(valeur: string | string[] | undefined): string | null {
  return (Array.isArray(valeur) ? valeur[0] : valeur) ?? null;
}
