// Politique de sécurité du contenu : nonce transmis par nginx dans X-Nonce ($request_id) ; à défaut (next dev
// sans nginx), un nonce aléatoire. Next.js reprend le nonce de l'en-tête CSP de la requête pour ses scripts.
import { type NextRequest, NextResponse } from "next/server";
import { politiqueDeSecurite } from "@/lib/csp";

export function middleware(requete: NextRequest) {
  const nonce = requete.headers.get("x-nonce") ?? crypto.randomUUID().replaceAll("-", "");
  const csp = politiqueDeSecurite(nonce);
  const entetes = new Headers(requete.headers);
  entetes.set("x-nonce", nonce);
  entetes.set("Content-Security-Policy", csp);
  const reponse = NextResponse.next({ request: { headers: entetes } });
  reponse.headers.set("Content-Security-Policy", csp);
  return reponse;
}

export const config = { matcher: [{ source: "/((?!_next/static|_next/image|favicon.ico).*)" }] };
