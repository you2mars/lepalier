"""Tables du service. Le socle (outbox, inbox, journal, job, planificateur, état du worker) vient de
`commun` ; les tables métier s'ajoutent à `METADATA` dans des modules voisins."""

from __future__ import annotations

from app.models.identity import (
    APPAREIL,
    CODE_SECOURS,
    INVITATION,
    REINITIALISATION,
    SESSION,
    TENTATIVE_CONNEXION,
    UTILISATEUR,
)
from app.models.socle import (
    ETAT_WORKER,
    IDEMPOTENCE,
    INBOX,
    INBOX_SVC,
    JOB,
    JOBS,
    JOURNAL,
    JOURNAL_SVC,
    METADATA,
    OUTBOX,
    OUTBOX_SVC,
    PLANIFICATEUR,
)

__all__ = [
    "APPAREIL",
    "CODE_SECOURS",
    "ETAT_WORKER",
    "IDEMPOTENCE",
    "INBOX",
    "INBOX_SVC",
    "INVITATION",
    "JOB",
    "JOBS",
    "JOURNAL",
    "JOURNAL_SVC",
    "METADATA",
    "OUTBOX",
    "OUTBOX_SVC",
    "PLANIFICATEUR",
    "REINITIALISATION",
    "SESSION",
    "TENTATIVE_CONNEXION",
    "UTILISATEUR",
]
