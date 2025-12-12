"""Tests for wildcard patterns and load address modes.

These tests verify:
1. LOAD"*",8 - loads first file in directory
2. LOAD"TEST*",8 - pattern matching with wildcard
3. LOAD"FILE",8,1 - absolute load mode (loads to file's embedded address)
4. Maximum length filename (16 characters)

Tests are parametrized for both drive modes:
- threaded: Uses threaded IEC bus (default, faster)
- synchronous: Uses synchronous IEC bus (cycle-accurate)
"""

import pytest
from pathlib import Path
from systems.c64 import C64
from mos6502 import errors

# Test fixtures paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
C64_FIXTURES_DIR = FIXTURES_DIR / "c64"
C64_ROMS_DIR = C64_FIXTURES_DIR / "roms"
DISKS_DIR = C64_FIXTURES_DIR / "disks"
WILDCARD_DISK = DISKS_DIR / "wildcard-test.d64"

# Check if ROMs and disk are available
ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
    and (C64_ROMS_DIR / "1541.rom").exists()
)
DISK_AVAILABLE = WILDCARD_DISK.exists()

requires_wildcard_fixtures = pytest.mark.skipif(
    not (ROMS_AVAILABLE and DISK_AVAILABLE),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {WILDCARD_DISK}"
)

# Drive modes to test
DRIVE_MODES = [
    pytest.param("threaded", id="threaded"),
    pytest.param("synchronous", id="synchronous"),
    pytest.param("multiprocess", id="multiprocess"),
]

# Maximum cycles for operations
MAX_BOOT_CYCLES = 5_000_000
MAX_LOAD_CYCLES = 20_000_000

# C64 memory addresses
BASIC_DIRECT_MODE_FLAG = 0x9D
KERNAL_STATUS = 0x90
BASIC_VARTAB_LO = 0x2D
BASIC_VARTAB_HI = 0x2E
BASIC_TXTTAB_LO = 0x2B
BASIC_TXTTAB_HI = 0x2C

# KERNAL status flags
KERNAL_STATUS_ERROR_MASK = 0x83


def run_cycles(c64, cycles):
    """Run CPU for specified cycles, catching exhaustion exception."""
    try:
        c64.cpu.execute(cycles=cycles)
    except errors.CPUCycleExhaustionError:
        pass


def wait_for_ready(c64, max_cycles=MAX_BOOT_CYCLES):
    """Wait for BASIC READY prompt by checking direct mode flag."""
    cycles_run = 0
    batch_size = 100_000

    while cycles_run < max_cycles:
        run_cycles(c64, batch_size)
        cycles_run += batch_size

        status = c64.memory.read(BASIC_DIRECT_MODE_FLAG)
        if status & 0x80:
            return True

    return False


def wait_for_load(c64, max_cycles=MAX_LOAD_CYCLES):
    """Wait for LOAD operation to complete."""
    cycles_run = 0
    batch_size = 100_000

    initial_basic_end = (c64.memory.read(BASIC_VARTAB_LO) |
                         (c64.memory.read(BASIC_VARTAB_HI) << 8))

    while cycles_run < max_cycles:
        run_cycles(c64, batch_size)
        cycles_run += batch_size

        status = c64.memory.read(BASIC_DIRECT_MODE_FLAG)
        in_direct_mode = (status & 0x80) != 0

        kernal_status = c64.memory.read(KERNAL_STATUS)
        no_errors = (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0

        current_basic_end = (c64.memory.read(BASIC_VARTAB_LO) |
                             (c64.memory.read(BASIC_VARTAB_HI) << 8))
        data_loaded = current_basic_end != initial_basic_end

        if in_direct_mode and no_errors and data_loaded:
            return True

    return False


def wait_for_load_any_address(c64, expected_start: int, max_cycles=MAX_LOAD_CYCLES):
    """Wait for LOAD operation to complete at a specific address.

    Used for ,8,1 loads where data goes to file's embedded address.
    """
    cycles_run = 0
    batch_size = 100_000

    # Store initial values at expected load address
    initial_values = [c64.memory.read(expected_start + i) for i in range(4)]

    while cycles_run < max_cycles:
        run_cycles(c64, batch_size)
        cycles_run += batch_size

        status = c64.memory.read(BASIC_DIRECT_MODE_FLAG)
        in_direct_mode = (status & 0x80) != 0

        kernal_status = c64.memory.read(KERNAL_STATUS)
        no_errors = (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0

        # Check if data at expected address changed
        current_values = [c64.memory.read(expected_start + i) for i in range(4)]
        data_loaded = current_values != initial_values

        if in_direct_mode and no_errors and data_loaded:
            return True

    return False


def create_c64_with_disk(drive_runner: bool) -> C64:
    """Create a C64 instance with wildcard test disk."""
    c64 = C64(
        rom_dir=C64_ROMS_DIR,
        display_mode='headless',
        video_chip='6569',
    )
    c64.cpu.reset()

    c64.attach_drive(
        drive_rom_path=C64_ROMS_DIR / "1541.rom",
        disk_path=WILDCARD_DISK,
        runner=drive_runner,
    )
    return c64


def get_loaded_program_size(c64) -> int:
    """Get the size of the loaded BASIC program in bytes."""
    basic_start = (c64.memory.read(BASIC_TXTTAB_LO) |
                   (c64.memory.read(BASIC_TXTTAB_HI) << 8))
    basic_end = (c64.memory.read(BASIC_VARTAB_LO) |
                 (c64.memory.read(BASIC_VARTAB_HI) << 8))
    return basic_end - basic_start


@requires_wildcard_fixtures
class TestWildcardStar:
    """Test LOAD"*",8 - loading first file in directory."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_load_star(self, drive_runner):
        """LOAD"*",8 loads the first file in directory (FIRST).

        This is the most common way users load programs - load whatever
        is first on the disk.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"*",8\r')

        assert wait_for_load(c64), "LOAD\"*\",8 timed out"

        # Verify no error
        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"

        # Verify some data was loaded
        program_size = get_loaded_program_size(c64)
        assert program_size > 0, "No program data loaded"


@requires_wildcard_fixtures
class TestWildcardPattern:
    """Test LOAD with pattern matching wildcards."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_load_prefix_wildcard(self, drive_runner):
        """LOAD"TEST*",8 loads first file matching TEST prefix.

        Should load TEST-A (first TEST file in directory).
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"TEST*",8\r')

        assert wait_for_load(c64), "LOAD\"TEST*\",8 timed out"

        # Verify no error
        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"


@requires_wildcard_fixtures
class TestAbsoluteLoadMode:
    """Test LOAD"FILE",8,1 - loading to file's embedded address."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_load_absolute_8_1(self, drive_runner):
        """LOAD"HIGHLOAD",8,1 loads to the file's embedded address ($C000).

        The ,8,1 parameter tells KERNAL to load to the address specified
        in the file's first two bytes, rather than to $0801.

        HIGHLOAD is a program with load address $C000.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Remember what's at $C000 before load
        pre_load_c000 = c64.memory.read(0xC000)

        c64.inject_keyboard_string('LOAD"HIGHLOAD",8,1\r')

        # For ,8,1 loads, BASIC end pointer doesn't change
        # We need to check that data appeared at $C000
        assert wait_for_load_any_address(c64, 0xC000), \
            "LOAD\"HIGHLOAD\",8,1 timed out"

        # Verify no error
        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"

        # Verify data was loaded to $C000 (should be different now)
        post_load_c000 = c64.memory.read(0xC000)
        # The first bytes should be BASIC line pointer, which is non-zero
        # Actually the load address is stripped, so first byte is next line ptr
        assert post_load_c000 != pre_load_c000 or post_load_c000 != 0, \
            "Data doesn't appear to have been loaded to $C000"


@requires_wildcard_fixtures
class TestFilenameEdgeCases:
    """Test loading files with edge case filenames."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_max_length_filename(self, drive_runner):
        """Load a file with maximum 16-character filename.

        Tests that the full filename is matched correctly.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"MAXFILENAME1234",8\r')

        assert wait_for_load(c64), "LOAD\"MAXFILENAME1234\",8 timed out"

        # Verify no error
        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"
