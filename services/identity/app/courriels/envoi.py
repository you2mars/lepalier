"""Envoi des e-mails de compte par SMTP (ADR 0006 : identity sur le réseau egress-mail ; Mailpit en dev)."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

from app.courriels.textes import Courriel
from commun.jobs import ErreurReseau


class Expediteur(Protocol):
    def envoyer(self, destinataire: str, courriel: Courriel) -> None: ...


@dataclass(frozen=True)
class ExpediteurSmtp:
    hote: str
    port: int
    adresse: str
    delai_secondes: float = 10.0

    def envoyer(self, destinataire: str, courriel: Courriel) -> None:
        """Une panne du serveur SMTP lève ErreurReseau : le job est reporté sans compter de tentative."""
        message = EmailMessage()
        message["From"] = self.adresse
        message["To"] = destinataire
        message["Subject"] = courriel.objet
        message.set_content(courriel.corps)
        try:
            with smtplib.SMTP(self.hote, self.port, timeout=self.delai_secondes) as smtp:
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise ErreurReseau(f"SMTP {self.hote}:{self.port} : {type(exc).__name__}") from exc
