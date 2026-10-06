// Chargement (UX-30) : squelette à la place du contenu, annoncé par aria-busy, sans texte.
export function Squelette({ forme = "bloc", nombre = 1 }: { forme?: "bloc" | "carte"; nombre?: number }) {
  return (
    <div aria-busy="true">
      {Array.from({ length: nombre }, (_, i) => (
        <div key={i} className={forme === "carte" ? "squelette squelette-carte" : "squelette"} />
      ))}
    </div>
  );
}
