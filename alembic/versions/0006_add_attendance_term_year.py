"""
Add term and year to staff_attendance

Revision ID: 0006_attendance_term_year
Revises: 0005_staff_models
Create Date: 2025-12-08 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006_attendance_term_year'
down_revision = '0005_staff_models'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('staff_attendance', sa.Column('term', sa.String(length=50), nullable=True))
    op.add_column('staff_attendance', sa.Column('year', sa.Integer(), nullable=True))
    # optional index on year
    op.create_index(op.f('ix_staff_attendance_year'), 'staff_attendance', ['year'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_staff_attendance_year'), table_name='staff_attendance')
    op.drop_column('staff_attendance', 'year')
    op.drop_column('staff_attendance', 'term')
