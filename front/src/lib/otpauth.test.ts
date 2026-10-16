import { describe, expect, it } from "vitest";
import { cleDeLUri } from "./otpauth";

const URI =
  "otpauth://totp/LePalier:Mme%20Durand?secret=JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP&issuer=LePalier&algorithm=SHA1&digits=6&period=30";

// Clé à saisir à la main dans l'application, par groupes de 4 (maquettes v3, § 0.5).
describe("cleDeLUri", () => {
  it("groupes de 4 caractères", () => {
    expect(cleDeLUri(URI)).toEqual(["JBSW", "Y3DP", "EHPK", "3PXP", "JBSW", "Y3DP", "EHPK", "3PXP"]);
  });

  it("dernier groupe plus court si la clé ne tombe pas juste", () => {
    expect(cleDeLUri("otpauth://totp/LePalier:x?secret=ABCDEFGHIJ")).toEqual(["ABCD", "EFGH", "IJ"]);
  });

  it.each([["https://exemple.fr/?secret=ABCD"], ["otpauth://totp/LePalier:x"], ["pas une adresse"]])(
    "%s : aucune clé",
    (uri) => {
      expect(cleDeLUri(uri)).toEqual([]);
    },
  );
});
