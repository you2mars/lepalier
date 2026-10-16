// Chargement (UX-30) : squelette de 3 cartes à la place de la liste.
import { Squelette } from "@/components/ui/Squelette";

export default function Chargement() {
  return <Squelette forme="carte" nombre={3} />;
}
