"use client";
// Message d'une page à la suivante (UX-4) : gardé dans la mémoire de la page par le cadre connecté, jamais dans
// l'adresse ni dans le stockage du navigateur ; annoncé pour une page d'arrivée, affiché tant qu'on y est, oublié dès
// qu'on va ailleurs ; perdu au rechargement. Sert quand la page d'arrivée ne peut pas retrouver ce qui a été fait
// (invitation annulée : la fiche n'existe plus).
import { usePathname } from "next/navigation";
import { createContext, type ReactNode, useContext, useEffect, useState } from "react";
import { Bandeau, type EtatBandeau } from "@/components/ui/Bandeau";

export type Message = { etat: EtatBandeau; texte: string; pour: string };

type Contexte = { message: Message | null; annoncer: (message: Message) => void };

const ContexteMessage = createContext<Contexte>({ message: null, annoncer: () => undefined });

export function MessageFlashProvider({ initial = null, children }: { initial?: Message | null; children: ReactNode }) {
  const [message, setMessage] = useState<Message | null>(initial);
  const chemin = usePathname();
  // à chaque changement de page : ailleurs que sur la page d'arrivée, le message est oublié (y compris au retour sur
  // cette page) ; pas à l'annonce, faite depuis la page de départ
  useEffect(() => {
    setMessage((m) => (m && chemin !== m.pour ? null : m));
  }, [chemin]);
  return <ContexteMessage.Provider value={{ message, annoncer: setMessage }}>{children}</ContexteMessage.Provider>;
}

export function useAnnonce(): (message: Message) => void {
  return useContext(ContexteMessage).annoncer;
}

export function BandeauFlash() {
  const { message } = useContext(ContexteMessage);
  const chemin = usePathname();
  return message && message.pour === chemin ? <Bandeau etat={message.etat} message={message.texte} /> : null;
}
