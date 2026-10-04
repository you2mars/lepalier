# ADR 0002 — Hébergement sur un VPS Hetzner CPX32 (3 octobre 2026)

Statut : accepté. Décision : VPS externe dédié (4 vCPU, 8 Go, 160 Go) chez Hetzner, datacenter UE, DPA signé ; exposition directe par nginx ; volume LUKS pour les données, déverrouillage manuel par SSH via WireGuard ; sauvegardes chiffrées vers le NAS domestique et un stockage objet d'un second fournisseur. Alternatives écartées : auto-hébergement Proxmox (dépendance au réseau domestique), relais VPS, Tang/Clevis (affaiblit le chiffrement). Tarifs à revérifier à la commande.
