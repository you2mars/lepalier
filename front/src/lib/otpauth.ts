// Clé de l'application d'authentification lue dans l'URI otpauth:// d'identity, par groupes de 4 caractères pour
// la saisie à la main (maquettes v3, § 0.5).
const GROUPE = 4;

export function cleDeLUri(uri: string): string[] {
  let adresse: URL;
  try {
    adresse = new URL(uri);
  } catch {
    return [];
  }
  const secret = adresse.protocol === "otpauth:" ? (adresse.searchParams.get("secret") ?? "") : "";
  const groupes: string[] = [];
  for (let i = 0; i < secret.length; i += GROUPE) groupes.push(secret.slice(i, i + GROUPE));
  return groupes;
}
