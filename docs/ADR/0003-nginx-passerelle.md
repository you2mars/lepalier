# ADR 0003 — nginx comme passerelle et frontal Internet (3 octobre 2026)

Statut : accepté. Décision : nginx 1.26+ termine TLS (Let's Encrypt, DNS-01), vérifie les sessions par `auth_request` vers identity, écrase les en-têtes d'identité, limite le débit, pose CSP avec nonce, HSTS et autres en-têtes, route `/api/<service>` et sert la page de maintenance ; CrowdSec ou fail2ban en bannissement ; WAF ModSecurity optionnel. Traefik écarté (routage dynamique inutile, durcissement moins fin).
