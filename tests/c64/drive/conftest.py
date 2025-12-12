"""Shared fixtures and constants for 1541 drive tests.

This module provides common test fixtures for all drive-related tests:
- DRIVE_MODES: Parametrized drive runner modes (threaded, synchronous, multiprocess)
- Common ROM/fixture path constants
- Shared helper functions
"""

import pytest
from pathlib import Path

# Test fixtures paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
C64_FIXTURES_DIR = FIXTURES_DIR / "c64"
C64_ROMS_DIR = C64_FIXTURES_DIR / "roms"
DISKS_DIR = C64_FIXTURES_DIR / "disks"

# Check if ROMs are available
ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
    and (C64_ROMS_DIR / "1541.rom").exists()
)

# Drive runner modes to test
# All drive tests should use @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
DRIVE_MODES = [
    pytest.param("threaded", id="threaded"),
    pytest.param("synchronous", id="synchronous"),
    pytest.param("multiprocess", id="multiprocess", marks=pytest.mark.slow),
]

# Common C64 memory addresses
KERNAL_KEYBOARD_BUFFER = 0x0277  # Keyboard buffer ($0277-$0280, 10 bytes)
KERNAL_KEYBOARD_COUNT = 0x00C6  # Number of characters in keyboard buffer
BASIC_DIRECT_MODE_FLAG = 0x9D   # Bit 7 set = direct mode (READY prompt)
KERNAL_STATUS = 0x90            # KERNAL I/O status byte
BASIC_VARTAB_LO = 0x2D          # Start of BASIC variables (end of program) low byte
BASIC_VARTAB_HI = 0x2E          # Start of BASIC variables (end of program) high byte
BASIC_TXTTAB_LO = 0x2B          # Start of BASIC text (load address) low byte
BASIC_TXTTAB_HI = 0x2C          # Start of BASIC text (load address) high byte
PETSCII_RETURN = 0x0D           # PETSCII code for RETURN key

# KERNAL status byte flags ($90)
KERNAL_STATUS_EOF = 0x40                   # Bit 6: End of file (normal after successful load)
KERNAL_STATUS_DEVICE_NOT_PRESENT = 0x80    # Bit 7: Device not present
KERNAL_STATUS_TIMEOUT = 0x03               # Bits 0-1: Read/write timeout errors
KERNAL_STATUS_ERROR_MASK = 0x83            # Mask for error bits (excludes EOF which is normal)

# Maximum cycles for common operations
MAX_BOOT_CYCLES = 5_000_000    # ~5 seconds at 1MHz for boot
MAX_LOAD_CYCLES = 20_000_000   # ~20 seconds for typical load


@pytest.fixture
def c64_cleanup():
    """Fixture that tracks C64 instances and cleans them up after test.

    Usage:
        def test_something(c64_cleanup):
            c64 = create_my_c64()
            c64_cleanup.register(c64)
            # test code...
    """
    class C64Cleanup:
        def __init__(self):
            self._instances = []

        def register(self, c64):
            """Register a C64 instance for cleanup."""
            self._instances.append(c64)
            return c64

        def cleanup_all(self):
            """Clean up all registered instances."""
            for c64 in self._instances:
                try:
                    c64.cleanup()
                except Exception:
                    pass
            self._instances.clear()

    cleanup = C64Cleanup()
    yield cleanup
    cleanup.cleanup_all()
