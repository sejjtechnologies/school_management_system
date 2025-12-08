"""Add generated time_range and exclusion constraint to prevent teacher overlap across streams

Revision ID: 0004_timetable_overlap
Revises: add_combined_stats
Create Date: 2025-12-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_timetable_overlap'
down_revision = 'add_combined_stats'
branch_labels = None
depends_on = None


def upgrade():
    # Create btree_gist extension required for GIST indexes that support btree operators
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")

    # Validate that start_time and end_time look like HH:MM and are not null
    op.execute(r"""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM timetable_slots
            WHERE start_time IS NULL OR end_time IS NULL
               OR start_time !~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$'
               OR end_time   !~ '^(?:[01][0-9]|2[0-3]):[0-5][0-9]$'
        ) THEN
            RAISE EXCEPTION 'Found timetable_slots rows with NULL or invalid start_time/end_time. Fix them before running this migration.';
        END IF;
    END
    $$;
    """)

    # Add generated int4range column time_range storing minutes-since-midnight range [start,end)
    # Use ADD COLUMN IF NOT EXISTS to be idempotent if the script is re-run
    op.execute(r"""
    ALTER TABLE timetable_slots
      ADD COLUMN IF NOT EXISTS time_range int4range GENERATED ALWAYS AS (
        int4range(
          (split_part(start_time, ':', 1)::int * 60 + split_part(start_time, ':', 2)::int),
          (split_part(end_time,   ':', 1)::int * 60 + split_part(end_time,   ':', 2)::int)
        )
      ) STORED;
    """)

    # Add exclusion constraint to prevent overlapping times for the same teacher on the same day.
    # Wrap creation in a DO block to avoid errors if the constraint already exists.
    op.execute(r"""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'no_teacher_overlap') THEN
        EXECUTE 'ALTER TABLE timetable_slots ADD CONSTRAINT no_teacher_overlap EXCLUDE USING gist (
          teacher_id WITH =,
          day_of_week WITH =,
          time_range WITH &&
        )';
      END IF;
    END
    $$;
    """)


def downgrade():
    # Drop the exclusion constraint if it exists
    op.execute(r"""
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'no_teacher_overlap') THEN
        EXECUTE 'ALTER TABLE timetable_slots DROP CONSTRAINT no_teacher_overlap';
      END IF;
    END
    $$;
    """)

    # Drop the generated column if it exists
    op.execute("ALTER TABLE timetable_slots DROP COLUMN IF EXISTS time_range;")

    # Note: we intentionally do not drop the extension 'btree_gist' because other objects may rely on it
