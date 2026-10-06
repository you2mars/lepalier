# front

Next.js 15 en BFF (ADR, `SPEC_TECHNIQUE`), règles d'écriture dans `front/CLAUDE.md`, textes dans `src/textes.ts`,
libellés d'identity lus dans `contracts/libelles/identity.json`.

- `npm ci` puis `npm run dev` (sans nginx, les appels `/api` ne répondent pas) ;
- `npm run lint`, `npm run typecheck`, `npm test` (vitest) ; `make audit` à la racine pour `npm audit`.
