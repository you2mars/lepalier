import { describe, expect, it } from "vitest";
import { politiqueDeSecurite } from "./csp";

describe("politiqueDeSecurite", () => {
  it("n'autorise que les scripts et styles portant le nonce de nginx", () => {
    const csp = politiqueDeSecurite("abc123");
    expect(csp).toContain("script-src 'self' 'nonce-abc123' 'strict-dynamic'");
    expect(csp).toContain("style-src 'self' 'nonce-abc123'");
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("base-uri 'none'");
    expect(csp).toContain("form-action 'self'");
    expect(csp).not.toContain("unsafe-inline");
    expect(csp).not.toContain("unsafe-eval");
  });

  it("refuse un nonce absent ou mal formé", () => {
    expect(() => politiqueDeSecurite("")).toThrow();
    expect(() => politiqueDeSecurite("abc'; script-src *")).toThrow();
  });
});
