import { render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { SignalHydratation } from "./SignalHydratation";

afterEach(() => document.documentElement.removeAttribute("data-hydrate"));

describe("SignalHydratation", () => {
  it("data-hydrate posé sur <html> une fois la page prise en main", () => {
    render(<SignalHydratation />);
    expect(document.documentElement.hasAttribute("data-hydrate")).toBe(true);
  });
});
