// Navigation complète (pas celle du routeur de Next) : après une déconnexion, aucune page connectée ne reste en
// mémoire, et la page quittée est remplacée dans l'historique (R0-08).
export function quitterVers(adresse: string): void {
  window.location.replace(adresse);
}
