# Front (Next.js 15, TypeScript) — BFF et interface

- Lis d'abord `docs/UX_CHARTE.md` et `docs/LEXIQUE.md` ; chaque écran passe par `/revue-ux` avant livraison.
- Structure : `src/app/(connecte)/…` pages par tâche ; `src/components/ui/` design system minimal (UX § 9) ; `src/lib/bff.ts` client vers `/api/<service>` avec propagation du cookie et dégradation par bloc ; `src/lib/format.ts` montants et dates fr-FR.
- Composants serveur par défaut ; `"use client"` seulement pour formulaires et graphes.
- CSP : nonce lu dans `headers().get('x-nonce')`, passé aux scripts ; aucun inline sans nonce.
- Navigation : toujours complète, par le navigateur (liens `<a>` ordinaires, `allerVers` ou `quitterVers` de `src/lib/navigation.ts`) ; jamais `next/link` ni `push` ou `replace` du routeur de Next, qui perd parfois une navigation sous charge (journal du lot 0, 9 octobre 2026) ; `router.refresh()` seulement pour relire la page en cours. Contrôlé par `src/lib/navigation.test.ts`.
- Tests : Playwright dans `e2e/`, un parcours par écran ; vitest pour `format.ts` et les composants de formulaire.
- Accessibilité : axe-core en test e2e, navigation clavier vérifiée, labels explicites, `aria-live` pour les messages de succès/erreur.
- Champs mot de passe et e-mail : `autocapitalize="none"`, `autocorrect="off"`, `spellcheck="false"`, y compris quand le bouton « Afficher » passe le champ de mot de passe en texte (sinon le correcteur ou la majuscule automatique modifient la saisie).
- Champ e-mail : `type="email"`, `autocomplete="username"`, `inputmode="email"`.
- Champ mot de passe : `autocomplete="current-password"` à la connexion, `autocomplete="new-password"` à la création (activation) et à la réinitialisation.
- Code de vérification (TOTP) : un seul champ, `inputmode="numeric"`, `autocomplete="one-time-code"` ; jamais six cases séparées.
- Styles (préparation d'une refonte graphique) : toutes les couleurs, tailles de texte, polices, espacements, rayons et ombres passent par les variables CSS du bloc `:root` de `src/app/globals.css` ; aucune valeur en dur dans les composants ni les écrans, aucun style en ligne, aucune autre feuille de style. Les écrans n'ont pas de style propre : ils utilisent les composants de `src/components/ui`. Contrôlé par `src/app/styles.test.ts`.
