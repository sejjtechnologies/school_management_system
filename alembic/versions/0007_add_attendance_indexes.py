"""
Add composite indexes to staff_attendance for faster range queries

Revision ID: 0007_add_attendance_indexes
Revises: 0006_attendance_term_year
Create Date: 2025-12-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0007_add_attendance_indexes'
down_revision = '0006_attendance_term_year'
branch_labels = None
depends_on = None


def upgrade():
    # Composite index to support date range scans grouped by staff
    op.create_index(op.f('ix_staff_attendance_date_staff_id'), 'staff_attendance', ['date', 'staff_id'], unique=False)
    # Composite index to support filtering by date and status (present/absent)
    op.create_index(op.f('ix_staff_attendance_date_status'), 'staff_attendance', ['date', 'status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_staff_attendance_date_status'), table_name='staff_attendance')
    op.drop_index(op.f('ix_staff_attendance_date_staff_id'), table_name='staff_attendance')
