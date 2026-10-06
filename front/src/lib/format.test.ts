import { describe, expect, it } from "vitest";
import { dateEnToutesLettres, dateHeureParis, heureParis } from "./format";

// Mêmes cas que libs/commun/tests/test_dates.py : une seule règle d'affichage des dates (UX-6, UX-13).
describe("dates à l'heure de Paris", () => {
  it.each([
    ["2026-07-14T23:30:00Z", "mercredi 15 juillet 2026", "1 h 30"],
    ["2026-01-10T23:30:00Z", "dimanche 11 janvier 2026", "0 h 30"],
    ["2026-10-04T12:05:00Z", "dimanche 4 octobre 2026", "14 h 05"],
    ["2026-10-01T08:00:00Z", "jeudi 1er octobre 2026", "10 h 00"],
    ["2026-10-25T00:59:00Z", "dimanche 25 octobre 2026", "2 h 59"],
    ["2026-10-25T01:00:00Z", "dimanche 25 octobre 2026", "2 h 00"],
  ])("%s → %s à %s", (instant, date, heure) => {
    expect(dateHeureParis(instant)).toEqual([date, heure]);
    expect(dateEnToutesLettres(instant)).toBe(date);
    expect(heureParis(instant)).toBe(heure);
  });

  it("refuse un instant sans fuseau horaire", () => {
    expect(() => dateHeureParis("2026-10-04T12:05:00")).toThrow(/fuseau/);
  });
});
