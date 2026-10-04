# Front (Next.js 15, TypeScript) — BFF et interface

- Lis d'abord `docs/UX_CHARTE.md` et `docs/LEXIQUE.md` ; chaque écran passe par `/revue-ux` avant livraison.
- Structure : `src/app/(connecte)/…` pages par tâche ; `src/components/ui/` design system minimal (UX § 9) ; `src/lib/bff.ts` client vers `/api/<service>` avec propagation du cookie et dégradation par bloc ; `src/lib/format.ts` montants et dates fr-FR.
- Composants serveur par défaut ; `"use client"` seulement pour formulaires et graphes.
- CSP : nonce lu dans `headers().get('x-nonce')`, passé aux scripts ; aucun inline sans nonce.
- Tests : Playwright dans `e2e/`, un parcours par écran ; vitest pour `format.ts` et les composants de formulaire.
- Accessibilité : axe-core en test e2e, navigation clavier vérifiée, labels explicites, `aria-live` pour les messages de succès/erreur.
