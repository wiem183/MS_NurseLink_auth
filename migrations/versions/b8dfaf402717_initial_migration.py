"""Initial migration

Revision ID: b8dfaf402717
Revises: 
Create Date: 2026-02-21 23:05:00.006502

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b8dfaf402717'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type only if it doesn't exist (must match app.models.enums.UserRole)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('PATIENT', 'NURSE', 'ADMIN');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create users table
    op.create_table('users',
                    sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
                    sa.Column('email', sa.String(length=255), nullable=False),
                    sa.Column('password_hash', sa.String(length=255), nullable=False),
                    sa.Column('first_name', sa.String(length=100), nullable=False),
                    sa.Column('last_name', sa.String(length=100), nullable=False),
                    sa.Column('phone', sa.String(length=30), nullable=True),
                    sa.Column('role', postgresql.ENUM('PATIENT', 'NURSE', 'ADMIN', name='userrole', create_type=False), nullable=False),
                    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
                    sa.Column('is_email_verified', sa.Boolean(), nullable=False, server_default='false'),
                    sa.Column('profile_picture_url', sa.String(length=500), nullable=True),
                    sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
                    sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
                    sa.Column('last_login_at', sa.DateTime(), nullable=True),
                    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create refresh_tokens table
    op.create_table('refresh_tokens',
                    sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
                    sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
                    sa.Column('token', sa.String(length=512), nullable=False),
                    sa.Column('expires_at', sa.DateTime(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
                    sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
                    sa.Column('is_one_time_use', sa.Boolean(), nullable=False, server_default='true'),
                    )
    op.create_index('ix_refresh_tokens_token', 'refresh_tokens', ['token'], unique=True)
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_refresh_tokens_user_id', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_token', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    op.execute('DROP TYPE userrole')