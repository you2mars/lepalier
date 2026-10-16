"""Réponses JSON produites par nginx lui-même (deploy/nginx/reponses_json.conf) : mêmes codes et mêmes textes
que commun, pour que le front les lise comme celles des services."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from commun.erreurs import _HTTP, MESSAGE_INDISPONIBLE

REPONSES = Path(__file__).resolve().parents[2] / "deploy" / "nginx" / "reponses_json.conf"


def _corps(emplacement: str) -> tuple[int, dict[str, object]]:
    bloc = re.search(rf"location @{emplacement} \{{(.*?)\n\}}", REPONSES.read_text(), re.S)
    assert bloc, emplacement
    statut, brut = re.search(r'return (\d{3}) "(.*)";', bloc.group(1)).groups()  # type: ignore[union-attr]
    return int(statut), json.loads(brut.replace('\\"', '"').replace("$request_id", "t"))


@pytest.mark.parametrize(
    ("emplacement", "statut", "code", "message"),
    [
        ("non_authentifie", 401, *_HTTP[401]),
        ("introuvable", 404, *_HTTP[404]),
        ("indisponible", 503, "service_indisponible", MESSAGE_INDISPONIBLE),
    ],
)
def test_reponses_nginx__format_et_texte_de_commun(
    emplacement: str, statut: int, code: str, message: str
) -> None:
    assert _corps(emplacement) == (statut, {"code": code, "message": message, "details": {}, "trace_id": "t"})
