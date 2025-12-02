"""create attendance and attendance_log tables

Revision ID: 0001_create_attendance
Revises: 
Create Date: 2025-12-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_create_attendance'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'attendance',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('pupil_id', sa.Integer(), sa.ForeignKey('pupils.id'), nullable=False),
        sa.Column('class_id', sa.Integer(), sa.ForeignKey('classes.id'), nullable=True),
        sa.Column('stream_id', sa.Integer(), sa.ForeignKey('streams.id'), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('pupil_id', 'date', name='u_pupil_date')
    )

    op.create_table(
        'attendance_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('attendance_id', sa.Integer(), sa.ForeignKey('attendance.id'), nullable=True),
        sa.Column('pupil_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('old_status', sa.String(length=32), nullable=True),
        sa.Column('new_status', sa.String(length=32), nullable=True),
        sa.Column('changed_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('attendance_log')
    op.drop_table('attendance')
