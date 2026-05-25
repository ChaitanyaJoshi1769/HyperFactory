"""API Key Scoping - Fine-grained permissions for API keys"""

from enum import Enum
from typing import List, Optional, Set, Dict
from datetime import datetime
from sqlalchemy.orm import Session as DBSession
from app.models import APIKey, User
from app.audit_logger import audit_logger, AuditEventType, AuditEventSeverity
import os

# ============================================================================
# Permission Enums
# ============================================================================

class APIScope(str, Enum):
    """Available API scopes for granular permission control"""

    # Read operations
    READ_FACTORIES = "read:factories"
    READ_MACHINES = "read:machines"
    READ_HARDWARE = "read:hardware"
    READ_SUPPLIERS = "read:suppliers"
    READ_CAD = "read:cad"
    READ_JOBS = "read:jobs"
    READ_USERS = "read:users"

    # Write operations
    WRITE_FACTORIES = "write:factories"
    WRITE_MACHINES = "write:machines"
    WRITE_HARDWARE = "write:hardware"
    WRITE_SUPPLIERS = "write:suppliers"
    WRITE_CAD = "write:cad"
    WRITE_JOBS = "write:jobs"
    WRITE_USERS = "write:users"

    # Admin operations
    ADMIN_USERS = "admin:users"
    ADMIN_SETTINGS = "admin:settings"
    ADMIN_AUDIT_LOG = "admin:audit_log"

    # Sensitive operations
    DELETE_RESOURCES = "delete:resources"
    EXPORT_DATA = "export:data"
    IMPORT_DATA = "import:data"

    # Meta operations
    MANAGE_API_KEYS = "manage:api_keys"  # Can create/revoke other keys


class ScopeLevel(str, Enum):
    """Scope levels for simplified permission assignment"""

    READ_ONLY = "read_only"          # All read:* scopes
    READ_WRITE = "read_write"        # All read:* and write:*
    ADMIN = "admin"                  # All scopes
    CUSTOM = "custom"                # User-specified scopes


# ============================================================================
# Default Scope Sets
# ============================================================================

DEFAULT_SCOPES: Dict[ScopeLevel, Set[APIScope]] = {
    ScopeLevel.READ_ONLY: {
        APIScope.READ_FACTORIES,
        APIScope.READ_MACHINES,
        APIScope.READ_HARDWARE,
        APIScope.READ_SUPPLIERS,
        APIScope.READ_CAD,
        APIScope.READ_JOBS,
    },
    ScopeLevel.READ_WRITE: {
        APIScope.READ_FACTORIES,
        APIScope.READ_MACHINES,
        APIScope.READ_HARDWARE,
        APIScope.READ_SUPPLIERS,
        APIScope.READ_CAD,
        APIScope.READ_JOBS,
        APIScope.WRITE_FACTORIES,
        APIScope.WRITE_MACHINES,
        APIScope.WRITE_HARDWARE,
        APIScope.WRITE_SUPPLIERS,
        APIScope.WRITE_CAD,
        APIScope.WRITE_JOBS,
    },
}


class APIKeyScopeManager:
    """Manages API key scopes and permission checking"""

    def __init__(self):
        """Initialize scope manager"""
        self.max_scopes_per_key = int(os.getenv("MAX_SCOPES_PER_KEY", "20"))

    def validate_scopes(self, scopes: List[str]) -> bool:
        """
        Validate scope list.

        Args:
            scopes: List of scope strings

        Returns:
            True if all scopes are valid
        """
        if not scopes:
            return False

        if len(scopes) > self.max_scopes_per_key:
            return False

        valid_scopes = {scope.value for scope in APIScope}
        for scope in scopes:
            if scope not in valid_scopes:
                return False

        return True

    def get_scopes_from_level(self, level: ScopeLevel) -> List[str]:
        """
        Get scope list from level.

        Args:
            level: Scope level (READ_ONLY, READ_WRITE, ADMIN, CUSTOM)

        Returns:
            List of scope strings
        """
        if level == ScopeLevel.ADMIN:
            # All scopes
            return [scope.value for scope in APIScope]
        elif level in DEFAULT_SCOPES:
            return [scope.value for scope in DEFAULT_SCOPES[level]]
        else:
            return []

    def check_scope(self, scopes: List[str], required_scope: str) -> bool:
        """
        Check if scopes include required permission.

        Args:
            scopes: List of granted scopes
            required_scope: Required scope to check

        Returns:
            True if scope is included
        """
        # Admin scopes grant all permissions
        if "admin:*" in scopes or f"{required_scope.split(':')[0]}:*" in scopes:
            return True

        # Check exact match
        if required_scope in scopes:
            return True

        # Wildcard scopes
        resource = required_scope.split(":")[0]
        if f"{resource}:*" in scopes:
            return True

        return False

    def check_multiple_scopes(
        self,
        scopes: List[str],
        required_scopes: List[str],
        require_all: bool = True,
    ) -> bool:
        """
        Check if scopes include multiple required permissions.

        Args:
            scopes: List of granted scopes
            required_scopes: List of required scopes
            require_all: If True, require all; if False, require any

        Returns:
            True if permission granted
        """
        checks = [self.check_scope(scopes, scope) for scope in required_scopes]

        if require_all:
            return all(checks)
        else:
            return any(checks)

    def restrict_scopes(
        self,
        current_scopes: List[str],
        max_scopes: List[str],
    ) -> List[str]:
        """
        Restrict scopes to maximum allowed (intersection).

        Args:
            current_scopes: Current scope list
            max_scopes: Maximum allowed scopes

        Returns:
            Restricted scope list (intersection)
        """
        current_set = set(current_scopes)
        max_set = set(max_scopes)

        return list(current_set & max_set)

    def merge_scopes(self, scope_lists: List[List[str]]) -> List[str]:
        """
        Merge multiple scope lists (union).

        Args:
            scope_lists: List of scope lists

        Returns:
            Merged scope list (unique)
        """
        merged = set()
        for scopes in scope_lists:
            merged.update(scopes)

        return list(merged)

    def get_resource_scopes(self, resource: str) -> List[str]:
        """
        Get all scopes for a resource.

        Args:
            resource: Resource name (e.g., 'factories', 'users')

        Returns:
            List of scopes for resource
        """
        scopes = []
        for scope in APIScope:
            if resource in scope.value:
                scopes.append(scope.value)

        return scopes

    def format_scopes_for_display(self, scopes: List[str]) -> str:
        """
        Format scopes for human-readable display.

        Args:
            scopes: List of scope strings

        Returns:
            Human-readable scope description
        """
        if not scopes:
            return "No permissions"

        # Check for full levels
        read_write_set = {scope.value for scope in DEFAULT_SCOPES[ScopeLevel.READ_WRITE]}
        if set(scopes) >= read_write_set:
            return "Read/Write access to all resources"

        read_only_set = {scope.value for scope in DEFAULT_SCOPES[ScopeLevel.READ_ONLY]}
        if set(scopes) >= read_only_set:
            return "Read-only access to all resources"

        # Count by type
        read_count = len([s for s in scopes if s.startswith("read:")])
        write_count = len([s for s in scopes if s.startswith("write:")])
        admin_count = len([s for s in scopes if s.startswith("admin:")])

        parts = []
        if read_count > 0:
            parts.append(f"{read_count} read")
        if write_count > 0:
            parts.append(f"{write_count} write")
        if admin_count > 0:
            parts.append(f"{admin_count} admin")

        return f"Custom permissions: {', '.join(parts)}"

    def log_scope_change(
        self,
        user_id: str,
        api_key_id: str,
        old_scopes: List[str],
        new_scopes: List[str],
        source_ip: str = None,
    ) -> None:
        """
        Log API key scope changes.

        Args:
            user_id: User ID
            api_key_id: API key ID
            old_scopes: Previous scopes
            new_scopes: New scopes
            source_ip: Source IP for audit
        """
        audit_logger.log_event(
            event_type=AuditEventType.API_KEY_CREATED,
            actor_id=user_id,
            resource_id=api_key_id,
            resource_type="api_key",
            action="scope_change",
            severity=AuditEventSeverity.INFO,
            details={
                "old_scopes": old_scopes,
                "new_scopes": new_scopes,
                "scopes_added": list(set(new_scopes) - set(old_scopes)),
                "scopes_removed": list(set(old_scopes) - set(new_scopes)),
            },
            source_ip=source_ip,
        )


# Global scope manager instance
api_key_scope_manager = APIKeyScopeManager()
