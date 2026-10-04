from __future__ import annotations

from sqlalchemy import Column, MetaData, Table, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP

from commun.inbox import Inbox, table_inbox
from commun.jobs import Jobs, table_job, table_planificateur
from commun.journal import Journal, table_journal
from commun.outbox import Outbox, table_outbox

METADATA = MetaData()

OUTBOX = table_outbox(METADATA)
INBOX = table_inbox(METADATA)
JOURNAL = table_journal(METADATA)
JOB = table_job(METADATA)
PLANIFICATEUR = table_planificateur(METADATA)
# dernier passage du worker, lu par /internal/healthz (TEC-OPS-06)
ETAT_WORKER = Table(
    "etat_worker",
    METADATA,
    Column("nom", Text, primary_key=True),
    Column("vu_le", TIMESTAMP(timezone=True), nullable=False),
)

OUTBOX_SVC = Outbox(OUTBOX)
INBOX_SVC = Inbox(INBOX)
JOURNAL_SVC = Journal(JOURNAL)
JOBS = Jobs(JOB, PLANIFICATEUR)
