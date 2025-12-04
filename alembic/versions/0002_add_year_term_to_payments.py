"""Add year and term fields to Payment table

Revision ID: 0002_add_year_term_to_payments
Revises: 0001_create_attendance
Create Date: 2025-12-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_year_term_to_payments'
down_revision = '0001_create_attendance'
branch_labels = None
depends_on = None


def upgrade():
    # Add year column to payments table
    op.add_column('payments', sa.Column('year', sa.Integer(), nullable=True))
    # Add term column to payments table
    op.add_column('payments', sa.Column('term', sa.String(length=20), nullable=True))


def downgrade():
    # Remove term column
    op.drop_column('payments', 'term')
    # Remove year column
    op.drop_column('payments', 'year')
