"""Shared fixtures and markers for C64 tests."""

from pathlib import Path

import pytest

# Path constants for C64 test fixtures
PROJECT_ROOT = Path(__file__).parent.parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
C64_FIXTURES_DIR = FIXTURES_DIR / "c64"
CARTRIDGE_TYPES_DIR = C64_FIXTURES_DIR / "cartridge_types"
C64_ROMS_DIR = C64_FIXTURES_DIR / "roms"

# Check if C64 ROMs are available for integration tests
C64_ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
)

# Skip marker for tests requiring C64 ROMs
# Use relative path for cleaner skip message
C64_ROMS_DIR_RELATIVE = C64_ROMS_DIR.relative_to(PROJECT_ROOT)
requires_c64_roms = pytest.mark.skipif(
    not C64_ROMS_AVAILABLE,
    reason=f"Missing C64 ROMs in {C64_ROMS_DIR_RELATIVE}"
)
