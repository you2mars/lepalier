"use client";
// Message d'une page à la suivante (UX-4), quand la page d'arrivée ne peut pas retrouver ce qui a été fait (invitation
// annulée : la fiche n'existe plus). Les navigations étant complètes (lib/navigation.ts), il est laissé par la page de
// départ dans le stockage de session de l'onglet, puis lu et effacé par la page d'arrivée à son chargement : affiché
// une fois, perdu au rechargement. Un message de confirmation seulement, jamais un jeton ni un code.
import { usePathname } from "next/navigation";
import { createContext, type ReactNode, useContext, useEffect, useState } from "react";
import { Bandeau, type EtatBandeau } from "@/components/ui/Bandeau";

export type Message = { etat: EtatBandeau; texte: string; pour: string };

const CLE = "lepalier.message";
const ETATS: readonly string[] = ["fait", "attention", "erreur"] satisfies EtatBandeau[];

// stockage refusé par le navigateur : le message est perdu, rien ne casse
export function laisserMessage(message: Message): void {
  try {
    sessionStorage.setItem(CLE, JSON.stringify(message));
  } catch {
    // message perdu
  }
}

function reprendreMessage(chemin: string): Message | null {
  try {
    const brut = sessionStorage.getItem(CLE);
    sessionStorage.removeItem(CLE);
    if (brut === null) return null;
    const m = JSON.parse(brut) as Partial<Record<keyof Message, unknown>>;
    if (typeof m.texte !== "string" || typeof m.etat !== "string" || !ETATS.includes(m.etat) || m.pour !== chemin) {
      return null;
    }
    return { etat: m.etat as EtatBandeau, texte: m.texte, pour: chemin };
  } catch {
    return null;
  }
}

const ContexteMessage = createContext<Message | null>(null);

export function MessageFlashProvider({ initial = null, children }: { initial?: Message | null; children: ReactNode }) {
  const [message, setMessage] = useState<Message | null>(initial);
  const chemin = usePathname();
  // une seule lecture, au chargement de la page, après l'hydratation (le serveur ne voit pas ce stockage)
  const [cheminAuChargement] = useState(chemin);
  useEffect(() => {
    const laisse = reprendreMessage(cheminAuChargement);
    if (laisse) setMessage(laisse);
  }, [cheminAuChargement]);
  return <ContexteMessage.Provider value={message}>{children}</ContexteMessage.Provider>;
}

export function BandeauFlash() {
  const message = useContext(ContexteMessage);
  const chemin = usePathname();
  return message && message.pour === chemin ? <Bandeau etat={message.etat} message={message.texte} /> : null;
}
