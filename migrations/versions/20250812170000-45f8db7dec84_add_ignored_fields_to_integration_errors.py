"""Add ignored fields to integration_errors table

Revision ID: 20250812170000
Revises: a5f8dbb7e84c
Create Date: 2025-08-12 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '45f8db7dec84'
down_revision: Union[str, None] = 'a5f8dbb7e84c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if table exists
    inspector = op.get_bind().dialect.inspector(op.get_bind())
    if 'integrationerror' not in inspector.get_table_names():
        # Create the table if it doesn't exist
        op.create_table('integrationerror',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('integration_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('operation_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('external_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('entity_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('error_message', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('error_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('client_id', sa.Integer(), nullable=True),
            sa.Column('contract_id', sa.Integer(), nullable=True),
            sa.Column('is_resolved', sa.Boolean(), nullable=False),
            sa.Column('is_ignored', sa.Boolean(), nullable=False),
            sa.Column('resolved_at', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('resolution_notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('ignored_at', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('ignore_notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['client_id'], ['client.id'], ),
            sa.ForeignKeyConstraint(['contract_id'], ['servicecontract.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for better performance
        op.create_index(op.f('ix_integrationerror_integration_name'), 'integrationerror', ['integration_name'], unique=False)
        op.create_index(op.f('ix_integrationerror_operation_type'), 'integrationerror', ['operation_type'], unique=False)
        op.create_index(op.f('ix_integrationerror_external_id'), 'integrationerror', ['external_id'], unique=False)
        op.create_index(op.f('ix_integrationerror_is_resolved'), 'integrationerror', ['is_resolved'], unique=False)
        op.create_index(op.f('ix_integrationerror_is_ignored'), 'integrationerror', ['is_ignored'], unique=False)
        
        # Create unique constraint to prevent duplicate errors for the same entity
        op.create_unique_constraint('uq_integration_error_unique', 'integrationerror', 
                                   ['integration_name', 'operation_type', 'external_id', 'entity_type', 'client_id', 'contract_id'])
    else:
        # Add ignored fields to existing table
        op.add_column('integrationerror', sa.Column('is_ignored', sa.Boolean(), nullable=False, server_default='false'))
        op.add_column('integrationerror', sa.Column('ignored_at', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        op.add_column('integrationerror', sa.Column('ignore_notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
        
        # Create index for is_ignored
        op.create_index(op.f('ix_integrationerror_is_ignored'), 'integrationerror', ['is_ignored'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Check if table exists
    inspector = op.get_bind().dialect.inspector(op.get_bind())
    if 'integrationerror' in inspector.get_table_names():
        # Remove ignored fields
        op.drop_index(op.f('ix_integrationerror_is_ignored'), table_name='integrationerror')
        op.drop_column('integrationerror', 'ignore_notes')
        op.drop_column('integrationerror', 'ignored_at')
        op.drop_column('integrationerror', 'is_ignored')
        
        # If this was a new table creation, drop the entire table
        if 'ix_integrationerror_integration_name' in [idx['name'] for idx in inspector.get_indexes('integrationerror')]:
            op.drop_constraint('uq_integration_error_unique', 'integrationerror', type_='unique')
            op.drop_index(op.f('ix_integrationerror_is_resolved'), table_name='integrationerror')
            op.drop_index(op.f('ix_integrationerror_external_id'), table_name='integrationerror')
            op.drop_index(op.f('ix_integrationerror_operation_type'), table_name='integrationerror')
            op.drop_index(op.f('ix_integrationerror_integration_name'), table_name='integrationerror')
            op.drop_table('integrationerror')
