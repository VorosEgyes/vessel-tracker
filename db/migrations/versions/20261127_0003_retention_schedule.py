"""Schedule the retention jobs when pg_cron is installed."""

import sys
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "20261127_0003"
down_revision = "20261127_0002"
branch_labels = None
depends_on = None

SCHEDULE_SQL = Path(__file__).with_suffix(".sql")


def upgrade() -> None:
    op.execute(SCHEDULE_SQL.read_text(encoding="utf-8"))
    installed = (
        op.get_bind()
        .execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron')"))
        .scalar_one()
    )
    if not installed:
        print("WARNING: pg_cron is unavailable; retention jobs are NOT scheduled", file=sys.stderr)


def downgrade() -> None:
    op.execute("""
        DO $retention$
        DECLARE job record;
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
                RAISE WARNING 'pg_cron is unavailable: no retention jobs removed';
                RETURN;
            END IF;
            IF current_setting('is_superuser') <> 'on' THEN
                RAISE EXCEPTION 'Retention schedule removal requires a superuser';
            END IF;
            IF EXISTS (
                SELECT 1 FROM cron.job
                 WHERE jobname IN ('drop-raw-partitions', 'drop-water-level-partitions',
                                   'drop-position-partitions')
                   AND (database <> current_database() OR username <> current_user)
            ) THEN
                RAISE EXCEPTION 'Conflicting retention job ownership or database; reconcile it before downgrade';
            END IF;
            FOR job IN
                SELECT jobid FROM cron.job
                 WHERE database = current_database() AND username = current_user
                   AND jobname IN ('drop-raw-partitions', 'drop-water-level-partitions',
                                   'drop-position-partitions')
            LOOP
                PERFORM cron.unschedule(job.jobid);
            END LOOP;
        END;
        $retention$;
    """)
