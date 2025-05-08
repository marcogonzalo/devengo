"""Accruals

Revision ID: 7536b7d1b92e
Revises: 2402093cc68c
Create Date: 2025-04-21 18:55:12.821367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7536b7d1b92e'
down_revision: Union[str, None] = '2402093cc68c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define the enum type (reusing from services migration)
service_period_status_enum = "serviceperiodstatus"
service_period_status_enum_values = ['ACTIVE', 'POSTPONED', 'DROPPED', 'ENDED']


def create_enum(name: str, values: list):
    """Create an enum type safely."""
    enum = postgresql.ENUM(*values, name=name, create_type=False)
    enum.create(op.get_bind(), checkfirst=True)
    return enum


def upgrade() -> None:
    """Upgrade schema."""
    # Get the enum type (it should already exist from services migration)
    period_status_enum = postgresql.ENUM(
        *service_period_status_enum_values,
        name=service_period_status_enum,
        create_type=False
    )

    op.create_table(
        'contractaccrual',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('contract_id', sa.Integer(), sa.ForeignKey(
            'servicecontract.id'), nullable=False, unique=True),
        sa.Column('total_amount_to_accrue', sa.Float(), nullable=False),
        sa.Column('total_amount_accrued', sa.Float(), nullable=False, default=0.0),
        sa.Column('remaining_amount_to_accrue', sa.Float(), nullable=False),
        sa.Column('total_sessions_to_accrue', sa.Integer(), nullable=False),
        sa.Column('total_sessions_accrued', sa.Integer(), nullable=False),
        sa.Column('sessions_remaining_to_accrue',
                  sa.Integer(), nullable=False),
        sa.Column('accrual_status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    op.create_table('accruedperiod',
                    sa.Column('created_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.Column('updated_at', sa.DateTime(
                        timezone=True), nullable=False),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('accrual_date', sa.Date(), nullable=False),
                    sa.Column('accrued_amount', sa.Float(), nullable=False),
                    sa.Column('accrual_portion', sa.Float(), nullable=False),
                    sa.Column('status', period_status_enum, nullable=False),
                    sa.Column('sessions_in_period',
                              sa.Integer(), nullable=False),
                    sa.Column('total_contract_amount',
                              sa.Float(), nullable=False),
                    sa.Column('status_change_date', sa.Date(), nullable=True),
                    sa.Column('contract_accrual_id', sa.Integer(), sa.ForeignKey(
                        'contractaccrual.id'), nullable=False),
                    sa.Column('service_period_id',
                              sa.Integer(), nullable=True),
                    sa.ForeignKeyConstraint(
                        ['contract_accrual_id'], ['contractaccrual.id'],
                        name='fk_accruedperiod_contract_accrual_id'
                    ),
                    sa.ForeignKeyConstraint(
                        ['service_period_id'], ['serviceperiod.id'],
                        name='fk_accruedperiod_service_period_id'
                    ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_accruedperiod_accrual_date'),
                    'accruedperiod', ['accrual_date'], unique=False)
    op.create_index(op.f('ix_accruedperiod_status'),
                    'accruedperiod', ['status'], unique=False)
    op.create_index(op.f('ix_servicecontract_status'),
                    'servicecontract', ['status'], unique=False)

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indices and accruedperiod table FIRST
    op.drop_index(op.f('ix_servicecontract_status'),
                  table_name='servicecontract')
    op.drop_index(op.f('ix_accruedperiod_status'), table_name='accruedperiod')
    op.drop_index(op.f('ix_accruedperiod_accrual_date'),
                  table_name='accruedperiod')
    op.drop_constraint('fk_accruedperiod_contract_accrual_id',
                       'accruedperiod', type_='foreignkey')
    op.drop_constraint('fk_accruedperiod_service_period_id',
                       'accruedperiod', type_='foreignkey')
    op.drop_column('accruedperiod', 'service_period_id')
    op.drop_table('accruedperiod')
    # Now drop contract_accrual table
    op.drop_table('contractaccrual')

    # ### end Alembic commands ###
