"""Add status and description to payments table

Revision ID: 0003_add_status_desc
Revises: 0002_add_year_term_to_payments
Create Date: 2025-12-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_add_status_desc'
down_revision = '0002_add_year_term_to_payments'
branch_labels = None
depends_on = None


def upgrade():
    # Add status column with default 'completed' and description column
    op.add_column('payments', sa.Column('status', sa.String(length=20), nullable=False, server_default='completed'))
    op.add_column('payments', sa.Column('description', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('payments', 'description')
    op.drop_column('payments', 'status')
