"""Initial schema - create all tables

Revision ID: 001
Revises:
Create Date: 2026-05-25

This migration creates the initial database schema for HyperFactory API
including all core tables for hardware, suppliers, factory, and CAD management.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all initial tables"""

    # Create materials table
    op.create_table(
        'materials',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('density', sa.Float(), nullable=True),
        sa.Column('cost_per_kg', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('tensile_strength', sa.Float(), nullable=True),
        sa.Column('yield_strength', sa.Float(), nullable=True),
        sa.Column('thermal_conductivity', sa.Float(), nullable=True),
        sa.Column('machinability_index', sa.Float(), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_materials_name', 'name'),
        sa.Index('ix_materials_created_at', 'created_at'),
    )

    # Create hardware_parts table
    op.create_table(
        'hardware_parts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('revision', sa.String(50), nullable=True),
        sa.Column('description', sa.String(2000), nullable=True),
        sa.Column('material_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('weight_kg', sa.Float(), nullable=False),
        sa.Column('estimated_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('estimated_lead_time_days', sa.Integer(), nullable=True),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('surface_area', sa.Float(), nullable=True),
        sa.Column('cad_model_url', sa.String(500), nullable=True),
        sa.Column('cad_model_hash', sa.String(256), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_hardware_parts_name', 'name'),
        sa.Index('ix_hardware_parts_type', 'type'),
        sa.Index('ix_hardware_parts_created_at', 'created_at'),
    )

    # Create tolerances table
    op.create_table(
        'tolerances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hardware_part_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('dimension', sa.String(255), nullable=False),
        sa.Column('nominal_value', sa.Float(), nullable=False),
        sa.Column('upper_tolerance', sa.Float(), nullable=False),
        sa.Column('lower_tolerance', sa.Float(), nullable=False),
        sa.Column('tolerance_type', sa.String(50), nullable=True),
        sa.Column('tolerance_grade', sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(['hardware_part_id'], ['hardware_parts.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create surface_finishes table
    op.create_table(
        'surface_finishes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hardware_part_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('roughness_ra', sa.Float(), nullable=False),
        sa.Column('roughness_rz', sa.Float(), nullable=True),
        sa.Column('process', sa.String(255), nullable=True),
        sa.Column('cost_multiplier', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['hardware_part_id'], ['hardware_parts.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create suppliers table
    op.create_table(
        'suppliers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('country', sa.String(50), nullable=False),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(20), nullable=True),
        sa.Column('quality_score', sa.Integer(), nullable=True),
        sa.Column('reliability_score', sa.Integer(), nullable=True),
        sa.Column('cost_competitiveness_score', sa.Integer(), nullable=True),
        sa.Column('on_time_delivery_rate', sa.Float(), nullable=True),
        sa.Column('defect_rate', sa.Float(), nullable=True),
        sa.Column('minimum_order_value', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('payment_terms', sa.String(255), nullable=True),
        sa.Column('lead_time_variability', sa.Float(), nullable=True),
        sa.Column('certifications', sa.JSON(), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_suppliers_name', 'name'),
        sa.Index('ix_suppliers_type', 'type'),
        sa.Index('ix_suppliers_country', 'country'),
        sa.Index('ix_suppliers_created_at', 'created_at'),
    )

    # Create supplier_capabilities table
    op.create_table(
        'supplier_capabilities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(255), nullable=True),
        sa.Column('process', sa.String(255), nullable=True),
        sa.Column('min_order_quantity', sa.Integer(), nullable=True),
        sa.Column('max_annual_capacity', sa.Float(), nullable=True),
        sa.Column('lead_time_standard_days', sa.Integer(), nullable=True),
        sa.Column('lead_time_expedited_days', sa.Integer(), nullable=True),
        sa.Column('cost_per_unit_base', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('precision_capability_microns', sa.Float(), nullable=True),
        sa.Column('material_capabilities', sa.JSON(), nullable=True),
        sa.Column('certifications', sa.JSON(), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create supplier_quotes table
    op.create_table(
        'supplier_quotes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('part_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('capability_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('total_price', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('lead_time_days', sa.Integer(), nullable=True),
        sa.Column('minimum_order_quantity', sa.Integer(), nullable=True),
        sa.Column('volume_available', sa.Float(), nullable=True),
        sa.Column('expiration_date', sa.DateTime(), nullable=True),
        sa.Column('terms', sa.String(2000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['capability_id'], ['supplier_capabilities.id'], ),
        sa.ForeignKeyConstraint(['part_id'], ['hardware_parts.id'], ),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_supplier_quotes_created_at', 'created_at'),
    )

    # Create factories table
    op.create_table(
        'factories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('location', sa.String(255), nullable=False),
        sa.Column('country', sa.String(50), nullable=True),
        sa.Column('region', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('capacity_utilization', sa.Float(), nullable=True),
        sa.Column('power_consumption_kwh', sa.Float(), nullable=True),
        sa.Column('production_efficiency', sa.Float(), nullable=True),
        sa.Column('defect_rate', sa.Float(), nullable=True),
        sa.Column('average_lead_time_days', sa.Integer(), nullable=True),
        sa.Column('throughput_parts_per_day', sa.Integer(), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create machines table
    op.create_table(
        'machines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(255), nullable=False),
        sa.Column('process', sa.String(255), nullable=True),
        sa.Column('factory_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('capacity_per_hour', sa.Float(), nullable=True),
        sa.Column('power_consumption_kw', sa.Float(), nullable=True),
        sa.Column('precision_microns', sa.Float(), nullable=True),
        sa.Column('material_compatibility', sa.JSON(), nullable=True),
        sa.Column('certifications', sa.JSON(), nullable=True),
        sa.Column('last_maintenance', sa.DateTime(), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['factory_id'], ['factories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_machines_name', 'name'),
    )

    # Create production_jobs table
    op.create_table(
        'production_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('part_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('machine_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('priority', sa.String(20), nullable=True),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('actual_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('estimated_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('actual_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('completion_time', sa.DateTime(), nullable=True),
        sa.Column('quality_checks_passed', sa.Integer(), nullable=True),
        sa.Column('quality_checks_failed', sa.Integer(), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
        sa.ForeignKeyConstraint(['part_id'], ['hardware_parts.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_production_jobs_status', 'status'),
        sa.Index('ix_production_jobs_created_at', 'created_at'),
    )

    # Create cad_models table
    op.create_table(
        'cad_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hardware_part_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('format', sa.String(20), nullable=False),
        sa.Column('file_url', sa.String(500), nullable=False),
        sa.Column('file_hash', sa.String(256), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('bounding_box_min_x', sa.Float(), nullable=True),
        sa.Column('bounding_box_min_y', sa.Float(), nullable=True),
        sa.Column('bounding_box_min_z', sa.Float(), nullable=True),
        sa.Column('bounding_box_max_x', sa.Float(), nullable=True),
        sa.Column('bounding_box_max_y', sa.Float(), nullable=True),
        sa.Column('bounding_box_max_z', sa.Float(), nullable=True),
        sa.Column('volume_cubic_mm', sa.Float(), nullable=True),
        sa.Column('surface_area_mm2', sa.Float(), nullable=True),
        sa.Column('part_count', sa.Integer(), nullable=True),
        sa.Column('assembly_count', sa.Integer(), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['hardware_part_id'], ['hardware_parts.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_cad_models_created_at', 'created_at'),
        sa.UniqueConstraint('file_hash', name='uq_cad_models_file_hash'),
    )

    # Create cad_analyses table
    op.create_table(
        'cad_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hardware_part_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('cad_model_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('analysis_type', sa.String(255), nullable=True),
        sa.Column('manufacturability_score', sa.Integer(), nullable=True),
        sa.Column('has_issues', sa.Boolean(), nullable=True),
        sa.Column('issues_count', sa.Integer(), nullable=True),
        sa.Column('dfm_score', sa.Integer(), nullable=True),
        sa.Column('estimated_machining_time_minutes', sa.Integer(), nullable=True),
        sa.Column('estimated_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('estimated_lead_time_days', sa.Integer(), nullable=True),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('issues', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cad_model_id'], ['cad_models.id'], ),
        sa.ForeignKeyConstraint(['hardware_part_id'], ['hardware_parts.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_cad_analyses_created_at', 'created_at'),
        sa.UniqueConstraint('cad_model_id', name='uq_cad_analyses_cad_model_id'),
    )


def downgrade() -> None:
    """Drop all tables"""
    op.drop_table('cad_analyses')
    op.drop_table('cad_models')
    op.drop_table('production_jobs')
    op.drop_table('machines')
    op.drop_table('factories')
    op.drop_table('supplier_quotes')
    op.drop_table('supplier_capabilities')
    op.drop_table('suppliers')
    op.drop_table('surface_finishes')
    op.drop_table('tolerances')
    op.drop_table('hardware_parts')
    op.drop_table('materials')
