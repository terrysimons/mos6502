"""Tests for loading files that span multiple tracks.

These tests verify that the disk drive correctly handles:
1. Sequential sector reading across track boundaries
2. Zone transitions (speed changes between tracks)
3. Large file loading similar to real programs like Tank Wars

Test disk layout (cross-track-test.d64):
- SPAN1-2: 40 sectors across tracks 1-2 (Zone 3 only, like Tank Wars)
- SPAN17-19: 42 sectors across tracks 17,19,20 (Zone 3->2 boundary, skips track 18)
- SPAN24-26: 38 sectors across tracks 24-26 (Zone 2->1 boundary)
- SPAN30-32: 36 sectors across tracks 30-32 (Zone 1->0 boundary)

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
CROSS_TRACK_DISK = DISKS_DIR / "cross-track-test.d64"

# Check if ROMs and disk are available
ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
    and (C64_ROMS_DIR / "1541.rom").exists()
)
DISK_AVAILABLE = CROSS_TRACK_DISK.exists()

requires_cross_track_fixtures = pytest.mark.skipif(
    not (ROMS_AVAILABLE and DISK_AVAILABLE),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {CROSS_TRACK_DISK}"
)

# Drive modes to test
DRIVE_MODES = [
    pytest.param("threaded", id="threaded"),
    pytest.param("synchronous", id="synchronous"),
    pytest.param("multiprocess", id="multiprocess"),
]

# Maximum cycles for operations
MAX_BOOT_CYCLES = 5_000_000
MAX_LOAD_CYCLES = 30_000_000  # Larger files need more time

# C64 memory addresses
KERNAL_KEYBOARD_BUFFER = 0x0277
KERNAL_KEYBOARD_COUNT = 0x00C6
BASIC_DIRECT_MODE_FLAG = 0x9D
KERNAL_STATUS = 0x90
BASIC_VARTAB_LO = 0x2D
BASIC_VARTAB_HI = 0x2E
BASIC_TXTTAB_LO = 0x2B
BASIC_TXTTAB_HI = 0x2C

# KERNAL status flags
KERNAL_STATUS_EOF = 0x40
KERNAL_STATUS_DEVICE_NOT_PRESENT = 0x80
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
    """Wait for LOAD operation to complete.

    Returns True if load completed successfully.
    """
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
    """Create a C64 instance with cross-track test disk."""
    c64 = C64(
        rom_dir=C64_ROMS_DIR,
        display_mode='headless',
        video_chip='6569',
    )
    c64.cpu.reset()

    c64.attach_drive(
        drive_rom_path=C64_ROMS_DIR / "1541.rom",
        disk_path=CROSS_TRACK_DISK,
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


@requires_cross_track_fixtures
class TestCrossTrackSameZone:
    """Test loading files spanning multiple tracks within the same zone."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_span_tracks_1_2_zone3(self, drive_runner):
        """Load SPAN1-2: 40 sectors across tracks 1-2 (Zone 3 only).

        This replicates the Tank Wars disk layout - a ~10KB file
        spanning the first two tracks, entirely within Zone 3.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Use inject_keyboard_string for longer commands
        c64.inject_keyboard_string('LOAD"SPAN1-2",8\r')

        assert wait_for_load(c64), "Load of SPAN1-2 timed out"

        # Verify program loaded correctly
        basic_start = c64.memory.read(BASIC_TXTTAB_LO) | (c64.memory.read(BASIC_TXTTAB_HI) << 8)
        assert basic_start == 0x0801, f"BASIC start should be $0801, got ${basic_start:04X}"

        # Check program size (40 sectors * ~254 bytes = ~10KB)
        program_size = get_loaded_program_size(c64)
        assert program_size > 9000, f"Program should be >9KB, got {program_size} bytes"


@requires_cross_track_fixtures
class TestCrossTrackZoneBoundaries:
    """Test loading files that cross zone boundaries (speed transitions)."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_span_zone3_to_zone2(self, drive_runner):
        """Load SPAN17-19: Crosses Zone 3 to Zone 2 boundary.

        Track 17 is Zone 3 (21 sectors/track)
        Track 18 is skipped (directory track)
        Track 19-20 are Zone 2 (19 sectors/track)

        This tests speed zone transition during loading.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"SPAN17-19",8\r')

        assert wait_for_load(c64), "Load of SPAN17-19 timed out (Zone 3->2 boundary)"

        program_size = get_loaded_program_size(c64)
        assert program_size > 9000, f"Program should be >9KB, got {program_size} bytes"

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_span_zone2_to_zone1(self, drive_runner):
        """Load SPAN24-26: Crosses Zone 2 to Zone 1 boundary.

        Track 24 is Zone 2 (19 sectors/track)
        Tracks 25-26 are Zone 1 (18 sectors/track)
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"SPAN24-26",8\r')

        assert wait_for_load(c64), "Load of SPAN24-26 timed out (Zone 2->1 boundary)"

        program_size = get_loaded_program_size(c64)
        assert program_size > 8000, f"Program should be >8KB, got {program_size} bytes"

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_span_zone1_to_zone0(self, drive_runner):
        """Load SPAN30-32: Crosses Zone 1 to Zone 0 boundary.

        Track 30 is Zone 1 (18 sectors/track)
        Tracks 31-32 are Zone 0 (17 sectors/track, slowest)
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"SPAN30-32",8\r')

        assert wait_for_load(c64), "Load of SPAN30-32 timed out (Zone 1->0 boundary)"

        program_size = get_loaded_program_size(c64)
        assert program_size > 8000, f"Program should be >8KB, got {program_size} bytes"


@requires_cross_track_fixtures
class TestCrossTrackDirectoryListing:
    """Test directory listing shows correct file sizes."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_load_directory(self, drive_runner):
        """Test LOAD"$",8 shows multi-block files correctly."""
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"$",8\r')

        assert wait_for_load(c64), "Directory listing load timed out"

        # Directory should load some data
        basic_end = c64.memory.read(BASIC_VARTAB_LO) | (c64.memory.read(BASIC_VARTAB_HI) << 8)
        assert basic_end > 0x0801, f"Directory should have data, end=${basic_end:04X}"
