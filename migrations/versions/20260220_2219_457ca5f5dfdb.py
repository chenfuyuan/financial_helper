"""add_concept_tables

Revision ID: 457ca5f5dfdb
Revises: eec6febc30ca
Create Date: 2026-02-20 22:19:53.343346

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '457ca5f5dfdb'
down_revision = 'eec6febc30ca'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'concept',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('third_code', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('content_hash', sa.String(length=16), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source', 'third_code', name='uq_concept_source_third_code'),
    )

    op.create_table(
        'concept_stock',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('concept_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('stock_third_code', sa.String(length=32), nullable=False),
        sa.Column('stock_symbol', sa.String(length=32), nullable=True),
        sa.Column('content_hash', sa.String(length=16), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['concept_id'], ['concept.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('concept_id', 'source', 'stock_third_code', name='uq_concept_stock_key'),
    )
    op.create_index(op.f('ix_concept_stock_stock_symbol'), 'concept_stock', ['stock_symbol'], unique=False)
    op.create_index(op.f('ix_concept_stock_stock_third_code'), 'concept_stock', ['stock_third_code'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_concept_stock_stock_third_code'), table_name='concept_stock')
    op.drop_index(op.f('ix_concept_stock_stock_symbol'), table_name='concept_stock')
    op.drop_table('concept_stock')
    op.drop_table('concept')
