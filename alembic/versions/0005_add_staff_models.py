"""
Add staff attendance, salary history and staff profiles tables

Revision ID: 0005_staff_models
Revises: 0004_timetable_overlap
Create Date: 2025-12-08 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005_staff_models'
down_revision = '0004_timetable_overlap'
branch_labels = None
depends_on = None


def upgrade():
    # Create staff_attendance table
    op.create_table(
        'staff_attendance',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('staff_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('recorded_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('staff_id', 'date', name='u_staff_date')
    )

    # Create salary_history table
    op.create_table(
        'salary_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('staff_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('old_salary', sa.Numeric(12, 2), nullable=False),
        sa.Column('new_salary', sa.Numeric(12, 2), nullable=False),
        sa.Column('changed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )

    # Create staff_profiles table
    op.create_table(
        'staff_profiles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('staff_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('bank_name', sa.String(length=100), nullable=True),
        sa.Column('bank_account', sa.String(length=100), nullable=True),
        sa.Column('tax_id', sa.String(length=100), nullable=True),
        sa.Column('pay_grade', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    )


def downgrade():
    op.drop_table('staff_profiles')
    op.drop_table('salary_history')
    op.drop_table('staff_attendance')
