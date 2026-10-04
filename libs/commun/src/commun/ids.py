"""Identifiants UUID v7 générés par le service propriétaire (TEC-DAT-01)."""

from __future__ import annotations

import uuid

import uuid_utils


def uuid7() -> uuid.UUID:
    """UUID v7 (ordonné dans le temps, croissant dans un même processus)."""
    return uuid.UUID(bytes=uuid_utils.uuid7().bytes)
