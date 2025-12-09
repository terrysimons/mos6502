"""Tests for loading files that use the last sector in each zone.

These tests verify that the GCR buffer correctly stores all sectors,
including the last sector on each track. This tests the fix for the
GCR buffer overflow bug where the last sector was truncated.

Zone sector counts:
- Zone 3 (tracks 1-17): 21 sectors (0-20), last = S20 (tested in cross-track tests)
- Zone 2 (tracks 18-24): 19 sectors (0-18), last = S18
- Zone 1 (tracks 25-30): 18 sectors (0-17), last = S17
- Zone 0 (tracks 31-35): 17 sectors (0-16), last = S16

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
LAST_SECTOR_DISK = DISKS_DIR / "last-sector-test.d64"

# Check if ROMs and disk are available
ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
    and (C64_ROMS_DIR / "1541.rom").exists()
)
DISK_AVAILABLE = LAST_SECTOR_DISK.exists()

requires_last_sector_fixtures = pytest.mark.skipif(
    not (ROMS_AVAILABLE and DISK_AVAILABLE),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {LAST_SECTOR_DISK}"
)

# Drive modes to test
DRIVE_MODES = [
    pytest.param(True, id="threaded-drive"),
    pytest.param(False, id="synchronous-drive"),
]

# Maximum cycles for operations
MAX_BOOT_CYCLES = 5_000_000
MAX_LOAD_CYCLES = 30_000_000

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


def create_c64_with_disk(threaded_drive: bool) -> C64:
    """Create a C64 instance with last-sector test disk."""
    c64 = C64(
        rom_dir=C64_ROMS_DIR,
        display_mode='headless',
        video_chip='6569',
    )
    c64.cpu.reset()

    c64.attach_drive(
        drive_rom_path=C64_ROMS_DIR / "1541.rom",
        disk_path=LAST_SECTOR_DISK,
        threaded=threaded_drive,
    )
    return c64


def get_loaded_program_size(c64) -> int:
    """Get the size of the loaded BASIC program in bytes."""
    basic_start = (c64.memory.read(BASIC_TXTTAB_LO) |
                   (c64.memory.read(BASIC_TXTTAB_HI) << 8))
    basic_end = (c64.memory.read(BASIC_VARTAB_LO) |
                 (c64.memory.read(BASIC_VARTAB_HI) << 8))
    return basic_end - basic_start


@requires_last_sector_fixtures
class TestLastSectorZone2:
    """Test loading files that use the last sector in Zone 2 (sector 18)."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_last_sector_zone2_s18(self, threaded_drive):
        """Load LASTZ2-T19: Uses all 19 sectors on track 19, including S18.

        This tests that sector 18 (the last sector in Zone 2) is readable.
        Zone 2 has 19 sectors per track (0-18).
        """
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"LASTZ2*",8\r')

        assert wait_for_load(c64), "Load of LASTZ2-T19 timed out (last sector S18)"

        # Verify program loaded - should be ~19 sectors worth
        program_size = get_loaded_program_size(c64)
        assert program_size > 4000, f"Program should be >4KB, got {program_size} bytes"


@requires_last_sector_fixtures
class TestLastSectorZone1:
    """Test loading files that use the last sector in Zone 1 (sector 17)."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_last_sector_zone1_s17(self, threaded_drive):
        """Load LASTZ1-T25: Uses all 18 sectors on track 25, including S17.

        This tests that sector 17 (the last sector in Zone 1) is readable.
        Zone 1 has 18 sectors per track (0-17).
        """
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"LASTZ1*",8\r')

        assert wait_for_load(c64), "Load of LASTZ1-T25 timed out (last sector S17)"

        program_size = get_loaded_program_size(c64)
        assert program_size > 3500, f"Program should be >3.5KB, got {program_size} bytes"


@requires_last_sector_fixtures
class TestLastSectorZone0:
    """Test loading files that use the last sector in Zone 0 (sector 16)."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_last_sector_zone0_s16(self, threaded_drive):
        """Load LASTZ0-T31: Uses all 17 sectors on track 31, including S16.

        This tests that sector 16 (the last sector in Zone 0) is readable.
        Zone 0 has 17 sectors per track (0-16).
        """
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"LASTZ0*",8\r')

        assert wait_for_load(c64), "Load of LASTZ0-T31 timed out (last sector S16)"

        program_size = get_loaded_program_size(c64)
        assert program_size > 3000, f"Program should be >3KB, got {program_size} bytes"
