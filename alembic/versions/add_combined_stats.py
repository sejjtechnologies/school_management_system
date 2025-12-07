"""Add combined stats columns to reports table

Revision ID: add_combined_stats
Revises: 0003_add_status_desc
Create Date: 2025-12-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_combined_stats'
down_revision = '0003_add_status_desc'
branch_labels = None
depends_on = None


def upgrade():
    # Add combined stats columns to reports table
    op.add_column('reports', sa.Column('combined_total', sa.Float(), nullable=True))
    op.add_column('reports', sa.Column('combined_average', sa.Float(), nullable=True))
    op.add_column('reports', sa.Column('combined_grade', sa.String(5), nullable=True))


def downgrade():
    # Remove combined stats columns from reports table
    op.drop_column('reports', 'combined_grade')
    op.drop_column('reports', 'combined_average')
    op.drop_column('reports', 'combined_total')
