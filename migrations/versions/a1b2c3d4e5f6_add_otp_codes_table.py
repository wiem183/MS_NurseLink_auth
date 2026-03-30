"""add otp_codes table

Revision ID: a1b2c3d4e5f6
Revises: <your_previous_revision_id>
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = 'b8dfaf402717'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'otp_codes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('code', sa.String(6), nullable=False),
        sa.Column('reset_token', sa.String(64), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_otp_codes_email', 'otp_codes', ['email'])
    op.create_index('ix_otp_codes_reset_token', 'otp_codes', ['reset_token'],
                    unique=True)


def downgrade() -> None:
    op.drop_index('ix_otp_codes_reset_token', table_name='otp_codes')
    op.drop_index('ix_otp_codes_email', table_name='otp_codes')
    op.drop_table('otp_codes')