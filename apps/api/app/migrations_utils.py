"""Database migration utilities"""

import subprocess
import sys
from pathlib import Path


def run_migrations():
    """Run pending database migrations"""
    alembic_dir = Path(__file__).parent.parent

    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=alembic_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"Migration error: {result.stderr}")
            return False

        print(result.stdout)
        return True
    except Exception as e:
        print(f"Failed to run migrations: {e}")
        return False


def create_migration(message: str):
    """Create a new migration file

    Args:
        message: Description of the migration
    """
    alembic_dir = Path(__file__).parent.parent

    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", message],
            cwd=alembic_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"Migration creation error: {result.stderr}")
            return False

        print(result.stdout)
        return True
    except Exception as e:
        print(f"Failed to create migration: {e}")
        return False


def get_current_revision():
    """Get the current database revision"""
    alembic_dir = Path(__file__).parent.parent

    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "current"],
            cwd=alembic_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return None

        return result.stdout.strip()
    except Exception as e:
        print(f"Failed to get current revision: {e}")
        return None


def get_migration_history():
    """Get migration history"""
    alembic_dir = Path(__file__).parent.parent

    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "history"],
            cwd=alembic_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return None

        return result.stdout.strip()
    except Exception as e:
        print(f"Failed to get migration history: {e}")
        return None
