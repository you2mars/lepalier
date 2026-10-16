// Politique de sécurité du contenu (CSP) : scripts et styles autorisés seulement avec le nonce que nginx
// transmet dans X-Nonce ($request_id), lu par le middleware.

const NONCE = /^[A-Za-z0-9+/=_-]+$/;

export function politiqueDeSecurite(nonce: string): string {
  if (!NONCE.test(nonce)) throw new Error("nonce absent ou mal formé");
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    `style-src 'self' 'nonce-${nonce}'`,
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ");
}
