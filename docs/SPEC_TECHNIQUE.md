# Spécifications techniques — Gestion locative personnelle (immeuble SCI, 20 lots)

Oct 3, 2026 · @You2Mars

## 1. Objet, périmètre et principes d'architecture

Ce document traduit la [spécification fonctionnelle](https://claude.ai/code/artifact/9b230a3b-2102-4d1d-9763-4c0f2114ec92) en une architecture de microservices : huit services autonomes (API + worker + base dédiée chacun) reliés par un bus d'événements, derrière une passerelle unique, pour une application auto-hébergée, mono-tenant (une SCI, un immeuble, environ 20 lots), multi-utilisateurs et sans interconnexion payante en v1.

**Avertissement sur le choix d'architecture.** À cette volumétrie (≈ 240 échéances et quelques milliers de documents par an), des microservices n'apportent ni gain de performance ni de disponibilité ; ils coûtent un bus, une passerelle, huit bases, de l'observabilité distribuée et des cohérences différées à gérer (consensus des praticiens, voir par exemple les travaux de M. Fowler sur « MonolithFirst » et de S. Newman, *Building Microservices*). Le choix reste défendable pour isoler les domaines, faire évoluer chaque service indépendamment et t'entraîner sur un cas réel. La spec minimise le surcoût : un seul hôte, un seul serveur PostgreSQL, un bus léger, des contrats d'événements versionnés et des services de taille raisonnable (pas de nano-services).

**Contraintes héritées de la spec fonctionnelle**

| Contrainte | Conséquence technique |
| --- | --- |
| Hébergement sur un VPS externe dédié à l'app (décision du 3 octobre 2026, remplace l'auto-hébergement) | Un seul hôte loué, Docker Compose, hébergeur dans l'Union européenne avec accord de sous-traitance RGPD ; données chiffrées au repos (LUKS) car l'hébergeur a l'accès physique ; sauvegardes rapatriées hors de l'hébergeur ; accès d'exploitation par WireGuard depuis chez toi |
| Documents opposables, immuables, conservés 10 ans (APP-DOC-06, APP-NF-04) | Un service `documents` propriétaire unique des fichiers (empreinte SHA-256, PDF/A) ; aucun autre service n'écrit sur le volume |
| Validation manuelle des paiements, quittance conditionnée (APP-ECH-03/05) | Machine à états dans `facturation` ; la quittance est produite par `documents` en réaction à l'événement `echeance.payee` |
| Calculs opposables au centime | Chaque moteur vit dans un seul service ; arithmétique décimale, règles d'arrondi écrites une fois, tests de non-régression |
| Rôles vérifiés côté serveur (APP-USR-05) | Authentification centralisée dans `identity`, autorisation appliquée par chaque service à partir d'une identité signée transmise par nginx |
| Volumétrie faible | Pas de cluster ; un conteneur par service, un bus mono-nœud persistant, un serveur PostgreSQL avec une base par service |
| Cohérence entre services | Événements persistants (outbox) et consommateurs idempotents (inbox) ; cohérence différée acceptée partout sauf dans la saisie des paiements et la génération de la quittance |
| Dépôt de code et livraison | GitHub (dépôt privé) + GHCR pour les images ; déploiement en mode « pull » par un runner auto-hébergé sur le VPS, jamais de SSH entrant depuis la CI |

**Principes directeurs**

- Un service = un domaine métier = une base : `identity`, `referentiel`, `facturation`, `charges-eau`, `documents`, `envois`, `veille`, `reporting`. Chaque service expose une API HTTP (lecture et commandes), tourne son propre worker (jobs planifiés, consommateurs d'événements) et ne lit jamais la base d'un autre service.
- Les données traversent les services par événements versionnés publiés sur un bus persistant ; un service qui a besoin d'une donnée d'un autre en garde une copie locale alimentée par ces événements. Les appels HTTP synchrones entre services sont réservés aux lectures ponctuelles non critiques et aux commandes qui exigent une réponse immédiate.
- Toute écriture métier passe par un service applicatif qui journalise localement et publie son événement dans la même transaction (outbox) ; aucune écriture directe depuis un contrôleur HTTP.
- Tout traitement planifié ou déclenché par événement est idempotent : clé d'idempotence par job, table d'inbox par consommateur.
- Les intégrations externes (SMTP, poste, sources de veille, modèle local) sont des adaptateurs derrière une interface, avec une implémentation « manuelle » ou « simulée » utilisable en test et en v1, chacune dans le service qui la possède.
- Les contrats (OpenAPI par service, schémas d'événements) sont des artefacts versionnés du dépôt, modifiés de façon additive ; un changement incompatible = nouvelle version d'événement consommée en parallèle de l'ancienne.
- L'application est publiée sur Internet derrière un seul nginx durci (§ 11), qui est le seul composant à voir le trafic non authentifié ; tout le reste vit sur des réseaux internes.
- La pile reprend celle déjà maîtrisée (FastAPI, PostgreSQL, Next.js) et y ajoute le strict nécessaire : un bus (NATS JetStream), nginx en passerelle et l'observabilité (OpenTelemetry).

**Conventions** : exigences techniques `TEC-<domaine>-<n°>` ; les renvois `APP-…` pointent vers la spec fonctionnelle ; les noms de services sont en `monospace` ; les événements sont nommés `<agrégat>.<fait>` au passé (`echeance.payee`). Les versions de bibliothèques citées sont celles connues au 3 octobre 2026, à vérifier au moment de l'initialisation du projet. Une première version de ce document décrivait un monolithe modulaire ; elle a été remplacée par cette version microservices le 3 octobre 2026.

## 2. Architecture générale

&#91;embedded content: composants et flux · 8 services, 1 bus\]

Le navigateur, depuis Internet, n'atteint que nginx, qui termine TLS, vérifie la session auprès d'`identity` par `auth_request`, limite le débit puis route vers le front ou vers le service concerné en y attachant l'identité signée ; les services ne partagent ni base ni fichiers et se synchronisent par événements persistants, le HTTP entre services restant limité aux lectures ponctuelles.

**Responsabilités et dépendances**

| Service | Possède | Publie | Consomme |
| --- | --- | --- | --- |
| `identity` | utilisateurs, sessions, TOTP, rôles | `utilisateur.cree`, `utilisateur.role_change`, `utilisateur.suspendu` | — |
| `referentiel` | SCI, associés, immeuble, lots, diagnostics, locations et versions, locataires, garants, clé de répartition | `location.demarree`, `location.version_changee`, `location.terminee`, `locataire.modifie`, `lot.modifie`, `diagnostic.enregistre`, `cle.changee` | `document.emis` (pour lier bail, avenant, EDL à la location) |
| `facturation` | échéances, paiements, rappels, révisions IRL appliquées | `echeance.emise`, `echeance.payee`, `echeance.partielle`, `echeance.en_retard`, `paiement.saisi`, `revision.preparee`, `revision.appliquee` | `location.*`, `irl.publie`, `regularisation.emise`, `document.emis` |
| `charges-eau` | relevés, factures d'eau, charges, répartitions, régularisations | `releve.saisi`, `facture.enregistree`, `charge.enregistree`, `regularisation.preparee`, `regularisation.emise`, `conso.alerte` | `location.*`, `lot.modifie`, `cle.changee` |
| `documents` | gabarits, documents, fichiers (volume `files`) | `document.emis`, `document.annule`, `fichier.importe` | `echeance.emise` (avis), `echeance.payee` (quittance), `paiement.saisi` (reçu partiel), `regularisation.emise`, `revision.appliquee`, commandes HTTP du front |
| `envois` | file d'envois, registre, adaptateur postal, SMTP | `envoi.prepare`, `envoi.statut_change`, `envoi.preuve_recue` | `document.emis` (règles de routage), commandes HTTP (déposer, saisir un statut) |
| `veille` | items de veille, table IRL, collecteurs | `irl.publie`, `veille.alerte`, `veille.qualifiee` | — |
| `reporting` | vues de lecture (agrégats), exports CSV et 2072 | `export.pret` | tous les événements métier ci-dessus |

**Règle d'or des dépendances** : `identity`, `referentiel` et `veille` ne consomment rien (ou presque) ; `reporting` consomme tout et n'est consommé par personne ; aucun cycle n'est admis entre `facturation`, `charges-eau`, `documents` et `envois` sur les consommations qui déclenchent un traitement. Deux consommations sont des **retours** (« ack ») qui clôturent un état chez le producteur amont sans rien publier : `facturation` passe l'échéance à `quittancee` sur `document.emis`, `referentiel` crée la `location_version` sur `revision.appliquee`. Elles sont déclarées à part dans `contracts/consumers.yaml`, exclues du contrôle de cycle (`make contracts`) et vérifiées en revue : un retour qui se mettrait à publier un événement serait une violation de contrat.

## 3. Stack technique et justification des choix

La pile retenue est FastAPI + PostgreSQL + Next.js, celle que tu pratiques déjà, complétée par NATS JetStream comme bus d'événements, Traefik comme passerelle, WeasyPrint pour les PDF et OpenTelemetry pour suivre une requête à travers les services ; chaque service est un paquet Python indépendant construit sur une image commune.

| Couche | Choix | Pourquoi | Alternative écartée |
| --- | --- | --- | --- |
| Langage des services | Python 3.12 | Un seul langage pour les huit services, bibliothèques PDF, décimales, TOTP matures | Mélange de langages (coût de maintenance pour une personne) |
| Framework API | FastAPI + Pydantic v2 | Validation stricte, OpenAPI par service, déjà maîtrisé | Django (trop lourd par service) |
| Accès aux données | SQLAlchemy 2 + Alembic, un historique de migrations par service | Transactions explicites, schémas indépendants | ORM partagé entre services (couplage) |
| Base de données | PostgreSQL 16, un serveur, une base et un rôle par service | Isolation logique sans multiplier les instances ; `NUMERIC`, exclusions, `SKIP LOCKED` | Une instance par service (inutile) |
| Bus d'événements | NATS JetStream (mono-nœud, stockage fichier, flux persistants, consommateurs durables, accusés explicites) | Léger, rejeu depuis une séquence, adapté à un hôte unique | RabbitMQ, Kafka, Redis Streams |
| Fiabilité de publication | Outbox transactionnelle par service + relais vers NATS ; inbox par consommateur | Aucun événement perdu ni appliqué deux fois | Publication directe depuis la transaction |
| Passerelle et exposition Internet | nginx 1.26+ : TLS (Let's Encrypt), `auth_request` vers `identity`, `limit_req`/`limit_conn`, en-têtes de sécurité, routage `/api/<service>`, interrupteur de maintenance ; CrowdSec ou fail2ban en bannissement ; relais VPS en `stream` optionnel (§ 11) | Mûr, lisible, outillage de durcissement abondant, déjà pratiqué sur tes autres projets | Traefik (routage dynamique inutile sur un Compose stable, moins d'options de durcissement), Caddy (forward-auth et limites moins fines), Kong |
| Front | Next.js 15 (App Router, TypeScript) servi derrière nginx, BFF appelant `/api/<service>` ; nonce CSP transmis par nginx | Déjà maîtrisé ; agrégation côté serveur | Micro-frontends |
| Graphes | ECharts | Cartes de chaleur, cascades, frises, export | Recharts |
| Génération PDF | WeasyPrint ≥ 62 (`pdf_variant='pdf/a-2b'`) dans `documents` | PDF/A sans navigateur headless | Chromium headless |
| Observabilité | OpenTelemetry → Tempo/Prometheus, logs JSON (services et nginx) → Loki, `trace_id` propagé en HTTP et dans l'enveloppe des événements | Indispensable pour suivre une chorégraphie | Logs seuls |
| Authentification | `identity` : sessions serveur (cookie `HttpOnly`), Argon2id, TOTP ; nginx convertit la session en en-têtes signés (HMAC) vérifiés par chaque service | Révocation immédiate ; aucun service ne gère de mot de passe | JWT porté par le client |
| Contrats | OpenAPI par service ; JSON Schema des événements dans `contracts/` ; bibliothèque `commun` versionnée | Compatibilité vérifiée en CI | Schémas implicites |
| Conteneurs | Docker Compose : 8 services, `front`, `nginx`, `nats`, `postgres`, `otel-collector`, `grafana` (+ Tempo, Loki, Prometheus), `crowdsec` (ou fail2ban sur l'hôte) | Reproductible sur une VM | Kubernetes (k3s possible en v2) |
| Tests | pytest + hypothesis, tests de contrat, Testcontainers, Playwright, `testssl.sh` et balayage externe pour la surface publique | — | — |

**Option « API + worker séparés »** : chaque service peut être lancé en deux conteneurs (`<svc>-api`, `<svc>-worker`) à partir de la même image, ce qui isole les pannes (un rendu PDF lourd ne ralentit pas l'API) au prix de 8 conteneurs supplémentaires ; la spec retient un conteneur par service en v1 avec deux processus, et laisse le découpage comme simple changement de Compose.

**Exigences**

- TEC-STK-01 — Dépôt unique (monorepo) `services/<nom>/`, `contracts/`, `libs/commun/`, `front/`, `deploy/` ; versions épinglées par service (lock files) ; mise à jour trimestrielle avec exécution complète des tests et des contrats.
- TEC-STK-02 — Sorties réseau par service déclarées dans Compose (réseaux Docker distincts) : seul `envois` atteint le SMTP et La Poste, seul `veille` atteint les sources publiques et le modèle local ; les autres n'ont aucune route sortante.
- TEC-STK-03 — Les montants sont des `Decimal` (Python) et `NUMERIC(12,2)` (base) de bout en bout, y compris dans les événements (sérialisés en chaînes décimales, jamais en nombres flottants JSON).
- TEC-STK-04 — La bibliothèque `commun` ne contient aucune logique métier : enveloppe d'événement, publication outbox, consommation inbox, middleware d'identité, utilitaires décimaux, client HTTP inter-services avec propagation du `trace_id`.

## 4. Modèle de données

Chaque service possède sa base et ses tables ; quand un service a besoin d'une donnée d'un autre, il en tient une copie locale (tables `ref_*`) alimentée par les événements, ce qui évite tout accès croisé. Toutes les tables métier portent `created_at`, `created_by`, `updated_at`, `updated_by`, et celles qui ont une vie juridique ne se suppriment jamais physiquement.

### 4.1 Propriété des données

| Service (base) | Tables maîtres | Copies locales (alimentées par événements) | Tables techniques |
| --- | --- | --- | --- |
| `identity` | `utilisateur`, `session`, `code_secours` | — | `outbox`, `journal` |
| `referentiel` | `sci`, `associe`, `immeuble`, `lot`, `diagnostic`, `location`, `location_version`, `locataire`, `location_locataire`, `garant`, `cle_repartition` | `ref_document` (liens bail/avenant/EDL) | `outbox`, `inbox`, `journal` |
| `facturation` | `echeance`, `paiement`, `rappel`, `revision` | `ref_location` (versions, locataire principal, jour d'échéance), `ref_irl`, `ref_regularisation` | `outbox`, `inbox`, `job`, `journal` |
| `charges-eau` | `releve_eau`, `facture_eau`, `charge`, `repartition`, `regularisation` | `ref_location` (occupation, mode de charges, provisions), `ref_lot` (tantièmes, surface), `ref_cle` | `outbox`, `inbox`, `job`, `journal` |
| `documents` | `gabarit_version`, `document`, `file` | `ref_sci`, `ref_lot`, `ref_location`, `ref_locataire`, `ref_echeance` (montants figés dans le contexte) | `outbox`, `inbox`, `job`, `journal`, `sequence_documents` |
| `envois` | `envoi`, `preuve`, `regle_routage`, `cout` | `ref_document` (métadonnées), `ref_locataire` (canal, adresse, accord démat.) | `outbox`, `inbox`, `job`, `journal` |
| `veille` | `irl`, `veille_item`, `source_etat`, `keyword` | — | `outbox`, `job`, `journal` |
| `reporting` | `agg_mensuel_location`, `agg_mensuel_immeuble`, `agg_eau`, `agg_charges`, `export`, `evenement_brut` (journal d'événements reçus) | tout, sous forme de projections | `inbox`, `job` |

Les définitions détaillées de chaque table maître restent celles du § 4.2 ci-dessous, inchangées ; seule leur localisation change.

### 4.2 Tables maîtres (par service propriétaire, voir § 4.1)

| Table | Champs clés | Contraintes et remarques |
| --- | --- | --- |
| `sci` | dénomination, siren, siège, gérant\_nom, gérant\_signature\_file\_id, familiale (bool), régime = 'IR', clôture = 31/12 | Une seule ligne ; `régime` en CHECK pour empêcher toute autre valeur en v1 |
| `associe` | sci\_id, identité, adresse, parts, date\_entrée, date\_sortie | Somme des parts actives = capital, vérifiée par trigger |
| `immeuble` | adresse, zone\_tendue (bool), total\_tantièmes, compteur\_general\_numero | Une ligne en v1, clé étrangère partout pour l'extension |
| `lot` | immeuble\_id, numéro, étage, surface NUMERIC(7,2), pièces, tantièmes, mode\_location\_autorisé ('vide','meuble','les\_deux'), archivé\_at | `UNIQUE(immeuble_id, numéro)` |
| `diagnostic` | lot\_id, type (DPE, amiante, plomb, électricité, gaz, ERP), classe (DPE), date, expire\_le, file\_id | Index sur `expire_le` pour le calendrier |
| `location` | lot\_id, type\_bail ('vide','meuble'), date\_effet, durée\_mois, date\_fin, loyer\_hc, mode\_charges ('provision','forfait','justificatifs'), charges\_mensuelles, dépôt\_garantie, jour\_échéance (1–28), irl\_trimestre\_ref, irl\_valeur\_ref, date\_révision, statut | Contrainte d'exclusion : deux locations d'un même lot ne se chevauchent pas (`EXCLUDE USING gist (lot_id WITH =, daterange(date_effet, date_fin) WITH &&)`) ; `forfait` interdit si `type_bail='vide'` (CHECK) |
| `location_version` | location\_id, valide\_de, valide\_a, loyer\_hc, charges\_mensuelles, mode\_charges, motif, avenant\_doc\_id | Historisation des montants (APP-REF-05) ; les échéances lisent la version valide à leur date |
| `locataire` | identité, naissance, email, téléphone, adresse\_notification, canal ('email','papier','les\_deux'), accord\_quittance\_demat (bool, date, doc\_id) | — |
| `location_locataire` | location\_id, locataire\_id, rôle ('principal','cotitulaire'), depuis, jusqua | Un seul `principal` actif par location |
| `garant` | location\_id, identité, adresse, montant, durée, acte\_doc\_id | — |
| `echeance` | location\_id, période\_début, période\_fin, loyer\_dû, charges\_dues, rappel\_dû, total\_dû, statut, émise\_le, en\_retard\_le, soldée\_le | `UNIQUE(location_id, période_début)` ; statut en ENUM (§ 5.1) ; jamais supprimée, annulée par `annulée_le` + motif |
| `paiement` | echeance\_id, date, montant, mode, référence, payeur ('locataire','garant','autre'), saisi\_par | Montant > 0 ; la somme des paiements d'une échéance est recalculée par le service, pas stockée |
| `releve_eau` | immeuble\_id, date, index NUMERIC(10,3), motif, photo\_file\_id, saisi\_par | Trigger : index ≥ précédent sauf motif 'remplacement' |
| `facture_eau` | immeuble\_id, fournisseur, période\_début, période\_fin, m3, montant\_abonnement, montant\_conso, montant\_taxes, total\_ttc, file\_id | — |
| `charge` | immeuble\_id, exercice, nature (ENUM aligné sur le décret 87-713), période\_début, période\_fin, montant, récupérable (bool), file\_id | — |
| `cle_repartition` | immeuble\_id, type ('tantiemes','surface','occupants'), valide\_de, valide\_a | Une seule clé valide à une date (exclusion) |
| `regularisation` | location\_id, exercice, décompte JSONB (par nature), provisions\_versées, solde, émise\_le, doc\_id | `UNIQUE(location_id, exercice)` |
| `irl` | trimestre (ex. '2026T2'), valeur NUMERIC(6,2), parution\_jo, source, importé\_le | Clé primaire `trimestre` ; valeur immuable une fois publiée |
| `document` | type, location\_id?, lot\_id?, locataire\_id?, gabarit\_version, file\_id, émis\_le, émis\_par, remplace\_doc\_id?, annulé\_le? | Immuable ; une correction crée une ligne qui pointe `remplace_doc_id` |
| `file` | sha256 (PK), taille, mime, chemin, créé\_le | Jamais modifié ; chemin dérivé de l'empreinte |
| `envoi` | document\_id, destinataire\_locataire\_id, canal, niveau\_service, implémentation ('manuel','laposte'), statut, suivi\_numero, preuve\_depot\_file\_id, ar\_file\_id, coût, réponse\_brute JSONB | Statut en ENUM (§ 8) |
| `veille_item` | source, url, empreinte, publié\_le, titre, résumé, score, qualification, qualifié\_par, qualifié\_le | `UNIQUE(source, empreinte)` |
| `utilisateur` | email, mot\_de\_passe\_hash (Argon2id), totp\_secret\_chiffré, rôle ENUM, associe\_id?, statut, invité\_le, activé\_le | — |
| `session` | id aléatoire 256 bits, utilisateur\_id, créé\_le, expire\_le, ip, user\_agent | Révocation par suppression |
| `journal` | horodatage, utilisateur\_id, action, table, enregistrement\_id, avant JSONB, après JSONB | Table en append-only (droits INSERT seulement pour le rôle applicatif) |
| `job` | type, payload JSONB, planifié\_pour, clé\_idempotence, statut, tentatives, dernière\_erreur, verrouillé\_par, verrouillé\_le | `UNIQUE(type, clé_idempotence)` (§ 6) |

### 4.3 Règles transverses

- TEC-DAT-01 — Montants en `NUMERIC(12,2)`, index de compteur en `NUMERIC(10,3)`, indices en `NUMERIC(6,2)` ; dates civiles en `DATE`, horodatages en `TIMESTAMPTZ` (UTC en base, affichage Europe/Paris) ; identifiants `UUID v7` générés par le service propriétaire et réutilisés tels quels dans les copies locales.
- TEC-DAT-02 — Suppression logique uniquement (`archivé_at`, `annulé_le`) sur lots, locations, documents, échéances, envois ; suppression physique autorisée seulement pour `session`, `job` terminés depuis plus de 90 jours, `outbox` relayées depuis plus de 30 jours, et données purgées au titre du RGPD (§ 11), avec trace dans `journal`.
- TEC-DAT-03 — Un rôle PostgreSQL par service (`svc_<nom>`) limité à sa base, sans DELETE sur les tables immuables et INSERT seul sur `journal` ; un rôle `admin` pour migrations et sauvegardes ; aucun rôle n'a de droit sur deux bases.
- TEC-DAT-04 — `outbox` (par service) : `id`, `type`, `version`, `clé_agrégat`, `payload JSONB`, `trace_id`, `créé_le`, `relayé_le` ; écrite dans la même transaction que la donnée ; relayée vers NATS par le worker (ordre par `id`) ; `inbox` (par consommateur) : `event_id` PK, `traité_le` — un événement déjà présent est acquitté sans effet.
- TEC-DAT-05 — Copies locales `ref_*` : ne contiennent que les champs nécessaires au service, portent `version_evenement` et `recu_le`, et sont reconstructibles à tout moment par rejeu du flux NATS depuis la séquence 1 (procédure de resynchronisation § 12).
- TEC-DAT-06 — Vues matérialisées des agrégats dans `reporting` uniquement, rafraîchies par son worker à réception des événements (différé 60 s, coalescé).
- TEC-DAT-07 — Les ENUM métier sont déclarés une fois dans `contracts/enums.json` et générés dans chaque service (types PostgreSQL + Pydantic) ; ajouter une valeur = une version de contrat + une migration par service concerné.
- TEC-DAT-08 — Index : `echeance(statut, période_début)`, `envoi(statut, créé_le)`, `job(statut, planifié_pour)`, `document(location_id, type, émis_le)`, `journal(table, enregistrement_id)`, `outbox(relayé_le) WHERE relayé_le IS NULL`.

## 5. Moteurs de calcul

Les cinq moteurs restent des fonctions pures sur des `Decimal`, mais chacun vit dans un seul service — échéancier, paiements et révision IRL dans `facturation`, eau-charges et régularisation dans `charges-eau` — et les enchaînements qui traversent plusieurs services sont décrits comme des chorégraphies d'événements (§ 5.6), sans orchestrateur central.

### 5.1 Échéancier

- TEC-CAL-01 — Génération : pour chaque location en cours, le job mensuel crée l'échéance de la période `[1er du mois, fin du mois]` à partir de `location_version` valide au 1er du mois ; clé d'idempotence `(location_id, période_début)`.
- TEC-CAL-02 — Prorata (premier et dernier mois) : `montant × jours_occupés / jours_du_mois`, arrondi `ROUND_HALF_UP` à 2 décimales, appliqué séparément au loyer et aux charges ; le prorata se fait sur le mois civil réel (28 à 31 jours), jamais sur 30.
- TEC-CAL-03 — Machine à états de `echeance.statut` : `a_venir → emise → (partielle | payee | en_retard) → quittancee`, plus `annulee` depuis tout état sauf `quittancee`. Transitions permises : `emise` par l'envoi de l'avis ou à J-10 ; `partielle`/`payee` uniquement par saisie d'un paiement ; `en_retard` par le job quotidien à J+N si non soldée ; `quittancee` par la génération de la quittance après `payee`. Toute autre transition est refusée par le service.
- TEC-CAL-04 — Un rappel (solde de régularisation, rattrapage de révision) est une ligne distincte `rappel_dû` de l'échéance, avec son motif, pour rester lisible sur l'avis et la quittance.

### 5.2 Affectation des paiements

- TEC-CAL-05 — Un paiement est rattaché à une échéance explicite ; `reste_dû = total_dû − Σ paiements` est calculé à la lecture. `reste_dû = 0` → `payee` ; `0 < reste_dû < total_dû` → `partielle`.
- TEC-CAL-06 — Surplus : si `montant > reste_dû`, le service propose la ventilation (surplus vers l'échéance suivante non soldée, sinon vers un arriéré) et enregistre deux paiements liés par un `groupe_id` ; jamais de montant négatif.
- TEC-CAL-07 — Retard d'une échéance = `date du paiement qui la solde − date d'échéance` (jour d'échéance de la location dans le mois) ; non soldée = `aujourd'hui − date d'échéance`. Stocké dans l'agrégat mensuel, recalculé si un paiement est corrigé.

### 5.3 Eau et charges

- TEC-CAL-08 — Consommation entre deux relevés = `index_n − index_{n-1}` ; si le relevé `n` a le motif `remplacement`, la consommation de l'intervalle = `(index_depose − index_{n-1}) + (index_n − index_pose)`, les deux index du changement étant saisis sur le même relevé.
- TEC-CAL-09 — Ventilation d'une facture ou d'une charge à cheval sur deux périodes : au jour, `montant × jours_dans_période / jours_facturés`, arrondi à 2 décimales, le dernier morceau recevant le reste pour que la somme soit exacte.
- TEC-CAL-10 — Part d'un lot sur une période : `coût × clé_lot / Σ clés_lots_occupés × jours_occupés_lot / jours_période`, avec `clés_lots_occupés` évaluée jour par jour quand l'occupation change dans la période (somme de parts journalières). Les jours de vacance sont imputés à la SCI.
- TEC-CAL-11 — Arrondi « au centime, somme exacte » : les parts sont calculées à 6 décimales, arrondies à 2, et la différence entre la somme des arrondis et le coût total est imputée à la part la plus grande (méthode du plus fort reste) — jamais de centime perdu ni créé.
- TEC-CAL-12 — Option sous-compteurs (v2) : si un lot a un compteur, sa part consommation = `m3_lot × prix_moyen_m3_période`, la part fixe suivant TEC-CAL-10 ; les lots sans compteur se partagent le reste.

### 5.4 Régularisation annuelle

- TEC-CAL-13 — Pour chaque location à provisions, par exercice : `Σ parts par nature (TEC-CAL-10) − Σ provisions appelées sur l'exercice`, détaillé par nature dans `regularisation.décompte` (JSONB figé) ; un solde positif crée un `rappel_dû` sur la prochaine échéance, un solde négatif crée un avoir imputé sur la prochaine échéance ou remboursé.
- TEC-CAL-14 — Nouvelle provision proposée = `charges_réelles_exercice / 12`, arrondie à l'euro supérieur, créée comme `location_version` avec motif `regularisation` après validation.
- TEC-CAL-15 — Location au forfait : le moteur calcule la part réelle pour information (écart affiché) mais n'écrit ni rappel ni avoir ; un garde-fou refuse toute régularisation sur une location `forfait`.

### 5.5 Révision IRL

- TEC-CAL-16 — `loyer_révisé = loyer_en_cours × IRL(trimestre_ref, année) / IRL(trimestre_ref, année−1)`, calcul en `Decimal` à 6 décimales, arrondi final `ROUND_HALF_UP` à 2 décimales ; les deux indices sont lus dans la table `irl` et figés dans la lettre.
- TEC-CAL-17 — La révision n'est calculée que si l'indice du trimestre de référence est publié ; sinon le job repasse chaque semaine. Une révision non appliquée dans l'année qui suit sa date est marquée `perdue` (art. 17-1) et ne génère pas de rattrapage.
- TEC-CAL-18 — Zone tendue : à la création d'une location sur un lot occupé dans les 18 mois précédents, le service plafonne le loyer proposé au dernier loyer révisé et exige une justification saisie pour le dépasser.

**Tests exigés** (§ 13) : pour chaque moteur, cas limites figés (mois de février bissextile, entrée le 31, remplacement de compteur, facture sur trois périodes, IRL non publié) et propriétés (somme des parts = coût, prorata monotone, aucune transition d'état interdite).

### 5.6 Enchaînements inter-services

| Enchaînement | Chorégraphie | Garantie | Si une étape échoue |
| --- | --- | --- | --- |
| Cycle mensuel | `facturation` crée l'échéance → `echeance.emise` → `documents` rend l'avis → `document.emis` → `envois` route et dépose → `envoi.statut_change` → `reporting` met à jour | Chaque étape idempotente par `echeance_id` / `document_id` ; l'avis n'est rendu qu'une fois (inbox) | L'échéance existe sans avis ; `documents` retente 3 fois puis crée une tâche ; l'échéance reste `emise` |
| Paiement → quittance | Saisie HTTP sur `facturation` (transaction : paiement + transition `payee` + outbox) → `echeance.payee` → `documents` rend la quittance → `document.emis` → `facturation` passe `quittancee` ; `envois` envoie | Le paiement est acquis dès la réponse HTTP ; la quittance suit en moins d'une minute en fonctionnement normal | Si la quittance n'est pas émise sous 10 min, `facturation` affiche « quittance en attente » et crée une tâche ; aucun rollback du paiement |
| Régularisation | `charges-eau` prépare (`regularisation.preparee`), un gérant valide (HTTP) → `regularisation.emise` → `facturation` crée le rappel ou l'avoir sur la prochaine échéance, `documents` rend la lettre, `envois` l'expédie | Le décompte est figé dans l'événement (montants par nature) ; `facturation` n'a jamais besoin de relire `charges-eau` | Un rappel non créé sous 10 min = tâche ; la lettre peut être réémise sans dupliquer le rappel (inbox) |
| Révision IRL | `veille` publie `irl.publie` → `facturation` calcule, publie `revision.preparee` ; validation gérant (HTTP) → `revision.appliquee` → `documents` rend la lettre ; `referentiel` enregistre une `location_version` par consommation de `revision.appliquee` | Le nouveau loyer n'entre dans les échéances qu'après `revision.appliquee` | Si `referentiel` ne versionne pas, `facturation` reste cohérent (il a sa propre copie) ; une alerte signale l'écart au rapprochement quotidien |
| Entrée d'un locataire | `referentiel` démarre la location (HTTP) → `location.demarree` → `facturation` crée la première échéance proratisée, `charges-eau` ouvre la période d'occupation, `documents` prépare le bail et les annexes (commande HTTP du front), `envois` attend | — | Une location sans échéance après 10 min = tâche |

- TEC-CAL-19 — Chaque enchaînement a un **rapprochement quotidien** dans `reporting` : pour chaque fait attendu (échéance sans avis, `payee` sans quittance, régularisation sans rappel, révision appliquée sans version), un écart de plus de 24 h crée une tâche nominative ; c'est le filet de sécurité de la cohérence différée.
- TEC-CAL-20 — Les événements portent les montants figés (jamais seulement des identifiants) pour que le consommateur n'ait pas à relire l'émetteur et pour que le rejeu reproduise exactement le passé.
- TEC-CAL-21 — Pas de saga avec compensation en v1 : les enchaînements sont tous « en avant » (un paiement saisi n'est jamais annulé par une étape aval) ; les corrections passent par des documents correctifs et des événements d'annulation explicites (`document.annule`, `echeance.annulee`).

## 6. Ordonnanceur et automatisations

Il n'y a pas d'ordonnanceur central : chaque service a son worker, sa table `job` et son planificateur quotidien (04:00 Europe/Paris), et ne planifie que ce qui porte sur ses propres données ; les réactions aux faits des autres services ne sont pas des jobs planifiés mais des consommateurs d'événements. Un jour « manqué » (hôte éteint) est rattrapé au redémarrage, car chaque planificateur génère les jobs de tous les jours écoulés depuis sa dernière exécution.

### 6.1 Catalogue des jobs

| Job | Service | Cadence | Clé d'idempotence | Effet |
| --- | --- | --- | --- | --- |
| `echeancier.generer` | `facturation` | 1er du mois ; et à réception de `location.demarree` | `location_id:période` | Crée l'échéance, publie `echeance.emise` à J-10 (TEC-CAL-01) |
| `avis.declencher` | `facturation` | Quotidien, J-10 | `echeance_id` | Passe l'échéance à `emise` et publie `echeance.emise` (le rendu est fait par `documents` en consommation) |
| `retard.marquer` | `facturation` | Quotidien | `echeance_id:date` | `en_retard` à J+N, publie `echeance.en_retard` |
| `revision.preparer` | `facturation` | Quotidien si `ref_irl` a l'indice ; sinon repasse | `location_id:année` | Calcul, `revision.preparee`, tâche « à valider » |
| `meuble.part` | `facturation` | Mensuel | `mois` | Part des recettes meublées, alerte au seuil |
| `assurance.demander` | `referentiel` | Quotidien, anniversaire du bail, relance +30 j | `location_id:année:n` | Publie `demande.attestation` (consommé par `documents` puis `envois`) |
| `conge.rappeler` | `referentiel` | Quotidien | `location_id:échéance_bail` | Tâche de rappel 7 mois (vide) / 4 mois (meublé) |
| `diagnostic.alerter` | `referentiel` | Quotidien | `diagnostic_id` | Alerte 90 j avant expiration |
| `releve.rappeler` | `charges-eau` | Mensuel | `immeuble_id:mois` | Tâche « saisir le relevé » |
| `conso.surveiller` | `charges-eau` | À chaque `releve.saisi` | `releve_id` | Alerte fuite (+30 %), publie `conso.alerte` |
| `regularisation.preparer` | `charges-eau` | Sur demande ou date paramétrée | `location_id:exercice` | Décompte, `regularisation.preparee` |
| `rendu.executer` | `documents` | À réception d'événements (`echeance.emise`, `echeance.payee`, …) | `type:clé_agrégat` | Rend le PDF, publie `document.emis` |
| `lot_impression.assembler` | `documents` | Quotidien 06:00 | `date` | PDF agrégé des documents papier du jour |
| `envoi.traiter` | `envois` | Continu (file) | `envoi_id` | SMTP ou adaptateur postal, publie `envoi.statut_change` |
| `poste.suivre` | `envois` | Quotidien si adaptateur API actif | `envoi_id:date` | Statuts et preuves |
| `irl.verifier` | `veille` | Hebdomadaire (quotidien 15 j après fin de trimestre) | `trimestre` | Insère dans `irl`, publie `irl.publie` |
| `veille.collecter` | `veille` | Quotidien par source | `source:date` | Collecte, scoring, `veille.alerte` |
| `agg.rafraichir` | `reporting` | Différé 60 s après événements, coalescé | `date` ou `location_id` | Vues matérialisées |
| `rapprochement.quotidien` | `reporting` | Quotidien 05:00 | `date` | Détecte les enchaînements incomplets (TEC-CAL-19) |
| `fiscal.exporter` | `reporting` | 2 janvier | `exercice` | État 2072 et quotes-parts |
| `outbox.relayer` | tous | Continu (toutes les 2 s) | `outbox.id` | Publie vers NATS, marque `relayé_le` |
| `sauvegarde.verifier` | `reporting` | Quotidien | `date` | Contrôle de la sauvegarde de la nuit (§ 12) |
| `rgpd.purger` | `referentiel`, `documents`, `envois` | Mensuel | `mois` | Purge coordonnée par `locataire.purge_demandee` (§ 11) |

### 6.2 Règles

- TEC-JOB-01 — Prise de job par `UPDATE job … WHERE id = (SELECT id FROM job WHERE statut='planifié' AND planifié_pour <= now() ORDER BY planifié_pour FOR UPDATE SKIP LOCKED LIMIT 1)` dans la base du service ; verrou expiré après 15 minutes.
- TEC-JOB-02 — Statuts `planifié → en_cours → terminé | échec` ; 3 tentatives (1, 10, 60 min) puis `échec` et tâche visible ; les erreurs réseau ne comptent pas comme tentative métier.
- TEC-JOB-03 — Consommateurs NATS : un consommateur durable par (service, flux), accusé explicite après commit de la transaction locale (inbox + effet + outbox éventuelle) ; en cas d'exception, pas d'accusé → relivraison avec délai croissant, et après 5 relivraisons l'événement est mis en quarantaine (`evenement_quarantaine`) avec tâche.
- TEC-JOB-04 — Mode « générer sans envoyer » (APP-AUT-01) : drapeau porté par l'événement (`options.sans_envoi`) ; `envois` crée l'`envoi` en `préparé` sans le traiter.
- TEC-JOB-05 — Aucun job ni consommateur n'écrit un statut d'échéance en dehors des transitions autorisées (TEC-CAL-03) ; `payee` n'existe que dans le service de saisie des paiements de `facturation`.
- TEC-JOB-06 — Le planificateur de chaque service est lancé par son worker au démarrage puis chaque jour (`tick`) ; il persiste `dernier_tick` et génère les jobs des jours manqués.
- TEC-JOB-07 — Horloge : décisions en date civile Europe/Paris calculée depuis `now()` de la base du service ; toutes les bases partagent le même serveur, donc la même horloge.
- TEC-JOB-08 — Enveloppe d'événement (bibliothèque `commun`) : `id` (UUID v7), `type`, `version`, `occurred_at`, `producer`, `aggregate_id`, `trace_id`, `causation_id`, `payload` ; sujet NATS `evt.<service>.<type>.v<n>` ; un flux JetStream par service producteur, rétention illimitée (le flux est aussi la source de rejeu, § 12).

## 7. Documents et PDF

Le service `documents` est le seul à rendre des PDF et à écrire sur le volume `files` ; il réagit aux événements des autres services (avis, quittance, reçu, lettres) et aux commandes HTTP du front (bail, avenant, congé), à partir de gabarits Jinja2 versionnés et d'un contexte figé stocké avec chaque document, puis publie `document.emis`.

### 7.1 Chaîne d'émission

1. Déclencheur : un événement consommé (`echeance.payee` → quittance) ou une commande HTTP (`POST /api/documents/{type}`) ; l'inbox garantit qu'un même événement ne produit qu'un document.
2. Le service construit le **contexte** depuis ses copies locales (`ref_sci`, `ref_location`, `ref_locataire`) et depuis les montants figés portés par l'événement ; si une copie locale manque (événement en avance sur `location.demarree`), le rendu est reporté de 60 s puis mis en quarantaine après 5 essais ; le contexte est stocké dans `document.contexte` (JSONB).
3. Le gabarit `templates/<type>/<type_bail>/<version>/document.html.j2` + `print.css` est rendu ; la version est celle déclarée active dans `templates/registry.yaml`.
4. WeasyPrint produit le PDF/A-2b avec métadonnées XMP (titre, type, identifiant, version de gabarit, date, `trace_id`), polices embarquées.
5. Le fichier est écrit sur le volume par empreinte (§ 7.3), la ligne `document` est créée, le `journal` reçoit l'événement et l'outbox publie `document.emis` (métadonnées, destinataire, canal par défaut, empreinte, URL interne de téléchargement) dans la même transaction.
6. `envois` consomme `document.emis` et applique ses règles de routage ; `referentiel` et `facturation` le consomment pour lier le document à la location ou à l'échéance.

### 7.2 Exigences

- TEC-DOC-01 — Un gabarit publié ne change plus : toute modification crée un nouveau dossier de version ; le registre indique la version active et la date d'entrée en vigueur ; les versions antérieures restent dans le dépôt pour rejouer un document ancien à l'identique.
- TEC-DOC-02 — Identifiant lisible imprimé sur chaque PDF : `<TYPE>-<AAAA>-<n° séquentiel immeuble>` (ex. `QUI-2027-0143`), plus l'empreinte courte en pied de page ; la séquence est une `SEQUENCE` PostgreSQL par type et par année.
- TEC-DOC-03 — Gabarits par type de bail : un même type de document peut avoir une variante `vide` et `meuble` ; le registre résout `(type, type_bail) → version`.
- TEC-DOC-04 — Pré-remplissage : un gabarit ne contient aucune valeur en dur ; les champs libres sont déclarés dans `registry.yaml` et validés avant rendu (un congé sans motif ne se rend pas).
- TEC-DOC-05 — Signature image du gérant : PNG stocké comme `file`, inséré par CSS uniquement sur les documents unilatéraux listés dans le registre ; jamais sur bail, avenant, EDL, inventaire.
- TEC-DOC-06 — Variante e-mail : le même contexte rend un corps HTML court (`email.html.j2`) et un texte brut ; le PDF reste la pièce jointe.
- TEC-DOC-07 — Publipostage : le job `avis.emettre` rend N PDF individuels puis un PDF agrégé (concaténation avec `pypdf`, page de garde listant les destinataires et le niveau de service) ; l'agrégé est un `document` de type `lot_impression` lié aux N documents.
- TEC-DOC-08 — Version imprimable : page d'adresse avec fenêtre DL (position normalisée 20 mm du bord gauche, 45 mm du haut, zone 90 × 45 mm, à valider sur ta référence d'enveloppe), adresse sur 6 lignes max, expéditeur en haut à gauche.
- TEC-DOC-09 — État des lieux et inventaire : contexte volumineux (pièces, éléments, photos) ; les photos sont réduites à 1600 px côté long et insérées en JPEG qualité 80, originaux conservés comme `file` ; le PDF reste sous 25 Mo, sinon les photos passent en annexe séparée.
- TEC-DOC-10 — Annulation : `document.annulé_le` + document correctif pointant `remplace_doc_id` ; un PDF annulé reste téléchargeable avec un bandeau « annulé le … » ajouté au rendu de la visionneuse, le fichier d'origine n'étant jamais modifié.

### 7.3 Stockage des fichiers

- TEC-FIL-01 — Chemin = `files/<sha256[0:2]>/<sha256[2:4]>/<sha256>` sur un volume dédié ; écriture dans un fichier temporaire puis `rename` atomique ; droits `0440`, propriétaire du worker, jamais réécrit.
- TEC-FIL-02 — Lecture par l'API via un endpoint authentifié qui vérifie le droit sur l'objet parent (document, relevé, pièce), jamais par URL directe du volume.
- TEC-FIL-03 — Contrôle d'intégrité mensuel : recalcul des empreintes d'un échantillon de 5 % des fichiers et de tous les fichiers de moins de 30 jours ; écart = alerte.
- TEC-FIL-04 — Types acceptés à l'import : PDF, JPEG, PNG, HEIC converti en JPEG à l'import ; taille max 50 Mo ; antivirus hors périmètre (usage personnel), mais aucun fichier importé n'est jamais servi avec un type MIME exécutable.

## 8. Envois : SMTP et adaptateur postal

Le service `envois` reçoit `document.emis`, applique la règle de routage, crée l'`envoi` et le confie à son worker, qui délègue à `EmailSender` (SMTP) ou à `PostalAdapter` (`ManualPostal` en v1, `LaPostePostal` en v2) ; chaque changement de statut est publié (`envoi.statut_change`) pour `reporting` et pour le tableau « à faire ». Le PDF est lu depuis `documents` par HTTP interne (`GET /internal/files/{sha256}`, réseau Docker seulement) au moment du traitement, jamais copié.

### 8.1 Interface `PostalAdapter`

```python
class PostalAdapter(Protocol):
    def quote(self, pli: PliRequest) -> Quote: ...                 # coût estimé avant validation
    def deposit(self, pli: PliRequest) -> DepositResult: ...       # identifiant d'envoi, n° de suivi, statut initial
    def track(self, envoi_ref: str) -> list[TrackingEvent]: ...    # événements normalisés
    def fetch_proofs(self, envoi_ref: str) -> list[ProofFile]: ... # preuve de dépôt, AR, retour
    def cancel(self, envoi_ref: str) -> bool: ...                  # avant dépôt réel seulement

@dataclass(frozen=True)
class PliRequest:
    document_sha256: str
    expediteur: Adresse            # la SCI
    destinataire: Adresse          # 6 lignes normalisées
    niveau: Literal['simple', 'suivi', 'lrar']
    options: frozenset[str]        # ex. {'ar'}
    reference_interne: str         # envoi_id
```

| Statut normalisé `envoi.statut` | `ManualPostal` | `LaPostePostal` |
| --- | --- | --- |
| `prepare` | Document dans le lot d'impression | Pli créé localement, non transmis |
| `depose` | Saisi par l'utilisateur (date + n° pour un recommandé) | Retour de `deposit()` accepté |
| `en_cours` | — | Événement de prise en charge / acheminement |
| `distribue` | Saisi par l'utilisateur ou via API Suivi gratuite | Événement de distribution |
| `avise` | Idem | Événement d'avis de passage (recommandé non retiré) |
| `retourne` | Idem | Événement de retour à l'expéditeur (NPAI, non réclamé) |
| `echec` | — | Dépôt refusé (adresse, format) → tâche |

### 8.2 Exigences

- TEC-ENV-01 — Routage : table `regle_routage` `(type_document, canal_locataire, accord_demat) → (canal, niveau)` dans la base d'`envois`, modifiable par un gérant ; le canal et l'accord du locataire proviennent de la copie locale `ref_locataire` (événement `locataire.modifie`).
- TEC-ENV-02 — SMTP : `aiosmtplib` avec STARTTLS ou TLS implicite, 3 tentatives ; `depose` au code 250 ; `Message-ID` stocké ; `envois` est le seul service autorisé à joindre le serveur SMTP (réseau Docker dédié).
- TEC-ENV-03 — Le choix de l'implémentation postale est une configuration par niveau de service (`simple`, `suivi`, `lrar`).
- TEC-ENV-04 — `LaPostePostal` (v2) : client HTTP (timeout 20 s), clé d'API chiffrée (§ 11), réponse brute conservée, table de correspondance des événements versionnée ; webhook entrant exposé par la passerelle sous `/hooks/laposte` avec secret partagé et validation de signature si le prestataire la fournit, sinon polling quotidien.
- TEC-ENV-05 — Un recommandé n'est déposé que par un utilisateur `gerant` : la commande `POST /api/envois/{id}/deposer` vérifie `X-Role` ; aucune consommation d'événement ne peut déposer un recommandé.
- TEC-ENV-06 — Preuves : fichiers récupérés par l'API ou importés par scan, remis à `documents` par HTTP interne (`POST /internal/files`) qui les stocke et renvoie l'empreinte ; `envois` ne garde que la référence ; mise en demeure sans preuve de dépôt après 10 jours = tâche.
- TEC-ENV-07 — Coût : `quote()` avant validation, coût réel après dépôt ; `envois` publie `envoi.cout_connu` consommé par `reporting` (dépense « frais postaux »).
- TEC-ENV-08 — `FakePostal` (mémoire) pour tests et démonstration ; interdit en production par un garde-fou de configuration au démarrage.
- TEC-ENV-09 — Adresse normalisée sur 6 lignes avec contrôle code postal / commune sur la base open data de La Poste (fichier rafraîchi semestriellement par `envois`) ; RNVP externe seulement dans `LaPostePostal`.
- TEC-ENV-10 — Reprise : si `documents` est indisponible au moment du traitement, l'envoi reste en file (pas d'échec), retenté toutes les 5 minutes pendant 24 h, puis tâche.

## 9. Veille juridique

Le service `veille` est autonome et sans dépendance entrante : ses collecteurs tournent dans son worker, produisent des `veille_item` dédupliqués et scorés, et il publie deux événements, `irl.publie` (donnée structurée consommée par `facturation`) et `veille.alerte` (consommé par `reporting` pour le tableau « à faire ») ; un résumé par modèle local reste une option débrayable.

### 9.1 Collecteurs

| Source | Mode d'accès | Fréquence | Sortie |
| --- | --- | --- | --- |
| INSEE série 001515333 (IRL) | Page de la série en CSV/JSON si disponible, sinon API BDM avec jeton gratuit ; parsing strict (trimestre, valeur, parution) | Hebdomadaire ; quotidienne dans les 15 jours suivant la fin d'un trimestre | Ligne `irl` (jamais de `veille_item`) |
| service-public.fr (IRL) | Page de la fiche F13723, tableau métropole | Même cadence | Valeur de contrôle : un écart avec l'INSEE bloque l'insertion et crée une alerte (APP-VJ-05) |
| Légifrance via PISTE (option) | API « Légifrance » : suivi des textes consolidés listés en configuration (loi 89-462, décrets 87-713, 2015-587, 2015-981, CCH extraits) ; comparaison de la date de dernière modification et diff des articles suivis | Quotidienne | `veille_item` par article modifié, avec l'ancien et le nouveau texte |
| Journal officiel (Légifrance) | Sommaire quotidien RSS/HTML | Quotidienne | `veille_item` filtrés |
| service-public.fr actualités | Flux RSS « Logement » | Quotidienne | `veille_item` |
| ANIL | Flux RSS actualités | Quotidienne | `veille_item` |

### 9.2 Chaîne de traitement

- TEC-VJ-01 — Chaque collecteur implémente `fetch() -> list[RawItem]` et déclare User-Agent, timeout (20 s), limite de taille (2 Mo) et quota (PISTE) ; `veille` est le seul service autorisé à joindre les sources publiques et le modèle local (réseau Docker dédié).
- TEC-VJ-02 — Déduplication par `(source, empreinte SHA-256 du contenu normalisé)` ; une mise à jour crée un item lié au précédent (`remplace_item_id`).
- TEC-VJ-03 — Scoring par dictionnaire pondéré (`veille/keywords.yaml`), seuil paramétré ; items sous le seuil conservés 90 jours.
- TEC-VJ-04 — Résumé optionnel par modèle local (API compatible OpenAI sur le réseau local), prompt fixe, nom et version du modèle stockés ; aucune donnée de l'app n'est transmise.
- TEC-VJ-05 — Qualification par `PATCH /api/veille/items/{id}` (gérant) ; `impact_gabarits` publie `veille.qualifiee` consommé par `documents` qui crée une tâche sur le registre des gabarits.
- TEC-VJ-06 — IRL : insertion dans `irl` par le collecteur INSEE (contrôle croisé service-public) ou saisie manuelle d'un gérant avec justificatif ; publication `irl.publie` v1 `{trimestre, valeur, parution_jo, source}` ; valeur immuable ; `facturation` ne calcule jamais une révision sur un indice absent de sa copie `ref_irl`.
- TEC-VJ-07 — Résilience : un job par source ; 7 jours d'échec consécutifs = alerte ; dernier contenu réussi conservé pour diff.

**Note sur PISTE** : l'inscription gratuite impose des CGU et des quotas ; le collecteur est livré désactivé, avec la configuration prête, pour que la décision reste la tienne (point ouvert § 14).

## 10. API, permissions et interface

nginx expose une seule origine publique : `/` vers le front, `/api/<service>/…` vers le service correspondant après `auth_request` sur `identity`, qui renvoie `X-User-Id`, `X-Role` et une signature HMAC que nginx réinjecte et que chaque service vérifie ; le front Next.js agrège côté serveur les appels à plusieurs services (BFF) pour que le navigateur ne connaisse jamais le découpage.

### 10.1 Ressources principales

| Préfixe | Service | Routes principales | Remarques |
| --- | --- | --- | --- |
| `/api/identity` | `identity` | `POST /auth/login`, `/auth/totp`, `/auth/logout`, `POST /users/invite`, `PATCH /users/{id}` ; `GET /auth/verify` appelé par nginx (`auth_request`), jamais routé au public | Seul préfixe sans en-têtes d'identité entrants ; `limit_req` strict sur `/auth/*` |
| `/api/referentiel` | `referentiel` | `GET/POST/PATCH /lots`, `/locations`, `/locataires`, `/garants`, `/diagnostics`, `GET/PATCH /sci`, `/associes`, `/cle-repartition` | Pas de `DELETE` ; archivage par `PATCH` ; `POST /locations` publie `location.demarree` |
| `/api/facturation` | `facturation` | `GET /echeances?periode=&statut=&lot=`, `POST /echeances/{id}/paiements`, `POST /echeances/{id}/annuler`, `GET/POST /revisions/{id}/appliquer` | La saisie de paiement est la seule route produisant `payee` |
| `/api/charges-eau` | `charges-eau` | `POST /releves`, `/factures-eau`, `/charges`, `GET /repartition?periode=`, `POST /regularisations/simuler`, `POST /regularisations/{location}/emettre` | Simulation sans écriture |
| `/api/documents` | `documents` | `POST /documents/{type}`, `GET /documents/{id}`, `GET /documents/{id}/pdf`, `POST /documents/{id}/annuler`, `POST /files`, `GET /files/{sha256}`, `GET /gabarits` | Rendu synchrone sous 3 s, sinon différé ; `/files` est la seule route acceptant 50 Mo (nginx) |
| `/api/envois` | `envois` | `GET /envois`, `POST /envois/{id}/deposer`, `/statut`, `/preuves`, `GET /lot-impression/{date}`, `GET/PATCH /regles-routage` | Transitions contrôlées (§ 8) |
| `/api/veille` | `veille` | `GET /items`, `PATCH /items/{id}`, `GET /irl`, `POST /irl` | — |
| `/api/reporting` | `reporting` | `GET /dashboards/global`, `GET /dashboards/locations/{id}`, `GET /taches`, `GET /exports/csv`, `GET /exports/2072`, `GET /journal`, `GET /sante` | Vues de lecture ; `/taches` agrège les tâches de tous les services |
| `/internal/*` | tous | `GET /internal/files/{sha256}`, `POST /internal/files`, `GET /internal/healthz`, `GET /internal/ref/...` | Réseau Docker `backend` seulement ; nginx répond 404 ; jeton de service |
| `/hooks/laposte` | `envois` | `POST` | Public en v2 : secret, signature, liste d'IP, `limit_req` |
| `/ops/*` | Grafana | — | Réservé aux adresses WireGuard (`allow`/`deny` nginx) |

### 10.2 Matrice des droits

| Action | Gérant | Associé | Opérateur |
| --- | --- | --- | --- |
| Lire référentiel, échéancier, documents, envois, tableaux de bord | oui | oui | oui (sans quotes-parts des associés) |
| Saisir relevé, facture, charge, pièce, paiement | oui | non | oui |
| Générer quittance, avis, reçu, attestation de loyer | oui | non | oui |
| Créer ou modifier lot, location, bail, avenant, congé, régularisation | oui | non | non |
| Déposer un recommandé, qualifier la veille, modifier gabarits actifs et paramètres | oui | non | non |
| Gérer utilisateurs, automatisations, secrets | oui | non | non |
| Commentaires internes | oui | oui | oui |
| Exports fiscaux et CSV | oui | oui | non |

- TEC-API-01 — Autorisation en deux couches : la passerelle refuse toute requête `/api/*` sans session valide ; chaque service applique `require_role(...)` sur ses routes et un contrôle objet via ses copies locales ; la matrice est testée par service et de bout en bout (§ 13).
- TEC-API-02 — Toute route d'écriture est idempotente par en-tête `Idempotency-Key` (UUID client) conservé 24 h dans le service concerné.
- TEC-API-03 — Validation Pydantic stricte (`extra='forbid'`), montants en chaîne décimale, dates ISO ; erreurs 422 détaillées ; format d'erreur commun à tous les services (`{code, message, details, trace_id}`).
- TEC-API-04 — Pagination par curseur ; filtres communs `periode`, `lot`, `location`, `statut`.
- TEC-API-05 — Appels HTTP inter-services : uniquement vers `/internal/*`, avec jeton de service par appelant (§ 11), timeout 5 s, pas de rejeu automatique sur les écritures ; toute lecture croisée régulière doit plutôt devenir une copie locale alimentée par événement.
- TEC-API-06 — Chaque réponse porte `X-Request-Id` et `trace_id` ; le front les affiche dans les messages d'erreur pour retrouver la trace dans Grafana.
- TEC-API-07 — Le BFF Next.js ne stocke rien : il relaie le cookie de session vers la passerelle et compose les réponses de plusieurs services (ex. page Location = `referentiel` + `facturation` + `documents` + `envois` + `reporting`) avec un budget de 500 ms et dégradation par bloc si un service ne répond pas.

### 10.3 Interface

| Page | Contenu | Composants notables |
| --- | --- | --- |
| Accueil « à faire » | Tâches en attente triées par échéance, alertes, raccourcis de saisie | Liste actionnable, badges de rôle |
| Immeuble et lots | Grille des lots avec statut, locataire, solde, DPE | Vue plan par étage (simple grille) |
| Location | Onglets : en-tête, échéancier, documents, envois, charges, frise, commentaires ; tableau de bord locataire (APP § 10.3) | ECharts : barres, solde cumulé, heatmap de ponctualité, frise |
| Échéancier mensuel | Toutes les échéances du mois, saisie rapide de paiement (montant, date, mode) | Formulaire optimisé mobile, clé d'idempotence |
| Eau et charges | Relevés (saisie + photo), factures, charges par nature, simulation de régularisation | Courbe conso + bande d'alerte, cascade |
| Documents | Catalogue par type, génération guidée, visionneuse PDF, versions | Formulaire généré depuis `registry.yaml` |
| Envois | File, lot d'impression du jour, registre, saisie des statuts et preuves | Scanner via caméra mobile |
| Tableau de bord global | Widgets APP § 10.2 avec filtres et périodes | ECharts, export PNG/CSV par widget |
| Veille | Fil d'alertes, qualification, table IRL | — |
| Administration | Utilisateurs, rôles, automatisations, gabarits actifs, secrets, journal, sauvegardes | Réservé gérant |

- TEC-UI-01 — Rendu serveur (RSC) pour les pages de lecture, composants client pour formulaires et graphes ; aucune donnée métier dans le `localStorage`.
- TEC-UI-02 — Mobile : saisie de relevé, de paiement et état des lieux utilisables à une main ; photos prises via `<input capture>` et compressées côté client avant envoi (§ 7.2).
- TEC-UI-03 — Tableaux de bord : un appel par tableau, réponse structurée `{widget_id: {definition, series, meta}}` ; les définitions des indicateurs (APP § 10.4) sont renvoyées avec les données et affichées au survol.
- TEC-UI-04 — Accessibilité minimale : contrastes, navigation clavier des formulaires, libellés sur les graphes ; langue : français uniquement.

## 11. Sécurité et données personnelles

L'application est accessible depuis Internet pour les utilisateurs (gérant, associés, opérateur) ; la seule porte d'entrée est nginx, qui termine TLS, vérifie chaque session auprès d'`identity` (`auth_request`), limite le débit, pose les en-têtes de sécurité et ne laisse passer que ce qui est explicitement routé ; WireGuard reste réservé à l'exploitation (Grafana, SSH, base). Derrière nginx, le modèle reste celui des sections précédentes : un seul service qui connaît les mots de passe, des réseaux cloisonnés, des jetons de service et un bus authentifié.

### 11.1 Modèle de menaces de l'exposition Internet

| Menace | Vecteur | Parades (où) |
| --- | --- | --- |
| Force brute, bourrage d'identifiants | `/api/identity/auth/*` | `limit_req` 5 req/min par IP (nginx), verrouillage 15 min après 5 échecs (identity), TOTP obligatoire, bannissement CrowdSec ou fail2ban sur 401/429 répétés |
| Balayage et exploitation de vulnérabilités connues | Toute URL | Un seul port (443), `server_tokens off`, 404 sur tout chemin non routé, WAF OWASP CRS en option, mises à jour trimestrielles et scan d'images |
| Déni de service applicatif | Requêtes lourdes (PDF, exports, dashboards) | `limit_req` global 20 req/s par IP avec rafale, `limit_conn` 20, timeouts courts, corps limité à 1 Mo sauf import de fichiers, rendus lourds différés (§ 7, § 10) |
| XSS, CSRF, clickjacking | Front | CSP avec nonce par requête, `SameSite=Strict`, contrôle `Origin` sur les écritures, `frame-ancestors 'none'`, aucun HTML non échappé |
| Injection | API | Pydantic strict, requêtes paramétrées SQLAlchemy, CRS en détection |
| Téléversement malveillant | `/api/documents/files` | Types et tailles contrôlés, MIME forcé en lecture, volume `noexec`, aucune exécution côté serveur |
| Abus du webhook La Poste (v2) | `/hooks/laposte` | URL avec secret, signature du prestataire si fournie, liste d'IP autorisées, `limit_req`, pas d'effet autre que mise à jour de statut |
| Interception, dégradation TLS | Réseau | TLS 1.2/1.3 seulement, suites Mozilla « intermediate », HSTS, OCSP stapling, enregistrement CAA, HTTP → 301 HTTPS |
| Usurpation d'identité interne | En-têtes `X-User-Id`, `X-Role` forgés par le client | nginx écrase systématiquement ces en-têtes avec les valeurs issues d'`auth_request` (ou vide) ; les services vérifient la signature HMAC |
| Exposition de l'IP du domicile | DNS | Option relais VPS (§ 11.2) |
| Fuite par les journaux | Logs nginx | Pas de cookies, de corps ni d'URL avec données ; IP conservées 30 jours au titre de la sécurité (intérêt légitime, à inscrire au registre § TEC-SEC-16) |

### 11.2 Topologie retenue : toute la plateforme sur un VPS externe

| Élément | Choix | Conséquence |
| --- | --- | --- |
| Où tourne l'app | Un VPS Hetzner CPX32 dédié (4 vCPU AMD, 8 Go, 160 Go NVMe, 20 To de trafic), datacenter dans l'UE, rien d'autre dessus ; DPA Hetzner signé dans la console | nginx, les huit services, NATS, PostgreSQL, l'observabilité et le runner de déploiement y vivent ; IP fixe (IPv4 + IPv6), pas de dépendance à la box ni au réseau domestique |
| Exposition | Directe : 443 (et 80 pour la redirection) ouverts, nginx en frontal (§ 11.3) ; 51820/udp pour WireGuard ; tout le reste fermé par nftables et par le pare-feu Hetzner Cloud (double barrière) | Pas de relais, pas de PROXY protocol ; les limites de débit et le bannissement voient directement l'IP cliente |
| Accès d'exploitation | WireGuard : ton poste (et ton réseau Proxmox pour les sauvegardes) ↔ VPS ; SSH, Grafana (`/ops`), PostgreSQL et NATS uniquement par le tunnel ; SSH par clé, mot de passe désactivé, non exposé publiquement | Un attaquant sur Internet ne voit que nginx |
| Chiffrement au repos | Volume Hetzner Cloud dédié (80 Go au départ, redimensionnable) formaté LUKS2 (`cryptsetup`, AES-XTS) et monté sur `/srv/app` ; le disque système reste non chiffré (OS seulement) ; déverrouillage manuel après un redémarrage : passphrase saisie par SSH à travers WireGuard (`systemd-cryptsetup` + `systemd-tty-ask-password-agent`), les conteneurs ne démarrent qu'une fois le volume monté | Un instantané ou un disque réaffecté ne livre que du chiffré ; un redémarrage demande une intervention de quelques minutes, signalée par l'alerte « volume non monté » ; les redémarrages sont planifiés (mises à jour de noyau) |
| Sauvegardes | Chaque nuit : `pg_dump` par base, instantané JetStream, `restic` chiffré vers deux cibles hors hébergeur : ton NAS via WireGuard et un stockage objet d'un second fournisseur ; les snapshots Hetzner sont un confort, pas la référence | Perte du VPS = restauration sur un CPX32 neuf en moins de 2 h (procédure § 12) |
| Données personnelles | Hetzner sous-traitant RGPD (DPA, UE) ; mention dans le registre (TEC-SEC-16) ; aucune donnée dans la console de l'hébergeur | Conformité documentée sans transfert hors UE |

Alternative abandonnée : auto-hébergement sur ta VM Proxmox avec ou sans relais VPS (gardé dans l'historique du document si tu reviens dessus : la seule différence est l'emplacement du Compose et le sens du tunnel WireGuard).

Dans cette topologie, les clés TLS, les sessions et les données vivent sur le VPS, chiffrées au repos ; ce qui en sort est chiffré (sauvegardes, tunnel) et ce qui y entre passe par nginx.

### 11.3 nginx : configuration de référence

nginx 1.26 ou plus récent, dans un conteneur `nginx` sur les réseaux `edge` et `backend` (il remplace Traefik partout dans ce document). Extraits normatifs :

```nginx
# nginx.conf (http {})
server_tokens off;
limit_req_zone  $binary_remote_addr zone=auth:10m rate=5r/m;
limit_req_zone  $binary_remote_addr zone=api:10m  rate=20r/s;
limit_conn_zone $binary_remote_addr zone=conn:10m;
proxy_cache_path /var/cache/nginx/auth levels=1 keys_zone=auth:1m max_size=10m inactive=30s;
log_format json escape=json '{"t":"$time_iso8601","rid":"$request_id","ip":"$remote_addr",'
  '"m":"$request_method","uri":"$uri","s":$status,"up":"$upstream_addr","ut":"$upstream_response_time","ua":"$http_user_agent"}';

server { listen 80; return 301 https://$host$request_uri; }

server {
  listen 443 ssl;  http2 on;          # + proxy_protocol et set_real_ip_from si relais VPS (§ 11.2 B)
  server_name app.exemple.fr;
  ssl_certificate     /etc/letsencrypt/live/app.exemple.fr/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/app.exemple.fr/privkey.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
  ssl_prefer_server_ciphers off;
  ssl_session_timeout 1d; ssl_session_cache shared:SSL:10m; ssl_session_tickets off;
  ssl_stapling on; ssl_stapling_verify on;
  access_log /var/log/nginx/access.json json;
  client_max_body_size 1m;
  limit_conn conn 20;
  limit_req  zone=api burst=40;
  proxy_read_timeout 30s; proxy_send_timeout 30s; client_body_timeout 15s; client_header_timeout 10s;

  add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
  add_header X-Content-Type-Options nosniff always;
  add_header Referrer-Policy no-referrer always;
  add_header Permissions-Policy "camera=(self), microphone=(), geolocation=(), payment=()" always;
  add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'nonce-$request_id'; style-src 'self' 'nonce-$request_id'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'" always;

  if (-f /etc/nginx/maintenance.flag) { return 503; }   # interrupteur de maintenance
  error_page 503 /maintenance.html;

  # Vérification de session (équivalent forward-auth)
  location = /_auth {
    internal;
    proxy_pass http://identity:8000/auth/verify;
    proxy_pass_request_body off; proxy_set_header Content-Length "";
    proxy_set_header Cookie $http_cookie; proxy_set_header X-Original-URI $request_uri;
    proxy_cache auth; proxy_cache_key "$cookie_session"; proxy_cache_valid 200 10s;
  }

  # Authentification : limitée, sans auth_request
  location /api/identity/auth/ {
    limit_req zone=auth burst=10 nodelay;
    proxy_pass http://identity:8000/auth/;
    include /etc/nginx/proxy_common.conf;
    proxy_set_header X-User-Id ""; proxy_set_header X-Role ""; proxy_set_header X-Auth-Sig ""; proxy_set_header X-Auth-Exp "";
  }

  # API : session vérifiée, identité injectée, en-têtes client écrasés
  location /api/ {
    auth_request /_auth;
    auth_request_set $uid $upstream_http_x_user_id;
    auth_request_set $role $upstream_http_x_role;
    auth_request_set $sig $upstream_http_x_auth_sig;
    auth_request_set $exp $upstream_http_x_auth_exp;
    error_page 401 = @unauth;
    include /etc/nginx/proxy_common.conf;
    proxy_set_header X-User-Id $uid; proxy_set_header X-Role $role;
    proxy_set_header X-Auth-Sig $sig; proxy_set_header X-Auth-Exp $exp;

    location /api/documents/files { client_max_body_size 50m; proxy_request_buffering off; proxy_read_timeout 120s; proxy_pass http://documents:8000/files; }
    location /api/identity/    { proxy_pass http://identity:8000/; }
    location /api/referentiel/ { proxy_pass http://referentiel:8000/; }
    location /api/facturation/ { proxy_pass http://facturation:8000/; }
    location /api/charges-eau/ { proxy_pass http://charges-eau:8000/; }
    location /api/documents/   { proxy_pass http://documents:8000/; }
    location /api/envois/      { proxy_pass http://envois:8000/; }
    location /api/veille/      { proxy_pass http://veille:8000/; }
    location /api/reporting/   { proxy_pass http://reporting:8000/; }
  }
  location @unauth { return 401 '{"code":"unauthenticated"}'; }

  location /hooks/laposte { limit_req zone=auth burst=5; allow 203.0.113.0/24; deny all; proxy_pass http://envois:8000/hooks/laposte; }  # plages réelles à renseigner en v2
  location /internal/ { return 404; }
  location /ops/ { allow 10.8.0.0/24; deny all; proxy_pass http://grafana:3000/; }   # WireGuard seulement
  location / { include /etc/nginx/proxy_common.conf; proxy_set_header X-Nonce $request_id; proxy_pass http://front:3000; }
}
```

`proxy_common.conf` : `proxy_http_version 1.1; proxy_set_header Host $host; proxy_set_header X-Forwarded-Proto https; proxy_set_header X-Real-IP $remote_addr; proxy_set_header X-Request-Id $request_id; proxy_hide_header X-Powered-By; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection $connection_upgrade;`. Le front lit `X-Nonce` pour poser le nonce CSP sur ses balises (`headers()` dans Next.js), ce qui rend la CSP stricte sans `unsafe-inline`.

### 11.4 Exigences périmétriques

- TEC-WEB-01 — Certificats Let's Encrypt renouvelés automatiquement (certbot ou acme.sh) par défi DNS-01 de préférence, sinon HTTP-01 limité à `/.well-known/acme-challenge/` ; clé ECDSA P-256 ; enregistrement DNS CAA ; sous-domaine dédié, pas de joker ; DNSSEC si l'hébergeur DNS le permet.
- TEC-WEB-02 — HSTS avec `preload` seulement après deux semaines sans incident ; test externe (SSL Labs ou `testssl.sh`) à chaque changement TLS, note A attendue.
- TEC-WEB-03 — `auth_request` vers `identity` avec cache de 10 s par cookie ; `identity` répond en moins de 5 ms ; un cookie absent ou invalide donne 401 sans toucher aux services.
- TEC-WEB-04 — Tous les en-têtes d'identité sont écrasés par nginx sur toutes les routes, valeur vide sur celles sans `auth_request` ; test automatisé d'en-têtes forgés.
- TEC-WEB-05 — Bannissement : CrowdSec (agent + bouncer nginx, listes communautaires) ou fail2ban (10 × 401/429 en 10 min → 1 h) ; les adresses WireGuard sont exclues ; choix noté au § 14.
- TEC-WEB-06 — WAF optionnel : ModSecurity v3 + OWASP CRS paranoïa 1, deux semaines en détection, exclusions sur `/api/documents/files` avant blocage.
- TEC-WEB-07 — Journaux nginx JSON sans cookie ni corps → Loki, 30 jours ; alerte sur 4xx/5xx anormaux.
- TEC-WEB-08 — Interrupteur de maintenance par fichier (`maintenance.flag`), page statique 503 (lié à TEC-SEC-17).
- TEC-WEB-09 — Pare-feu hôte (nftables) sur le VPS : entrant 443, 80, 51820/udp seulement ; SSH écoute uniquement sur l'adresse WireGuard ; sortant limité par conteneur via les réseaux Docker ; les ports PostgreSQL, NATS, Grafana ne sont jamais liés à l'interface publique (vérifié par un balayage externe à chaque déploiement de Compose).
- TEC-WEB-10 — Mises à jour de nginx sous 7 jours pour une faille critique ; avis de sécurité nginx, Let's Encrypt et de l'hébergeur ajoutés comme sources du service `veille` (catégorie « sécurité »).
- TEC-WEB-11 — Revue annuelle : balayage externe (`nmap`, `nikto` ou équivalent) depuis l'extérieur, comparaison avec la surface attendue, compte rendu archivé.
- TEC-WEB-12 — Durcissement de l'hôte VPS : image Debian 13 minimale, utilisateur non-root avec `sudo`, `unattended-upgrades` pour les correctifs de sécurité, `fail2ban`/CrowdSec aussi sur SSH, authentification SSH par clé uniquement, console de l'hébergeur protégée par 2FA, mot de passe root de secours conservé hors ligne.

### 11.5 Exigences transverses

| ID | Exigence | Mise en œuvre |
| --- | --- | --- |
| TEC-SEC-01 | Authentification des personnes | `identity` : Argon2id (19 Mio, 2 itérations, parallélisme 1), TOTP RFC 6238 (fenêtre ±1), 10 codes de secours hachés ; verrouillage 15 min après 5 échecs par compte et par IP ; WebAuthn (clé ou empreinte) possible en v2 en remplacement du TOTP, souhaitable dès lors que l'app est publique |
| TEC-SEC-02 | Sessions | Identifiant 256 bits en cookie `HttpOnly; Secure; SameSite=Strict; Path=/`, 12 h glissantes, 30 jours max, révocables ; rotation à la connexion et après le TOTP ; vérifiées à chaque requête par `auth_request` (cache nginx 10 s) |
| TEC-SEC-03 | Identité transmise aux services | En-têtes `X-User-Id`, `X-Role`, `X-Auth-Exp` + `X-Auth-Sig` = HMAC-SHA256 (clé partagée `identity` ↔ services, tournée mensuellement) ; un service rejette toute requête `/api/*` sans signature valide, même venant du réseau interne |
| TEC-SEC-04 | Appels inter-services | Routes `/internal/*` accessibles uniquement sur le réseau Docker `backend` et renvoyées en 404 par nginx ; jeton de service par couple appelant → appelé, chiffré en base ; mTLS en option v2 |
| TEC-SEC-05 | Bus | NATS avec comptes et utilisateurs par service (publication limitée à `evt.<lui>.*`, abonnements limités aux sujets consommés) ; TLS interne ; aucun accès depuis l'extérieur |
| TEC-SEC-06 | Cloisonnement réseau | Réseaux Docker : `edge` (nginx, front), `backend` (services, NATS, PostgreSQL), `egress-mail` (envois), `egress-web` (veille), `egress-laposte` (envois, v2) ; aucun service sur plus de réseaux que nécessaire |
| TEC-SEC-07 | CSRF et en-têtes | `SameSite=Strict` + contrôle `Origin` sur les écritures (dans les services, via `commun`) ; CSP avec nonce, `frame-ancestors 'none'`, HSTS, `Referrer-Policy`, `Permissions-Policy` posés par nginx (§ 11.3) |
| TEC-SEC-08 | Secrets | Clé maîtresse hors conteneur (fichier 0400) ; secrets applicatifs chiffrés AES-256-GCM dans la base du service propriétaire ; clés TLS lisibles par nginx seul ; rotation = re-chiffrement en lot ; aucun secret dans Compose ni dans le dépôt |
| TEC-SEC-09 | Exposition | nginx seul port ouvert (443) selon la topologie du § 11.2 ; WireGuard pour l'exploitation (`/ops`, SSH, base) ; limitation de débit et bannissement (§ 11.4) |
| TEC-SEC-10 | Journal d'audit | `journal` en INSERT seul dans chaque base ; `reporting` en consolide une vue ; export mensuel signé (SHA-256) conservé avec les sauvegardes ; les connexions, échecs et changements de rôle d'`identity` y figurent avec l'IP source |
| TEC-SEC-11 | Fichiers | Servis uniquement par `documents` après contrôle du droit sur l'objet parent ; `Content-Disposition` et MIME forcés ; volume `noexec` dans le seul conteneur `documents` ; téléversement limité à 50 Mo sur une seule route |
| TEC-SEC-12 | Base de données | Un rôle par service, mots de passe distincts, écoute sur `backend` seulement ; `pg_hba` limite chaque rôle à sa base ; sauvegardes chiffrées (§ 12) |
| TEC-SEC-13 | Dépendances et images | `pip-audit`, `npm audit`, Trivy à chaque mise à jour trimestrielle ; images reconstruites depuis Debian officiel |
| TEC-SEC-14 | Purge RGPD | `referentiel` publie `locataire.purge_demandee` (locataire sorti depuis plus de 5 ans) ; `documents`, `envois`, `reporting` purgent et répondent `locataire.purge_effectuee` ; documents contractuels et comptables conservés 10 ans avec le nom seul ; `reporting` vérifie les réponses sous 7 jours |
| TEC-SEC-15 | Minimisation | Pièces d'identité purgées 3 mois après signature ; attestations d'assurance 3 ans ; photos d'état des lieux avec le document ; journaux nginx 30 jours |
| TEC-SEC-16 | Registre des traitements | `docs/rgpd.md` par service ; y ajouter le traitement « journaux de sécurité » (IP, 30 jours, intérêt légitime) et la mention de l'hébergeur du relais si topologie B |
| TEC-SEC-17 | Mode lecture seule et maintenance | Événement `systeme.lecture_seule` (503 sur les écritures) + `maintenance.flag` nginx pour une coupure complète |
| TEC-SEC-18 | Observabilité sans fuite | Traces et logs avec identifiants seulement ; Grafana sur `/ops` accessible uniquement depuis WireGuard, avec son propre compte |
| TEC-SEC-19 | Notification des associés | À la première connexion depuis un nouvel appareil ou une nouvelle IP, e-mail d'information à l'utilisateur ; une connexion refusée après TOTP valide (compte suspendu) alerte le gérant |

**Hors périmètre** : SSO, maillage de services (Istio/Linkerd), antivirus sur les fichiers importés, HSM ou déverrouillage automatique du volume LUKS (le déverrouillage reste manuel après redémarrage).

## 12. Exploitation : déploiement, sauvegardes, supervision

L'app tourne dans une vingtaine de conteneurs sur un VPS Hetzner CPX32 dédié sous Debian 13 (4 vCPU, 8 Go, 160 Go NVMe, volume LUKS additionnel pour les données), déployés par Docker Compose à partir d'images publiées dans GHCR et tirées par un runner GitHub auto-hébergé sur le VPS ; un serveur PostgreSQL héberge huit bases, NATS persiste les événements, une pile d'observabilité suit le tout, et les sauvegardes chiffrées partent chaque nuit vers deux cibles hors hébergeur.

### 12.1 Topologie

| Conteneur(s) | Image | Rôle | Réseaux |
| --- | --- | --- | --- |
| `nginx` | nginx:1.27-alpine (ou image avec ModSecurity si WAF retenu) | TLS, `auth_request`, limites de débit, en-têtes de sécurité, routage `/api/<service>`, page de maintenance, logs JSON | `edge`, `backend` ; 443 et 80 exposés ; volumes `letsencrypt`, `nginx_cache` |
| `certbot` | certbot/dns-\<fournisseur> | Renouvellement DNS-01, rechargement de nginx | sortie HTTPS vers Let's Encrypt et l'API DNS |
| `crowdsec` + bouncer nginx (ou fail2ban sur l'hôte) | crowdsecurity/crowdsec | Lecture des logs nginx et SSH, bannissements | `backend` ; sortie HTTPS vers l'API CrowdSec |
| `front` | build Next.js (node:22-slim) | BFF et rendu des pages, nonce CSP | `edge` |
| `identity`, `referentiel`, `facturation`, `charges-eau`, `documents`, `envois`, `veille`, `reporting` | image commune `app-base` + le paquet du service ; API uvicorn + worker | Services métier | `backend` ; plus `egress-mail` / `egress-laposte` (`envois`), `egress-web` (`veille`) ; volume `files` pour `documents` seul |
| `nats` | nats:2 avec JetStream | Bus d'événements persistant | `backend` ; volume `natsdata` |
| `postgres` | postgres:16 | Huit bases, un rôle par service | `backend` ; volume `pgdata` |
| `otel-collector`, `tempo`, `prometheus`, `loki`, `grafana`, `nginx-exporter`, `node-exporter` | images officielles | Traces, métriques, logs, tableaux d'exploitation, métriques de l'hôte | `backend` ; Grafana derrière nginx sur `/ops`, réservé WireGuard |
| `gh-runner` | runner GitHub Actions auto-hébergé (conteneur dédié avec accès au socket Docker, ou service systemd sur l'hôte) | Tire les images GHCR et exécute `docker compose pull && up -d` sur signal de la CI ; connexion sortante uniquement | `backend` ; sortie HTTPS vers GitHub et GHCR |
| `wireguard` (hôte, pas conteneur) | paquet Debian | Accès d'exploitation depuis ton poste et ton réseau ; canal des sauvegardes vers le NAS | hôte, 51820/udp |
| `restic` (hôte, timer systemd) | paquet Debian | Sauvegardes chiffrées vers NAS (via WireGuard) et stockage objet distant | hôte |
| `mailpit` (preprod seulement) | axllent/mailpit | Bac à sable SMTP | `egress-mail` |

Volumes, tous sur le volume LUKS `/srv/app` monté après déverrouillage : `pgdata`, `natsdata`, `files` (monté `noexec`, `documents` seul), `letsencrypt` (lisible par nginx seul), `nginx_cache`, `grafana_data`, `tempo_data`, `loki_data` ; Docker est configuré pour ne démarrer la pile (`docker compose up`) qu'une fois `/srv/app` monté (unité systemd `RequiresMountsFor`). Configuration par fichier `.env` par service hors dépôt + clé maîtresse sur le volume chiffré ; les secrets applicatifs sont en base chiffrée (TEC-SEC-08), jamais dans `.env`.

### 12.2 Exigences

- TEC-OPS-01 — Déploiement en mode « pull » : la CI publie les images taguées (`ghcr.io/<toi>/<svc>:<sha>`) et le manifeste Compose versionné ; le runner auto-hébergé exécute `docker compose pull <svc> && docker compose up -d <svc>` après les migrations Alembic (conteneur éphémère sous verrou) ; aucun accès SSH entrant depuis GitHub ; un service se déploie seul si son contrat n'a pas changé de façon incompatible ; mode lecture seule (TEC-SEC-17) pendant une migration de `facturation` ou `referentiel`, `maintenance.flag` pendant une restauration.
- TEC-OPS-02 — Ordre de démarrage : `postgres`, `nats` → `identity` → `referentiel`, `veille` → `facturation`, `charges-eau`, `documents` → `envois`, `reporting` → `front` → `nginx` ; `depends_on` avec `healthcheck` ; un service démarre sans ses pairs et rattrape les événements manqués.
- TEC-OPS-03 — Sauvegardes : `pg_dump -Fc` de chaque base + instantané JetStream + `restic` sur `files`, `letsencrypt` et les fichiers de configuration, chaque nuit à 03:00, chiffrés, vers deux cibles hors hébergeur : ton NAS (via WireGuard) et un stockage objet d'un second fournisseur ; rétention 30 jours / 12 mois / 10 ans ; `sauvegarde.verifier` contrôle les artefacts sur les deux cibles ; les instantanés de l'hébergeur sont un confort, jamais la sauvegarde de référence.
- TEC-OPS-04 — Restauration sur un VPS neuf : procédure scriptée (installation Debian, LUKS, Docker, WireGuard, `restic restore`, `docker compose up`, bascule DNS avec TTL 300 s) testée chaque trimestre sur un VPS temporaire, objectif inférieur à 2 h ; rapport daté archivé.
- TEC-OPS-05 — Resynchronisation d'un service : `rebuild <svc>` (copies `ref_*` vidées, consommateurs remis à la séquence 1, rejeu).
- TEC-OPS-06 — Supervision : `/internal/healthz` par service agrégé par `reporting` sous `/api/reporting/sante` ; `node-exporter` pour l'hôte ; alertes Prometheus : volume LUKS non monté après redémarrage, lag de consommateur, échecs de jobs, disque > 85 %, sauvegarde absente sur l'une des deux cibles, certificat expirant sous 14 jours, 401/429/5xx anormaux, bannissements en rafale ; alertes par e-mail via `envois`, et par un second canal indépendant (e-mail direct depuis l'hôte, ou sonde externe type Uptime Kuma chez toi interrogeant `https://app…/healthz` public minimal) pour les pannes de la plateforme elle-même.
- TEC-OPS-07 — Journaux : stdout JSON par conteneur et `access.json` de nginx → Loki (30 jours) ; traces → Tempo ; aucune donnée personnelle hors IP dans les logs nginx.
- TEC-OPS-08 — Horloge : NTP sur l'hôte ; conteneurs en UTC ; la base fait foi.
- TEC-OPS-09 — Mises à jour : `unattended-upgrades` pour l'hôte (sécurité), trimestrielles pour la pile, sous 7 jours pour nginx ou une bibliothèque TLS en cas de faille publiée ; procédure : sauvegarde → tests et contrats en CI → déploiement service par service → santé → `testssl.sh` si nginx a changé → quittance de démonstration.
- TEC-OPS-10 — Environnements : `dev` (Compose allégé sur ton poste), `preprod` (second VPS temporaire ou VM Proxmox chez toi avec copie restaurée, Mailpit, `FakePostal`, certificat auto-signé), `prod` (le VPS) ; garde-fou interdisant `FakePostal` ou un SMTP de test en `prod`.
- TEC-OPS-11 — Dimensionnement : ≈ 2 000 événements et ≈ 600 documents par an ; 4 vCPU / 8 Go / 80 Go couvrent la pile, l'observabilité (≈ 2 Go) et CrowdSec ; prévoir l'extension du volume LUKS avant 70 % d'occupation.
- TEC-OPS-12 — DNS : A/AAAA du sous-domaine vers l'IP du VPS, CAA, TTL 300 s pour pouvoir basculer vers un VPS de secours ; IPv6 activé si l'hébergeur le fournit (nginx écoute sur les deux).
- TEC-OPS-13 — Choix de l'hébergeur : datacenter dans l'UE, DPA disponible, volume additionnel ou disque redimensionnable, instantanés, console avec 2FA, IPv4 fixe, pare-feu réseau de l'hébergeur en complément de nftables ; un VPS dédié à cette app, séparé de tes autres projets, pour qu'une faille ailleurs ne touche pas les données des locataires.

## 13. Tests, qualité et plan de réalisation

La qualité repose sur quatre niveaux — propriétés sur les moteurs, intégration par service, **contrats** entre services (OpenAPI et schémas d'événements), bout en bout sur la plateforme complète — et la livraison se fait service par service, en huit lots dont chacun laisse la plateforme utilisable.

### 13.1 Tests

| Niveau | Cible | Outils | Critère |
| --- | --- | --- | --- |
| Unitaire par propriétés | Moteurs § 5 dans `facturation` et `charges-eau` | pytest + hypothesis | Somme des parts = coût ; prorata borné et monotone ; aucune transition interdite ; invariance à l'ordre des paiements |
| Unitaire sur cas figés | Cas limites (février bissextile, entrée le 31, remplacement de compteur, facture sur 3 périodes, IRL manquant, forfait meublé) | pytest, fixtures JSON versionnées | Résultats attendus au centime |
| Intégration par service | Service + sa base + NATS (Testcontainers) : transactions, outbox relayée, inbox idempotente, jobs rejouables, reprise après crash simulé | pytest, Testcontainers | Deux livraisons d'un même événement = un seul effet ; crash entre commit et acquittement = pas de doublon |
| Contrats | Chaque événement publié valide son JSON Schema ; chaque consommateur déclare les versions qu'il accepte ; OpenAPI de chaque service figé et diffé ; graphe des dépendances sans cycle | Validation de schémas en CI, test de compatibilité (ancien consommateur × nouveau producteur), `openapi-diff` | Un changement incompatible bloque la fusion tant qu'une nouvelle version d'événement n'est pas ajoutée |
| Droits | Matrice § 10.2 par service + passerelle (requête sans session, signature HMAC falsifiée, en-tête `X-Role` injecté sans signature) | pytest paramétré | 100 % des combinaisons ; refus par défaut |
| Documents | Rendu de chaque gabarit actif avec un contexte de référence | WeasyPrint, extraction de texte, `veraPDF` | Aucune régression non revue ; PDF/A valide |
| Chorégraphies | Les cinq enchaînements § 5.6 sur la plateforme Compose complète, y compris avec un service arrêté puis redémarré | pytest + Compose, Playwright | Chaque enchaînement aboutit, le rapprochement quotidien ne remonte aucun écart |
| Bout en bout | Parcours utilisateur : entrée → avis → paiement → quittance ; relevé → régularisation ; impayé → mise en demeure ; invitation d'un associé | Playwright sur `preprod` | Verts avant chaque mise en production |
| Restauration | Sauvegarde → restauration des 8 bases + flux → `sante` → intégrité → rejeu d'un service | Script trimestriel | Compte rendu archivé |

- TEC-QA-01 — Forge : GitHub, dépôt privé (monorepo), compte protégé par 2FA avec clé matérielle, branche `main` protégée (revue par PR même seul, CI obligatoire, commits signés) ; CI GitHub Actions avec détection des services modifiés : lint (`ruff`, `eslint`), typage (`mypy --strict` sur les moteurs, `tsc`), tests du service, tests de contrat de tous les services (toujours exécutés), audits (`pip-audit`, `npm audit`, Trivy), build des images ; pipeline complet sous 15 minutes pour rester dans les 2 000 minutes mensuelles du plan gratuit.
- TEC-QA-02 — Couverture minimale 95 % sur les moteurs, 80 % par service ; une baisse bloque la fusion.
- TEC-QA-03 — Revue des gabarits : tout changement de texte légal passe par une relecture séparée du code, texte source en commentaire du commit.
- TEC-QA-04 — `contracts/CHANGELOG.md` trace chaque version d'événement, producteur, consommateurs et date de retrait prévue.
- TEC-QA-05 — Chaîne de livraison : fusion sur `main` → images construites et publiées dans GHCR (privé, taguées par SHA et par version) et signées (cosign, optionnel) → environnement GitHub `preprod` déployé automatiquement par le runner de preprod → tests de bout en bout → environnement `prod` à approbation manuelle → le runner auto-hébergé du VPS tire et déploie (TEC-OPS-01) ; le runner n'a aucun secret applicatif, seulement l'accès en lecture à GHCR ; les secrets GitHub se limitent au jeton du runner et aux identifiants de publication d'images.
- TEC-QA-06 — Retour arrière : redéployer le tag précédent (`compose` versionné) ; une migration de base n'est jamais destructive dans la même livraison (expansion puis contraction à la livraison suivante), ce qui rend le retour arrière possible sans restauration.

### 13.2 Plan de réalisation

| Lot | Contenu | Prérequis | Livrable utilisable |
| --- | --- | --- | --- |
| 0 — Plateforme | Monorepo, image de base, `commun` (enveloppe, outbox/inbox, identité), Compose (postgres, nats, traefik, observabilité), CI avec tests de contrat, `identity` complet | Décisions § 14 | Connexion, invitations, traces visibles dans Grafana |
| 1 — `referentiel` + `documents` | SCI, lots, locations, locataires ; gabarits bail vide + annexes, EDL ; stockage immuable ; événements `location.*`, `document.emis` | Lot 0 | Rédiger et imprimer un bail et ses annexes |
| 2 — `facturation` + `envois` | Échéances, paiements, machine à états ; avis et quittances par chorégraphie ; SMTP, lot d'impression, registre ; `reporting` minimal (tâches) | Lot 1 | Cycle mensuel complet en autonomie |
| 3 — `charges-eau` + `veille` (IRL) | Relevés, factures, charges, répartition, régularisation ; collecteur INSEE et `irl.publie` ; révision IRL dans `facturation` ; assurance et calendrier dans `referentiel` | Lot 2 | Première régularisation annuelle outillée |
| 4 — `reporting` complet | Projections, vues matérialisées, dashboards global et locataire, exports CSV et 2072, rapprochement quotidien | Lot 3 (≥ 3 mois de données) | Clôture d'exercice |
| 5 — `veille` complet + meublé | Collecteurs RSS/JO (PISTE optionnel), scoring, qualification ; gabarits meublé, inventaire, forfait, garde-fou fiscal | Lot 3 | Veille active, option meublée disponible |
| 6 — Résilience | Procédures de resynchronisation, restauration cohérente testée, alertes Prometheus, quarantaine | Lots 0–4 | Plateforme exploitable sans intervention quotidienne |
| 7 — v2 postale | `LaPostePostal`, webhook, suivi, preuves, coûts | Contrat La Poste, lot 2 | Recommandés sans déplacement |

Ordre de construction à l'intérieur d'un lot : contrats d'événements (schémas + changelog) → migration du service → moteur et tests → consommateurs et jobs → routes → écran (BFF) → test de chorégraphie. Chaque lot se termine par une restauration cohérente réussie, un rejeu complet de `reporting` et un passage des tests de bout en bout.

## 14. Traçabilité et points ouverts

Chaque domaine de la spec fonctionnelle a un service responsable ; onze décisions restent à prendre avant le lot 0, dont trois propres à l'architecture distribuée.

### 14.1 Exigences fonctionnelles → composants

| Spec fonctionnelle | Service responsable | Composants | Référence |
| --- | --- | --- | --- |
| § 3 Référentiel, § 3.1 SCI | `referentiel` | Tables maîtres, événements `location.*`, `lot.*`, `cle.changee` | § 4.1, § 2 |
| § 3.2 Rôles | `identity` + passerelle + chaque service | Sessions, TOTP, `forwardAuth`, signature HMAC, `require_role` | § 10, § 11 |
| § 4 Documents | `documents` | Registre de gabarits, WeasyPrint PDF/A, volume `files`, `document.emis` | § 7 |
| § 5 Échéancier et paiements | `facturation` | Moteur échéancier, machine à états, route de paiement, `echeance.*` | § 5.1–5.2, § 5.6 |
| § 6 Eau et charges | `charges-eau` | Moteur de répartition, régularisation, `regularisation.emise` | § 5.3–5.4 |
| § 7 Automatisations | chaque service (son `job`), rapprochement dans `reporting` | Catalogue des jobs, consommateurs | § 6 |
| § 8 Envois et § 8.3 adaptateur | `envois` | File, `EmailSender`, `PostalAdapter`, `envoi.statut_change` | § 8 |
| § 9 Veille | `veille` | Collecteurs, `irl.publie`, `veille.alerte` | § 9 |
| § 10 Tableaux de bord | `reporting` | Projections, vues matérialisées, `/dashboards/*`, exports | § 4.1, § 10 |
| § 11 Non fonctionnel | plateforme | Traefik, NATS, réseaux cloisonnés, sauvegardes cohérentes, `sante`, purge coordonnée | § 11, § 12 |
| § 13 Points ouverts fonctionnels | — | Repris ci-dessous lorsqu'ils ont un impact technique | § 14.2 |

### 14.2 Décisions techniques à prendre

| # | Décision | Options | Impact |
| --- | --- | --- | --- |
| 1 | Confirmer l'architecture | Microservices (ce document) · monolithe modulaire (version précédente) | Tout le document ; voir l'avertissement § 1 |
| 2 | Bus d'événements | NATS JetStream (recommandé) · RabbitMQ · Redis Streams | § 3, § 6 |
| 3 | API et worker | Un conteneur par service, deux processus (recommandé v1) · deux conteneurs par service | § 3, § 12 |
| 4 | Observabilité | Pile complète (recommandé) · logs seuls (déconseillé) | TEC-OPS-07, RAM |
| 5 | Front | Next.js 15 en BFF (recommandé) · FastAPI + Jinja2 + HTMX | § 3, § 10 |
| 6 | Hébergement | **Décidé le 3 oct. 2026 : VPS externe dédié chez Hetzner, gamme CPX32 (4 vCPU AMD, 8 Go, 160 Go NVMe), datacenter UE (Falkenstein, Nuremberg ou Helsinki), DPA signé dans la console** ; tarif à revérifier à la commande | § 11.2, § 12, TEC-OPS-13 |
| 7 | Topologie d'exposition | **Décidé : directe sur le VPS, nginx en frontal** | § 11.2 |
| 8 | Bannissement | CrowdSec + bouncer nginx (listes communautaires) · fail2ban sur l'hôte (plus simple) | TEC-WEB-05 |
| 9 | WAF | ModSecurity + OWASP CRS en détection puis blocage · aucun WAF | TEC-WEB-06 |
| 10 | Certificats | DNS-01 via l'API de ton registrar (recommandé) · HTTP-01 avec le port 80 | TEC-WEB-01 |
| 11 | Second facteur | TOTP (v1) · WebAuthn dès la v1 puisque l'app est publique | TEC-SEC-01 |
| 12 | Chiffrement au repos | **Décidé : LUKS sur un volume Hetzner dédié, déverrouillage manuel par SSH via WireGuard après chaque redémarrage** ; Tang/Clevis écarté (la clé WireGuard sur la partition non chiffrée affaiblirait la protection) | § 11.2, TEC-OPS-06 |
| 13 | Seconde cible de sauvegarde | Stockage objet UE (Scaleway, OVH) · Backblaze B2 · un second VPS | TEC-OPS-03 |
| 14 | Forge et livraison | **Décidé : GitHub privé + GHCR + runner auto-hébergé en mode pull** | TEC-QA-01, TEC-QA-05, TEC-OPS-01 |
| 15 | Preprod | Second VPS Hetzner temporaire à chaque campagne (facturation à l'heure) · VM Proxmox chez toi | TEC-OPS-10 |
| 16 | Collecteur PISTE | Activer · RSS et JO seulement | § 9 |
| 17 | Résumé de veille | Modèle local (accessible via WireGuard depuis le VPS) · aucun | TEC-VJ-04 |
| 18 | Format d'enveloppe | DL à fenêtre · C5 | TEC-DOC-08 |
| 19 | Offre La Poste (v2) | LReL + API Courrier suivi · Maileva | TEC-ENV-04, lot 7 |

**Hypothèses techniques à vérifier à l'initialisation** : support PDF/A-2b par la version de WeasyPrint installée ; disponibilité d'un export CSV/JSON de la série INSEE sans jeton (sinon API BDM) ; comportement de `auth_request` avec `proxy_cache` sur la version de nginx retenue (et absence de mise en cache des 401) ; possibilité de créer un volume LUKS sur le VPS choisi (disque additionnel ou partition dédiée) et comportement au redémarrage ; disponibilité d'un plugin certbot DNS pour ton hébergeur DNS ; débit du tunnel WireGuard vers ton NAS pour la sauvegarde nocturne (quelques Go au plus) ; limites de taille de message NATS ; format exact des événements de suivi La Poste ; position de fenêtre de l'enveloppe choisie.
