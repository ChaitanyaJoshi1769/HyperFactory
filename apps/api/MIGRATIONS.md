# Database Migrations Guide

This guide explains how to manage database schema changes using Alembic migrations.

## Overview

Alembic is a database migration tool that tracks schema changes and provides a way to version your database structure. All migration files are in the `migrations/` directory.

## Setup

Alembic is already configured. The migration configuration includes:

- **alembic.ini** - Alembic configuration file
- **migrations/env.py** - Migration environment setup
- **migrations/script.py.mako** - Migration template
- **migrations/versions/** - Migration files

## Running Migrations

### Apply all pending migrations

```bash
cd apps/api
alembic upgrade head
```

### Apply specific migration

```bash
alembic upgrade 001
```

### Rollback to previous migration

```bash
alembic downgrade -1
```

### Rollback to specific revision

```bash
alembic downgrade 001
```

## Creating New Migrations

### Auto-generate migration (recommended)

After making changes to models in `app/models/`, auto-generate the migration:

```bash
alembic revision --autogenerate -m "Add new table or modify schema"
```

This creates a new file in `migrations/versions/` with the SQL changes.

### Manual migration

To manually create a migration:

```bash
alembic revision -m "Custom migration description"
```

Then edit the generated file to add upgrade/downgrade logic.

## Migration Naming Convention

Migrations are numbered sequentially:
- `001_initial_schema.py` - Initial database schema
- `002_add_users_table.py` - Example second migration
- `003_add_indexes.py` - Example third migration

## Current Migrations

### 001_initial_schema
Creates all core tables:
- materials
- hardware_parts
- tolerances
- surface_finishes
- suppliers
- supplier_capabilities
- supplier_quotes
- factories
- machines
- production_jobs
- cad_models
- cad_analyses

## Checking Migration Status

### Current revision

```bash
alembic current
```

### Migration history

```bash
alembic history
```

### Pending migrations

```bash
alembic history -r base:head
```

## Migration Best Practices

1. **Always test migrations** - Test both upgrade and downgrade paths
2. **Keep migrations small** - One logical change per migration
3. **Use descriptive names** - Make it clear what the migration does
4. **Review generated SQL** - Auto-generated migrations may need tweaks
5. **Never edit applied migrations** - Create a new migration for fixes
6. **Include downgrade logic** - Always implement rollback paths

## Environment Configuration

Migrations use the `DATABASE_URL` environment variable:

```bash
# Set in .env file
DATABASE_URL=postgresql://user:password@localhost:5432/hyperfactory
```

If not set, migrations default to SQLite for testing:
```
DATABASE_URL=sqlite:///./test.db
```

## Troubleshooting

### Migration already exists

Error: "Target database is not up to date."

**Solution:** Check current revision and run pending migrations:
```bash
alembic current
alembic upgrade head
```

### Conflict in migration files

If multiple migrations are created for the same change:

1. Identify which is correct
2. Delete the duplicate
3. Update the `down_revision` in the remaining migration if needed

### Migration fails

Check the error message:
- Syntax error: Review the migration SQL
- Constraint error: May need to drop/recreate constraints
- Data error: May need to handle existing data

## Integration with API

Migrations can be run during application startup:

```python
from app.migrations_utils import run_migrations

# In main.py startup event
@app.on_event("startup")
async def startup_event():
    run_migrations()
```

Or manually before starting the server:

```bash
alembic upgrade head
python main.py
```

## Example: Creating a New Migration

1. Modify a model in `app/models/hardware.py`:

```python
class HardwarePart(Base):
    # ... existing columns ...
    new_field = Column(String(255), nullable=True)
```

2. Generate the migration:

```bash
alembic revision --autogenerate -m "Add new_field to hardware_parts"
```

3. Review the generated file in `migrations/versions/`

4. Test the migration:

```bash
# Apply
alembic upgrade head

# Rollback
alembic downgrade -1
```

5. Commit to git:

```bash
git add migrations/versions/XXX_add_new_field_to_hardware_parts.py
git commit -m "Add migration for new_field"
```

## SQL References

### Supported Column Types

- `String(length)` - VARCHAR
- `Integer()` - INTEGER
- `Float()` - FLOAT
- `Numeric(precision, scale)` - NUMERIC/DECIMAL
- `Boolean()` - BOOLEAN
- `DateTime()` - TIMESTAMP
- `JSON()` - JSON
- `UUID()` - UUID (PostgreSQL)

### Common Operations

#### Add column
```python
op.add_column('table_name', 
    sa.Column('new_column', sa.String(255)))
```

#### Drop column
```python
op.drop_column('table_name', 'old_column')
```

#### Add index
```python
op.create_index('ix_table_column', 'table_name', ['column'])
```

#### Add constraint
```python
op.create_unique_constraint('uq_table_column', 'table_name', ['column'])
```

## Further Reading

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Column Types](https://docs.sqlalchemy.org/en/20/core/types.html)
- [PostgreSQL Type System](https://www.postgresql.org/docs/current/datatype.html)
