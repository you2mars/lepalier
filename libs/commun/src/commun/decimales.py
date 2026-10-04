"""Utilitaires décimaux (TEC-STK-03) : jamais de float, ROUND_HALF_UP, répartition au plus fort reste."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from typing import Annotated

from pydantic import BeforeValidator, PlainSerializer

CENTIME = Decimal("0.01")


def vers_decimal(valeur: object) -> Decimal:
    """Convertit une chaîne décimale (point), un entier ou un Decimal ; refuse float, bool et non-nombres."""
    if isinstance(valeur, bool) or isinstance(valeur, float):
        raise TypeError("nombre à virgule flottante refusé : utilisez une chaîne décimale")
    if isinstance(valeur, Decimal):
        resultat = valeur
    elif isinstance(valeur, int):
        resultat = Decimal(valeur)
    elif isinstance(valeur, str):
        try:
            resultat = Decimal(valeur.strip())
        except InvalidOperation as exc:
            raise ValueError(f"valeur décimale illisible : {valeur!r}") from exc
    else:
        raise TypeError(f"type non décimal : {type(valeur).__name__}")
    if not resultat.is_finite():
        raise ValueError("valeur décimale non finie refusée")
    return resultat


def arrondir(valeur: Decimal, pas: Decimal = CENTIME) -> Decimal:
    """Arrondi commercial (ROUND_HALF_UP) au pas donné."""
    return valeur.quantize(pas, rounding=ROUND_HALF_UP)


def en_chaine(valeur: Decimal) -> str:
    """Sérialisation JSON d'un montant : deux décimales exactement ; refuse un montant non arrondi."""
    if valeur != arrondir(valeur):
        raise ValueError(f"montant non arrondi au centime : {valeur} (arrondir explicitement avant)")
    return f"{arrondir(valeur):f}"


def repartir_plus_fort_reste(
    total: Decimal, poids: Sequence[Decimal], pas: Decimal = CENTIME
) -> list[Decimal]:
    """Répartit `total` au prorata des `poids`, au pas près, somme exacte (méthode du plus fort reste).

    Les égalités de reste sont départagées par l'ordre des poids (déterministe).
    """
    if total < 0 or total != total.quantize(pas):
        raise ValueError(f"total à répartir invalide : {total} (positif, multiple de {pas})")
    if not poids or any(p < 0 for p in poids):
        raise ValueError("poids invalides : au moins un, tous positifs ou nuls")
    with localcontext() as ctx:
        ctx.prec = 60
        somme = sum(poids, Decimal(0))
        if somme == 0:
            raise ValueError("la somme des poids est nulle")
        unites = (total / pas).to_integral_value()
        bases: list[Decimal] = []
        restes: list[Decimal] = []
        for p in poids:
            produit = unites * p
            base = (produit / somme).to_integral_value(rounding=ROUND_FLOOR)
            bases.append(base)
            restes.append(produit - base * somme)
        a_distribuer = int(unites - sum(bases, Decimal(0)))
        ordre = sorted(range(len(poids)), key=lambda i: (-restes[i], i))
        for i in ordre[:a_distribuer]:
            bases[i] += 1
        return [(b * pas).quantize(pas) for b in bases]


def _montant(valeur: object) -> Decimal:
    try:
        resultat = vers_decimal(valeur)
    except (TypeError, ValueError) as exc:
        raise ValueError(_MESSAGE_MONTANT) from exc
    if resultat != arrondir(resultat):
        raise ValueError(_MESSAGE_MONTANT)
    return arrondir(resultat)


_MESSAGE_MONTANT = "Le montant doit être écrit avec un point et deux décimales au plus, par exemple 650.00."

Montant = Annotated[
    Decimal,
    BeforeValidator(_montant),
    PlainSerializer(en_chaine, return_type=str, when_used="json"),
]
"""Montant Pydantic : chaîne décimale ou entier en entrée (float refusé), chaîne « 650.00 » en JSON."""
