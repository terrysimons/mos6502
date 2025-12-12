"""Tests for loading files that span multiple zone boundaries.

This tests loading files that cross multiple speed zone transitions
in a single load operation. The drive must handle multiple speed
changes during the file read.

Speed zones:
- Zone 3: Tracks 1-17 (21 sectors/track, fastest)
- Zone 2: Tracks 18-24 (19 sectors/track)
- Zone 1: Tracks 25-30 (18 sectors/track)
- Zone 0: Tracks 31-35 (17 sectors/track, slowest)

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
MULTI_ZONE_DISK = DISKS_DIR / "multi-zone-span.d64"

# Check if ROMs and disk are available
ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
    and (C64_ROMS_DIR / "1541.rom").exists()
)
DISK_AVAILABLE = MULTI_ZONE_DISK.exists()

requires_multi_zone_fixtures = pytest.mark.skipif(
    not (ROMS_AVAILABLE and DISK_AVAILABLE),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {MULTI_ZONE_DISK}"
)

# Drive modes to test
DRIVE_MODES = [
    pytest.param("threaded", id="threaded"),
    pytest.param("synchronous", id="synchronous"),
    pytest.param("multiprocess", id="multiprocess", marks=pytest.mark.slow),
]

# Maximum cycles for operations
MAX_BOOT_CYCLES = 5_000_000
MAX_LOAD_CYCLES = 100_000_000  # Very large file (150 sectors) needs more time

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


def create_c64_with_disk(drive_runner: bool) -> C64:
    """Create a C64 instance with multi-zone span test disk."""
    c64 = C64(
        rom_dir=C64_ROMS_DIR,
        display_mode='headless',
        video_chip='6569',
    )
    c64.cpu.reset()

    c64.attach_drive(
        drive_rom_path=C64_ROMS_DIR / "1541.rom",
        disk_path=MULTI_ZONE_DISK,
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


@requires_multi_zone_fixtures
class TestMultiZoneSpan:
    """Test loading files spanning multiple zone boundaries."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_span_three_zones(self, drive_runner):
        """Load SPAN-3ZONES: Spans Zone 3 -> Zone 2 -> Zone 1.

        This file spans tracks 17-25, crossing two zone boundaries:
        - Zone 3 (Track 17): 21 sectors, fastest speed
        - Zone 2 (Tracks 19-24): 19 sectors/track, medium speed
        - Zone 1 (Track 25): 18 sectors/track, slower speed

        Track 18 is skipped (directory track).

        Tests that the drive correctly handles multiple speed zone
        transitions during a single file load.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"SPAN-3ZONES",8\r')

        assert wait_for_load(c64), "Load of SPAN-3ZONES timed out (multi-zone)"

        # 150 sectors * 254 bytes = ~38KB
        program_size = get_loaded_program_size(c64)
        assert program_size > 35000, f"Program should be >35KB, got {program_size} bytes"
