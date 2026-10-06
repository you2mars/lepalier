// Liste de codes à recopier (codes de secours) : liste numérotée nommée, police à chasse fixe de 18 px.
export function ListeCodes({ codes, libelle }: { codes: string[]; libelle?: string }) {
  return (
    <ol className="codes" aria-label={libelle}>
      {codes.map((code) => (
        <li key={code}>{code}</li>
      ))}
    </ol>
  );
}
