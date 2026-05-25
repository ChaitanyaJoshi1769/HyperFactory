"""API Key Scoping tests - Fine-grained permission control"""

import pytest
from app.api_key_scopes import (
    APIScope,
    ScopeLevel,
    APIKeyScopeManager,
    DEFAULT_SCOPES,
)


# ============================================================================
# Scope Enum Tests
# ============================================================================

def test_api_scope_enum_read_operations():
    """Test READ operation scopes exist"""
    assert APIScope.READ_FACTORIES.value == "read:factories"
    assert APIScope.READ_MACHINES.value == "read:machines"
    assert APIScope.READ_HARDWARE.value == "read:hardware"
    assert APIScope.READ_SUPPLIERS.value == "read:suppliers"
    assert APIScope.READ_CAD.value == "read:cad"
    assert APIScope.READ_JOBS.value == "read:jobs"
    assert APIScope.READ_USERS.value == "read:users"


def test_api_scope_enum_write_operations():
    """Test WRITE operation scopes exist"""
    assert APIScope.WRITE_FACTORIES.value == "write:factories"
    assert APIScope.WRITE_MACHINES.value == "write:machines"
    assert APIScope.WRITE_HARDWARE.value == "write:hardware"
    assert APIScope.WRITE_SUPPLIERS.value == "write:suppliers"
    assert APIScope.WRITE_CAD.value == "write:cad"
    assert APIScope.WRITE_JOBS.value == "write:jobs"
    assert APIScope.WRITE_USERS.value == "write:users"


def test_api_scope_enum_admin_operations():
    """Test ADMIN operation scopes exist"""
    assert APIScope.ADMIN_USERS.value == "admin:users"
    assert APIScope.ADMIN_SETTINGS.value == "admin:settings"
    assert APIScope.ADMIN_AUDIT_LOG.value == "admin:audit_log"


def test_api_scope_enum_sensitive_operations():
    """Test SENSITIVE operation scopes exist"""
    assert APIScope.DELETE_RESOURCES.value == "delete:resources"
    assert APIScope.EXPORT_DATA.value == "export:data"
    assert APIScope.IMPORT_DATA.value == "import:data"


def test_api_scope_enum_meta_operations():
    """Test META operation scopes exist"""
    assert APIScope.MANAGE_API_KEYS.value == "manage:api_keys"


def test_scope_level_enum_exists():
    """Test ScopeLevel enum values"""
    assert ScopeLevel.READ_ONLY.value == "read_only"
    assert ScopeLevel.READ_WRITE.value == "read_write"
    assert ScopeLevel.ADMIN.value == "admin"
    assert ScopeLevel.CUSTOM.value == "custom"


# ============================================================================
# Default Scope Set Tests
# ============================================================================

def test_default_scopes_read_only():
    """Test READ_ONLY scope set"""
    read_only_scopes = DEFAULT_SCOPES[ScopeLevel.READ_ONLY]

    assert APIScope.READ_FACTORIES in read_only_scopes
    assert APIScope.READ_MACHINES in read_only_scopes
    assert APIScope.READ_HARDWARE in read_only_scopes
    assert APIScope.READ_SUPPLIERS in read_only_scopes
    assert APIScope.READ_CAD in read_only_scopes
    assert APIScope.READ_JOBS in read_only_scopes

    # Should not contain write scopes
    assert APIScope.WRITE_FACTORIES not in read_only_scopes
    assert APIScope.ADMIN_USERS not in read_only_scopes


def test_default_scopes_read_write():
    """Test READ_WRITE scope set"""
    read_write_scopes = DEFAULT_SCOPES[ScopeLevel.READ_WRITE]

    # Should contain all read scopes
    assert APIScope.READ_FACTORIES in read_write_scopes
    assert APIScope.READ_MACHINES in read_write_scopes

    # Should contain all write scopes
    assert APIScope.WRITE_FACTORIES in read_write_scopes
    assert APIScope.WRITE_MACHINES in read_write_scopes

    # Should not contain admin scopes
    assert APIScope.ADMIN_USERS not in read_write_scopes


def test_default_scopes_count():
    """Test default scope set sizes"""
    read_only_count = len(DEFAULT_SCOPES[ScopeLevel.READ_ONLY])
    read_write_count = len(DEFAULT_SCOPES[ScopeLevel.READ_WRITE])

    assert read_only_count == 6  # 6 read scopes
    assert read_write_count == 12  # 6 read + 6 write (not including write:users)


# ============================================================================
# Scope Validation Tests
# ============================================================================

def test_validate_scopes_valid():
    """Test validating valid scopes"""
    manager = APIKeyScopeManager()

    scopes = [
        APIScope.READ_FACTORIES.value,
        APIScope.WRITE_MACHINES.value,
    ]

    assert manager.validate_scopes(scopes) is True


def test_validate_scopes_empty():
    """Test validating empty scope list"""
    manager = APIKeyScopeManager()

    assert manager.validate_scopes([]) is False


def test_validate_scopes_invalid_scope():
    """Test validating with invalid scope"""
    manager = APIKeyScopeManager()

    scopes = [
        APIScope.READ_FACTORIES.value,
        "invalid:scope",
    ]

    assert manager.validate_scopes(scopes) is False


def test_validate_scopes_exceeds_max():
    """Test validating scope list exceeding max"""
    manager = APIKeyScopeManager()
    manager.max_scopes_per_key = 3

    scopes = [
        APIScope.READ_FACTORIES.value,
        APIScope.READ_MACHINES.value,
        APIScope.READ_HARDWARE.value,
        APIScope.READ_SUPPLIERS.value,
    ]

    assert manager.validate_scopes(scopes) is False


def test_validate_scopes_at_max():
    """Test validating scope list at max limit"""
    manager = APIKeyScopeManager()
    manager.max_scopes_per_key = 3

    scopes = [
        APIScope.READ_FACTORIES.value,
        APIScope.READ_MACHINES.value,
        APIScope.READ_HARDWARE.value,
    ]

    assert manager.validate_scopes(scopes) is True


def test_validate_scopes_all_valid():
    """Test all enum scopes are valid"""
    manager = APIKeyScopeManager()

    all_scopes = [scope.value for scope in APIScope]
    # This should be valid as long as it doesn't exceed max
    manager.max_scopes_per_key = len(all_scopes)

    assert manager.validate_scopes(all_scopes) is True


# ============================================================================
# Scope Level to Scopes Conversion Tests
# ============================================================================

def test_get_scopes_from_level_read_only():
    """Test getting READ_ONLY scopes"""
    manager = APIKeyScopeManager()

    scopes = manager.get_scopes_from_level(ScopeLevel.READ_ONLY)

    assert len(scopes) == 6
    assert "read:factories" in scopes
    assert "read:machines" in scopes
    assert "write:factories" not in scopes


def test_get_scopes_from_level_read_write():
    """Test getting READ_WRITE scopes"""
    manager = APIKeyScopeManager()

    scopes = manager.get_scopes_from_level(ScopeLevel.READ_WRITE)

    assert len(scopes) == 12  # 6 read + 6 write (not including write:users)
    assert "read:factories" in scopes
    assert "write:machines" in scopes
    assert "admin:users" not in scopes


def test_get_scopes_from_level_admin():
    """Test getting ADMIN scopes (all)"""
    manager = APIKeyScopeManager()

    scopes = manager.get_scopes_from_level(ScopeLevel.ADMIN)

    # Should include all scopes
    assert len(scopes) > 15
    assert "read:factories" in scopes
    assert "write:machines" in scopes
    assert "admin:users" in scopes
    assert "delete:resources" in scopes


def test_get_scopes_from_level_custom():
    """Test getting CUSTOM scopes (empty)"""
    manager = APIKeyScopeManager()

    scopes = manager.get_scopes_from_level(ScopeLevel.CUSTOM)

    assert scopes == []


# ============================================================================
# Single Scope Checking Tests
# ============================================================================

def test_check_scope_exact_match():
    """Test checking scope with exact match"""
    manager = APIKeyScopeManager()

    scopes = ["read:factories", "write:machines"]

    assert manager.check_scope(scopes, "read:factories") is True
    assert manager.check_scope(scopes, "write:machines") is True


def test_check_scope_no_match():
    """Test checking scope with no match"""
    manager = APIKeyScopeManager()

    scopes = ["read:factories"]

    assert manager.check_scope(scopes, "write:factories") is False


def test_check_scope_admin_wildcard():
    """Test admin:* wildcard grants all permissions"""
    manager = APIKeyScopeManager()

    scopes = ["admin:*"]

    assert manager.check_scope(scopes, "read:factories") is True
    assert manager.check_scope(scopes, "write:machines") is True
    assert manager.check_scope(scopes, "admin:users") is True
    assert manager.check_scope(scopes, "delete:resources") is True


def test_check_scope_resource_wildcard():
    """Test resource:* wildcard for specific resource"""
    manager = APIKeyScopeManager()

    scopes = ["read:*"]

    assert manager.check_scope(scopes, "read:factories") is True
    assert manager.check_scope(scopes, "read:machines") is True
    assert manager.check_scope(scopes, "write:factories") is False


def test_check_scope_write_wildcard():
    """Test write:* wildcard for all write operations"""
    manager = APIKeyScopeManager()

    scopes = ["write:*"]

    assert manager.check_scope(scopes, "write:factories") is True
    assert manager.check_scope(scopes, "write:machines") is True
    assert manager.check_scope(scopes, "read:factories") is False


# ============================================================================
# Multiple Scope Checking Tests
# ============================================================================

def test_check_multiple_scopes_require_all():
    """Test checking multiple scopes with require_all=True"""
    manager = APIKeyScopeManager()

    scopes = ["read:factories", "write:machines", "read:hardware"]
    required = ["read:factories", "write:machines"]

    assert manager.check_multiple_scopes(scopes, required, require_all=True) is True


def test_check_multiple_scopes_require_all_missing():
    """Test require_all when one is missing"""
    manager = APIKeyScopeManager()

    scopes = ["read:factories", "write:machines"]
    required = ["read:factories", "delete:resources"]

    assert manager.check_multiple_scopes(scopes, required, require_all=True) is False


def test_check_multiple_scopes_require_any():
    """Test checking multiple scopes with require_all=False"""
    manager = APIKeyScopeManager()

    scopes = ["read:factories", "write:machines"]
    required = ["delete:resources", "read:factories"]

    assert manager.check_multiple_scopes(scopes, required, require_all=False) is True


def test_check_multiple_scopes_require_any_none_found():
    """Test require_any when none found"""
    manager = APIKeyScopeManager()

    scopes = ["read:factories"]
    required = ["write:hardware", "admin:users"]

    assert manager.check_multiple_scopes(scopes, required, require_all=False) is False


def test_check_multiple_scopes_with_wildcard():
    """Test multiple scope checking with wildcards"""
    manager = APIKeyScopeManager()

    scopes = ["read:*", "write:*"]
    required = ["read:factories", "write:machines", "admin:users"]

    # read and write match, but admin doesn't
    assert manager.check_multiple_scopes(scopes, required, require_all=True) is False
    assert manager.check_multiple_scopes(scopes, required, require_all=False) is True


# ============================================================================
# Scope Restriction Tests (Intersection)
# ============================================================================

def test_restrict_scopes_intersection():
    """Test restricting scopes to intersection"""
    manager = APIKeyScopeManager()

    current = ["read:factories", "write:machines", "read:hardware", "admin:users"]
    max_allowed = ["read:factories", "read:hardware", "write:machines"]

    restricted = manager.restrict_scopes(current, max_allowed)

    assert len(restricted) == 3
    assert "read:factories" in restricted
    assert "write:machines" in restricted
    assert "read:hardware" in restricted
    assert "admin:users" not in restricted


def test_restrict_scopes_no_overlap():
    """Test restricting scopes with no overlap"""
    manager = APIKeyScopeManager()

    current = ["read:factories", "read:machines"]
    max_allowed = ["write:factories", "admin:users"]

    restricted = manager.restrict_scopes(current, max_allowed)

    assert len(restricted) == 0


def test_restrict_scopes_complete_overlap():
    """Test restricting scopes with complete overlap"""
    manager = APIKeyScopeManager()

    current = ["read:factories", "write:machines"]
    max_allowed = ["read:factories", "write:machines"]

    restricted = manager.restrict_scopes(current, max_allowed)

    assert len(restricted) == 2
    assert "read:factories" in restricted
    assert "write:machines" in restricted


def test_restrict_scopes_empty_current():
    """Test restricting empty scope list"""
    manager = APIKeyScopeManager()

    restricted = manager.restrict_scopes([], ["read:factories"])

    assert restricted == []


def test_restrict_scopes_empty_max():
    """Test restricting with empty max allowed"""
    manager = APIKeyScopeManager()

    restricted = manager.restrict_scopes(["read:factories"], [])

    assert restricted == []


# ============================================================================
# Scope Merge Tests (Union)
# ============================================================================

def test_merge_scopes_union():
    """Test merging scope lists (union)"""
    manager = APIKeyScopeManager()

    lists = [
        ["read:factories", "write:machines"],
        ["read:hardware", "write:hardware"],
        ["admin:users"],
    ]

    merged = manager.merge_scopes(lists)

    assert len(merged) == 5
    assert "read:factories" in merged
    assert "write:machines" in merged
    assert "read:hardware" in merged
    assert "write:hardware" in merged
    assert "admin:users" in merged


def test_merge_scopes_duplicates():
    """Test merging scopes removes duplicates"""
    manager = APIKeyScopeManager()

    lists = [
        ["read:factories", "write:machines"],
        ["read:factories", "admin:users"],
    ]

    merged = manager.merge_scopes(lists)

    assert len(merged) == 3
    assert merged.count("read:factories") == 1


def test_merge_scopes_empty_lists():
    """Test merging empty lists"""
    manager = APIKeyScopeManager()

    merged = manager.merge_scopes([[], []])

    assert merged == []


def test_merge_scopes_single_list():
    """Test merging single list"""
    manager = APIKeyScopeManager()

    lists = [["read:factories", "write:machines"]]

    merged = manager.merge_scopes(lists)

    assert len(merged) == 2
    assert "read:factories" in merged
    assert "write:machines" in merged


# ============================================================================
# Resource Scope Lookup Tests
# ============================================================================

def test_get_resource_scopes_factories():
    """Test getting all scopes for factories resource"""
    manager = APIKeyScopeManager()

    scopes = manager.get_resource_scopes("factories")

    assert "read:factories" in scopes
    assert "write:factories" in scopes
    assert len(scopes) == 2


def test_get_resource_scopes_machines():
    """Test getting all scopes for machines resource"""
    manager = APIKeyScopeManager()

    scopes = manager.get_resource_scopes("machines")

    assert "read:machines" in scopes
    assert "write:machines" in scopes


def test_get_resource_scopes_users():
    """Test getting all scopes for users resource"""
    manager = APIKeyScopeManager()

    scopes = manager.get_resource_scopes("users")

    # Should include read, write, and admin
    assert "read:users" in scopes
    assert "write:users" in scopes
    assert "admin:users" in scopes


def test_get_resource_scopes_admin():
    """Test getting all admin scopes"""
    manager = APIKeyScopeManager()

    scopes = manager.get_resource_scopes("admin")

    assert "admin:users" in scopes
    assert "admin:settings" in scopes
    assert "admin:audit_log" in scopes


def test_get_resource_scopes_nonexistent():
    """Test getting scopes for nonexistent resource"""
    manager = APIKeyScopeManager()

    scopes = manager.get_resource_scopes("nonexistent")

    assert scopes == []


# ============================================================================
# Display Formatting Tests
# ============================================================================

def test_format_scopes_empty():
    """Test formatting empty scope list"""
    manager = APIKeyScopeManager()

    formatted = manager.format_scopes_for_display([])

    assert formatted == "No permissions"


def test_format_scopes_read_only_full():
    """Test formatting full READ_ONLY permission set"""
    manager = APIKeyScopeManager()

    read_only_scopes = [s.value for s in DEFAULT_SCOPES[ScopeLevel.READ_ONLY]]
    formatted = manager.format_scopes_for_display(read_only_scopes)

    assert "Read-only" in formatted
    assert "all resources" in formatted


def test_format_scopes_read_write_full():
    """Test formatting full READ_WRITE permission set"""
    manager = APIKeyScopeManager()

    read_write_scopes = [s.value for s in DEFAULT_SCOPES[ScopeLevel.READ_WRITE]]
    formatted = manager.format_scopes_for_display(read_write_scopes)

    assert "Read/Write" in formatted
    assert "all resources" in formatted


def test_format_scopes_custom():
    """Test formatting custom scope set"""
    manager = APIKeyScopeManager()

    scopes = ["read:factories", "write:machines", "admin:users"]
    formatted = manager.format_scopes_for_display(scopes)

    assert "Custom" in formatted
    assert "read" in formatted
    assert "write" in formatted
    assert "admin" in formatted


def test_format_scopes_read_only_partial():
    """Test formatting partial read-only scope set"""
    manager = APIKeyScopeManager()

    scopes = ["read:factories", "read:machines"]
    formatted = manager.format_scopes_for_display(scopes)

    assert "Custom" in formatted
    assert "2 read" in formatted


def test_format_scopes_write_only():
    """Test formatting write-only scopes"""
    manager = APIKeyScopeManager()

    scopes = ["write:factories", "write:machines", "write:hardware"]
    formatted = manager.format_scopes_for_display(scopes)

    assert "3 write" in formatted
    assert "Custom" in formatted


# ============================================================================
# Integration Tests
# ============================================================================

def test_manager_instance_exists():
    """Test that global manager instance exists"""
    from app.api_key_scopes import api_key_scope_manager

    assert api_key_scope_manager is not None
    assert isinstance(api_key_scope_manager, APIKeyScopeManager)


def test_typical_read_write_workflow():
    """Test typical read/write key workflow"""
    manager = APIKeyScopeManager()

    # Create key with read-write to factories and machines
    requested_scopes = [
        "read:factories",
        "read:machines",
        "write:factories",
        "write:machines",
    ]

    # Validate scopes
    assert manager.validate_scopes(requested_scopes) is True

    # Check individual permissions
    assert manager.check_scope(requested_scopes, "read:factories") is True
    assert manager.check_scope(requested_scopes, "write:machines") is True
    assert manager.check_scope(requested_scopes, "admin:users") is False

    # Format for display
    formatted = manager.format_scopes_for_display(requested_scopes)
    assert "Custom" in formatted


def test_typical_admin_workflow():
    """Test typical admin key workflow"""
    manager = APIKeyScopeManager()
    manager.max_scopes_per_key = 100  # Allow all admin scopes

    # Get all admin scopes
    admin_scopes = manager.get_scopes_from_level(ScopeLevel.ADMIN)

    # Validate
    assert manager.validate_scopes(admin_scopes) is True

    # Check various permissions
    assert manager.check_scope(admin_scopes, "read:factories") is True
    assert manager.check_scope(admin_scopes, "delete:resources") is True
    assert manager.check_scope(admin_scopes, "manage:api_keys") is True


def test_typical_restriction_workflow():
    """Test scope restriction (delegation) workflow"""
    manager = APIKeyScopeManager()

    # Admin key with all scopes
    admin_scopes = manager.get_scopes_from_level(ScopeLevel.ADMIN)

    # User can request subset
    requested_scopes = [
        "read:factories",
        "write:machines",
        "admin:users",  # Trying to request admin
    ]

    # Restrict to what admin has AND user requests
    effective_scopes = manager.restrict_scopes(requested_scopes, admin_scopes)

    assert "read:factories" in effective_scopes
    assert "write:machines" in effective_scopes
    assert "admin:users" in effective_scopes


def test_scope_escalation_prevention():
    """Test that scope restriction prevents escalation"""
    manager = APIKeyScopeManager()

    # API key can only do read:factories
    key_scopes = ["read:factories"]

    # User tries to escalate by requesting more scopes
    requested_scopes = [
        "read:factories",
        "write:machines",
        "admin:users",
    ]

    # Restriction should only allow read:factories
    effective_scopes = manager.restrict_scopes(requested_scopes, key_scopes)

    assert effective_scopes == ["read:factories"]
    assert "write:machines" not in effective_scopes
    assert "admin:users" not in effective_scopes


def test_wildcard_scope_inheritance():
    """Test that admin:* grants all permissions"""
    manager = APIKeyScopeManager()

    admin_wildcard = ["admin:*"]

    # Should grant all permissions
    assert manager.check_scope(admin_wildcard, "read:factories") is True
    assert manager.check_scope(admin_wildcard, "write:machines") is True
    assert manager.check_scope(admin_wildcard, "admin:settings") is True
    assert manager.check_scope(admin_wildcard, "delete:resources") is True
    assert manager.check_scope(admin_wildcard, "export:data") is True


def test_multiple_permission_checks():
    """Test checking multiple permissions at once"""
    manager = APIKeyScopeManager()

    scopes = ["read:factories", "write:machines", "read:hardware"]

    # Check if has both read operations
    has_both_reads = manager.check_multiple_scopes(
        scopes,
        ["read:factories", "read:hardware"],
        require_all=True
    )
    assert has_both_reads is True

    # Check if has either admin or read
    has_admin_or_read = manager.check_multiple_scopes(
        scopes,
        ["admin:users", "read:factories"],
        require_all=False
    )
    assert has_admin_or_read is True


def test_scope_merge_and_restrict():
    """Test combining merge and restrict operations"""
    manager = APIKeyScopeManager()

    # Multiple users contribute scopes
    user1_scopes = ["read:factories", "write:machines"]
    user2_scopes = ["read:hardware", "write:hardware"]

    # Merge their scopes
    merged = manager.merge_scopes([user1_scopes, user2_scopes])
    assert len(merged) == 4

    # Restrict to read-only
    read_only_max = manager.get_scopes_from_level(ScopeLevel.READ_ONLY)
    restricted = manager.restrict_scopes(merged, read_only_max)

    # Should only have read operations
    assert "read:factories" in restricted
    assert "read:hardware" in restricted
    assert "write:machines" not in restricted
    assert "write:hardware" not in restricted
