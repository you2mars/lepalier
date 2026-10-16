// Constat UX (18) : sur un téléphone lent, un formulaire envoyé avant la prise en main de la page par React partait
// en POST vers la page elle-même, qui revenait vidée, sans message. Ce script en ligne, exécuté dès la lecture du
// HTML (avant le JavaScript de Next), annule l'envoi de tout formulaire qui ne porte pas encore data-pret (posé par
// le composant Formulaire à sa prise en main) : rien n'est envoyé, les champs restent remplis, et le même bouton
// fonctionne une fois le formulaire prêt.
import { headers } from "next/headers";

export const SCRIPT_ENVOI_APRES_PRISE_EN_MAIN =
  'document.addEventListener("submit",function(e){var f=e.target;if(!(f instanceof HTMLFormElement&&f.hasAttribute("data-pret")))e.preventDefault()},true);';

export async function EnvoiApresPriseEnMain() {
  // nonce de la politique de sécurité (middleware) : sans lui, le navigateur refuserait le script
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  return <script nonce={nonce} dangerouslySetInnerHTML={{ __html: SCRIPT_ENVOI_APRES_PRISE_EN_MAIN }} />;
}
