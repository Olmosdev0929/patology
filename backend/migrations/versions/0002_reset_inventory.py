"""reset IGX inventory to the laboratory's own shelf, starting from zero

Removes the starter demo lots and stock history, and every non-custom marker; the seed then
recreates the shelf list (app/seed/inventory.py) with empty lots and passports. Markers the
lab added itself (is_custom) are kept, without lots.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-26 10:00:00
"""
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM stock_movements")
    op.execute("DELETE FROM igx_lots")
    op.execute("DELETE FROM igx_markers WHERE is_custom IS NOT TRUE")
    op.execute("UPDATE igx_markers SET stock = 0, used_30d = 0, expiry_date = NULL")


def downgrade() -> None:
    pass  # data reset; nothing to restore
