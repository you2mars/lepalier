# LePalier — synthèse des spécifications (fonctionnelle + technique)

Les specs complètes (`SPEC_FONCTIONNELLE.md`, `SPEC_TECHNIQUE.md`) font foi ; cette synthèse donne le contexte minimal pour travailler sans les relire entièrement.

## 1. Contexte
- Immeuble d'environ 20 lots détenu par une **SCI à l'IR**, sans comptable ; **tous les lots loués vides** ; l'option meublée existe mais est désactivée par défaut (garde-fou fiscal APP-SCI-05 : alerte dès que les recettes meublées dépassent 8 % des recettes, seuil de bascule à l'IS ≈ 10 %).
- **Compteur d'eau général unique** : relevés mensuels, répartition par clé (tantièmes par défaut) × jours d'occupation, régularisation annuelle.
- Échanges avec les locataires : **e-mail + courrier papier** ; API La Poste préparée (v2) derrière un adaptateur.
- Utilisateurs : **gérant** (admin), **associés** (lecture + exports + commentaires), **opérateur** (saisie) ; certains sont peu à l'aise avec l'informatique → charte UX stricte.
- Accessible depuis **Internet**, hébergée sur un **VPS Hetzner CPX32** dédié, nginx en frontal, volume LUKS (déverrouillage manuel via WireGuard après redémarrage).

## 2. Besoins fonctionnels clés (références APP-)
- Référentiel : SCI, associés, immeuble, lots (tantièmes, DPE), locations (type de bail, versions de loyer/charges), locataires, garants (APP-REF-01…07, APP-SCI-01…05, APP-USR-01…06).
- Documents : bail vide (+ meublé en option), annexes, EDL, avenants, congés, avis, quittance, reçu, régularisation, relances, publipostage, PDF/A immuables (APP-DOC-01…08).
- Échéancier : une échéance par mois, avis automatique J-10, **paiement validé à la main**, quittance générée seulement au statut `payee`, reçu partiel, retard à J+10, relances manuelles (APP-ECH-01…10).
- Eau et charges : relevés, factures, répartition, régularisation annuelle, provision proposée, forfait meublé exclu de la régularisation (APP-EAU-01…05, APP-CHG-01…07).
- Automatisations et calendrier : avis, quittance, assurance (+30 j relance), révision IRL, régularisation, échéances de bail, relevé, diagnostics, DPE, part meublée, export fiscal (APP-AUT-01…05).
- Envois : routage e-mail/papier par type de document, lot d'impression (enveloppe à fenêtre), registre des envois, recommandés saisis à la main en v1 (APP-ENV-01…07, APP-POST-01…05).
- Veille juridique : INSEE (IRL structuré), Légifrance/PISTE optionnel, RSS service-public/ANIL/JO, scoring par mots-clés, qualification manuelle (APP-VJ-01…06).
- Tableaux de bord global et par locataire, formules figées (APP-TB-01…07, § 10.4).
- Non fonctionnel : 2FA, rôles vérifiés serveur, PDF/A 10 ans, sauvegardes, RGPD (purge 5 ans), exports 2072 reportables ligne à ligne.

## 3. Architecture technique (références TEC-)
| Service | Possède | Publie | Consomme |
| --- | --- | --- | --- |
| identity | utilisateurs, sessions, TOTP, rôles | utilisateur.* | — |
| referentiel | SCI, associés, immeuble, lots, locations(+versions), locataires, garants, clé | location.demarree / version_changee / terminee, locataire.modifie, lot.modifie, diagnostic.enregistre, cle.changee, demande.attestation | document.emis, revision.appliquee |
| facturation | échéances, paiements, rappels, révisions | echeance.emise / payee / partielle / en_retard, paiement.saisi, revision.preparee / appliquee | location.*, irl.publie, regularisation.emise, document.emis |
| charges-eau | relevés, factures d'eau, charges, répartitions, régularisations | releve.saisi, facture.enregistree, charge.enregistree, regularisation.preparee / emise, conso.alerte | location.*, lot.modifie, cle.changee |
| documents | gabarits, documents, fichiers (volume `files`) | document.emis / annule, fichier.importe | echeance.emise / payee, paiement.saisi, regularisation.emise, revision.appliquee, demande.attestation, commandes HTTP |
| envois | file d'envois, registre, adaptateur postal, SMTP | envoi.prepare / statut_change / preuve_recue / cout_connu | document.emis, locataire.modifie, commandes HTTP |
| veille | items, table IRL, collecteurs | irl.publie, veille.alerte / qualifiee | — |
| reporting | projections, agrégats, exports, tâches | export.pret | tout |

- Bus : **NATS JetStream**, enveloppe commune (`id` UUID v7, `type`, `version`, `occurred_at`, `producer`, `aggregate_id`, `trace_id`, `causation_id`, `payload`), sujet `evt.<service>.<type>.v<n>`, un flux par producteur, rétention illimitée.
- Dépendances : aucun cycle entre facturation, charges-eau, documents, envois sur les arêtes « consumers » ; les retours « ack » (facturation passe `quittancee` sur `document.emis`, referentiel versionne sur `revision.appliquee`) ne publient rien et sont déclarés à part dans `contracts/consumers.yaml`.
- Fiabilité : **outbox** transactionnelle par service + relais ; **inbox** par consommateur ; jobs idempotents (`SKIP LOCKED`, verrou 15 min, 3 tentatives, quarantaine après 5 relivraisons).
- Données : PostgreSQL 16, **une base et un rôle par service**, copies locales `ref_*`, `NUMERIC(12,2)`, suppression logique, journal INSERT seul.
- Passerelle : **nginx** (TLS Let's Encrypt, `auth_request` vers identity, `limit_req`, en-têtes de sécurité, routage `/api/<service>`), identité transmise en en-têtes `X-User-Id`, `X-Role`, `X-Auth-Exp`, `X-Auth-Sig` (HMAC) vérifiés par chaque service.
- Front : Next.js 15 en BFF, ECharts, nonce CSP via `X-Nonce`.
- PDF : WeasyPrint (PDF/A-2b), gabarits Jinja2 versionnés dans `templates/registry.yaml`, fichiers par empreinte SHA-256.
- Observabilité : OpenTelemetry → Tempo, Prometheus, Loki, Grafana sur `/ops` (WireGuard seulement).
- Livraison : GitHub privé → CI → images GHCR → runner auto-hébergé sur le VPS en mode pull (jamais de SSH entrant).

## 4. Règles de calcul à ne jamais réinventer (TEC-CAL)
- Prorata au jour sur le mois civil réel (28–31 jours), `ROUND_HALF_UP` 2 décimales, loyer et charges séparément.
- États de l'échéance : `a_venir → emise → (partielle | payee | en_retard) → quittancee`, `annulee` sauf depuis `quittancee` ; `payee` seulement par saisie d'un paiement.
- Part d'un lot = coût × clé_lot / Σ clés des lots occupés (jour par jour) × jours occupés / jours de la période ; vacance imputée à la SCI ; arrondi « plus fort reste » : somme des parts = coût exact.
- Régularisation = Σ parts par nature − provisions ; nouvelle provision = réel / 12 arrondi à l'euro supérieur ; forfait meublé jamais régularisé.
- Révision IRL = loyer × IRL(T, N) / IRL(T, N-1), 6 décimales puis arrondi ; perdue si non appliquée dans l'année ; jamais sur un indice absent de `ref_irl`.
- Rapprochement quotidien (reporting) : échéance sans avis, `payee` sans quittance, régularisation sans rappel, révision sans version → tâche après 24 h.

## 5. Décisions prises (§ 14 spec technique)
Microservices ; NATS JetStream ; un conteneur par service (API + worker) ; observabilité complète ; Next.js BFF ; **Hetzner CPX32**, exposition directe nginx ; **LUKS manuel** ; **GitHub + GHCR + runner pull** ; bannissement et WAF à trancher (CrowdSec recommandé, WAF optionnel) ; DNS-01 recommandé ; TOTP v1 (WebAuthn envisagé) ; PISTE et résumé LLM à trancher ; enveloppe DL ; La Poste v2 à trancher.

## 6. Lots de livraison
0 Plateforme (socle, identity, CI, contrats) → 1 referentiel + documents (bail imprimé) → 2 facturation + envois (cycle mensuel complet) → 3 charges-eau + veille IRL (régularisation) → 4 reporting complet (clôture d'exercice) → 5 veille complète + meublé → 6 résilience → 7 v2 postale.
