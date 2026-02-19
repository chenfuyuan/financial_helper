"""add stock_basic table

Revision ID: c1add_stock_basic
Revises: bae8ccdeb6df
Create Date: 2026-02-20

"""

import sqlalchemy as sa
from alembic import op

revision = "c1add_stock_basic"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 字段顺序：id 最前，业务字段居中，公用字段最后（见 guide/development-conventions.md）
    op.create_table(
        "stock_basic",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("third_code", sa.String(length=32), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False),
        sa.Column("area", sa.String(length=32), nullable=False),
        sa.Column("industry", sa.String(length=64), nullable=False),
        sa.Column("list_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "third_code", name="uq_stock_basic_source_third_code"),
    )


def downgrade() -> None:
    op.drop_table("stock_basic")
