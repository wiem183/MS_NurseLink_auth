"""add purpose column to otp_codes

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b1c2d3e4f5a6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'otp_codes',
        sa.Column(
            'purpose',
            sa.String(30),
            nullable=False,
            server_default='password_reset',  # safe default for existing rows
        ),
    )
    op.create_index('ix_otp_codes_email_purpose', 'otp_codes', ['email', 'purpose'])


def downgrade() -> None:
    op.drop_index('ix_otp_codes_email_purpose', table_name='otp_codes')
    op.drop_column('otp_codes', 'purpose')