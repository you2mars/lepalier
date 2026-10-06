// Chargement (UX-30) : squelette de 3 cartes à la place de la liste.
export default function Chargement() {
  return (
    <div aria-busy="true">
      {[0, 1, 2].map((i) => (
        <div key={i} className="squelette squelette-carte" />
      ))}
    </div>
  );
}
