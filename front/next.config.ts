import type { NextConfig } from "next";

// Libellés partagés lus dans ../contracts/libelles (écrits une seule fois, aussi lus par identity).
const config: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  experimental: { externalDir: true },
  async headers() {
    // Pages connectées jamais gardées en cache : « Précédent » après déconnexion n'affiche rien (R0-08).
    return [{ source: "/:chemin*", headers: [{ key: "Cache-Control", value: "no-store" }] }];
  },
};

export default config;
