"""Add internal_service_periods and period_amount

Revision ID: b1c2d3e4f5a6
Revises: 934af5fcae06
Create Date: 2026-11-10 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = '934af5fcae06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'service',
        sa.Column(
            'internal_service_periods',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )
    op.add_column(
        'serviceperiod',
        sa.Column('period_amount', sa.Float(), nullable=True),
    )

    # Prefill allowlisted Holded accountNums (AI Flex)
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE service SET internal_service_periods = TRUE "
            "WHERE account_identifier = '70501003'"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('serviceperiod', 'period_amount')
    op.drop_column('service', 'internal_service_periods')
