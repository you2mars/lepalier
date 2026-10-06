// Dates en toutes lettres et heures à l'heure de Paris (UX-6, UX-13) : mêmes règles que libs/commun (commun.dates).

const FORMAT = new Intl.DateTimeFormat("fr-FR", {
  timeZone: "Europe/Paris",
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  hourCycle: "h23",
});
const AVEC_FUSEAU = /(Z|[+-]\d{2}:?\d{2})$/;

function parties(instant: string | Date): Record<string, string> {
  if (typeof instant === "string" && !AVEC_FUSEAU.test(instant)) {
    throw new Error("instant sans fuseau horaire : impossible de le situer à l'heure de Paris");
  }
  return Object.fromEntries(FORMAT.formatToParts(new Date(instant)).map((p) => [p.type, p.value]));
}

export function dateHeureParis(instant: string | Date): [string, string] {
  const p = parties(instant);
  const jour = Number(p.day) === 1 ? "1er" : String(Number(p.day));
  return [`${p.weekday} ${jour} ${p.month} ${p.year}`, `${Number(p.hour)} h ${p.minute}`];
}

export function dateEnToutesLettres(instant: string | Date): string {
  return dateHeureParis(instant)[0];
}

export function heureParis(instant: string | Date): string {
  return dateHeureParis(instant)[1];
}
