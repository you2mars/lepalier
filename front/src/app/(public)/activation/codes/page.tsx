import { redirect } from "next/navigation";

// Les codes de secours ne vivent que dans la mémoire de la page d'activation : chargée de nouveau, cette adresse
// ne peut plus les afficher ; l'accueil le dit (bandeau « Attention », maquettes v3, écran 4).
export default function Page(): never {
  redirect("/?motif=codes_perdus");
}
