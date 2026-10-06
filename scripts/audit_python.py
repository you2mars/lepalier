"""Audit des dépendances Python (étape 6, TEC-QA-01, TEC-SEC-13) : python3 scripts/audit_python.py <projet>…

Pour chaque projet (libs/commun, services/<service>) : dépendances exportées de uv.lock (outils de
développement compris, puisque la CI les exécute), passées à pip-audit ; la gravité de chaque vulnérabilité
est lue dans sa fiche OSV ou celle de ses alias (gravité déclarée par GitHub). Échec sur une gravité haute,
critique ou inconnue (jamais de laisser-passer par défaut) ; les autres sont signalées sans bloquer.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import httpx

OSV = "https://api.osv.dev/v1/vulns/{}"
ORDRE = ["faible", "moyenne", "haute", "critique", "inconnue"]
GRAVITES = {
    "LOW": "faible",
    "MODERATE": "moyenne",
    "MEDIUM": "moyenne",
    "HIGH": "haute",
    "CRITICAL": "critique",
}
BLOQUANTES = {"haute", "critique", "inconnue"}

Fiche = dict[str, Any]


def gravite(fiche: Fiche) -> str:
    """Gravité déclarée de la fiche ; un score CVSS seul n'est pas recalculé ici : « inconnue »."""
    declaree = str(fiche.get("database_specific", {}).get("severity", "")).upper()
    return GRAVITES.get(declaree, "inconnue")


def gravite_avec_alias(identifiant: str, alias: Iterable[str], lire: Callable[[str], Fiche | None]) -> str:
    """La gravité connue la plus forte parmi la fiche et ses alias ; « inconnue » si aucune n'en déclare."""
    connues = []
    for nom in [identifiant, *alias]:
        fiche = lire(nom)
        if fiche is not None and (g := gravite(fiche)) != "inconnue":
            connues.append(g)
    return max(connues, key=ORDRE.index) if connues else "inconnue"


def code_de_sortie(gravites: Iterable[str]) -> int:
    return 1 if any(g in BLOQUANTES for g in gravites) else 0


def ligne_rapport(
    projet: str, paquet: str, version: str, identifiant: str, niveau: str, corrections: list[str]
) -> str:
    correctif = f"corrigée en {', '.join(corrections)}" if corrections else "aucune version corrigée connue"
    return f"{projet} : {paquet} {version}, {identifiant}, gravité {niveau}, {correctif}"


def _lire_osv(client: httpx.Client) -> Callable[[str], Fiche | None]:
    def lire(identifiant: str) -> Fiche | None:
        reponse = client.get(OSV.format(identifiant))
        return reponse.json() if reponse.status_code == 200 else None

    return lire


def _outil(nom: str) -> str:
    chemin = shutil.which(nom)
    if chemin is None:
        raise RuntimeError(f"{nom} introuvable dans le PATH (uv tool install {nom}, ou uvx {nom})")
    return chemin


def _vulnerabilites(projet: Path) -> list[dict[str, Any]]:
    # outils de l'environnement d'audit, arguments fixes : aucune entrée externe
    export = [_outil("uv"), "export", "--frozen", "--all-extras", "--all-groups", "--no-hashes"]
    export += ["--no-emit-project", "--no-emit-package", "commun"]
    exporte = subprocess.run(export, cwd=projet, capture_output=True, text=True, check=True).stdout  # noqa: S603
    with tempfile.NamedTemporaryFile("w", suffix=".txt") as exigences:
        exigences.write(exporte)
        exigences.flush()
        commande = [_outil("pip-audit"), "-r", exigences.name, "--disable-pip", "--no-deps", "-f", "json"]
        audit = subprocess.run(commande, capture_output=True, text=True, check=False)  # noqa: S603
    if audit.returncode not in (0, 1):
        raise RuntimeError(f"pip-audit a échoué pour {projet} : {audit.stderr.strip()}")
    return list(json.loads(audit.stdout)["dependencies"])


def main(projets: list[str]) -> int:
    gravites: list[str] = []
    with httpx.Client(timeout=30) as client:
        lire = _lire_osv(client)
        for projet in projets:
            nom = Path(projet).name
            for dependance in _vulnerabilites(Path(projet)):
                for vuln in dependance.get("vulns", []):
                    niveau = gravite_avec_alias(vuln["id"], vuln.get("aliases", []), lire)
                    gravites.append(niveau)
                    print(
                        ligne_rapport(
                            nom,
                            dependance["name"],
                            dependance["version"],
                            vuln["id"],
                            niveau,
                            vuln.get("fix_versions", []),
                        )
                    )
    bloquantes = sum(g in BLOQUANTES for g in gravites)
    print(f"{len(gravites)} vulnérabilité(s) connue(s), dont {bloquantes} bloquante(s).")
    return code_de_sortie(gravites)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
