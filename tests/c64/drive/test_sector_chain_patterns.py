"""Tests for loading files with various sector allocation patterns.

These tests verify the drive correctly handles non-sequential sector chains:
1. Interleaved allocation (standard 1541 pattern)
2. Wrap-around sector chains (S20 -> S0 within track)
3. Fragmented files (non-contiguous across tracks)
4. Backward track references

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
SECTOR_CHAIN_DISK = DISKS_DIR / "sector-chain-test.d64"

# Check if ROMs and disk are available
ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
    and (C64_ROMS_DIR / "1541.rom").exists()
)
DISK_AVAILABLE = SECTOR_CHAIN_DISK.exists()

requires_sector_chain_fixtures = pytest.mark.skipif(
    not (ROMS_AVAILABLE and DISK_AVAILABLE),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {SECTOR_CHAIN_DISK}"
)

# Drive modes to test
DRIVE_MODES = [
    pytest.param("threaded", id="threaded"),
    pytest.param("synchronous", id="synchronous"),
    pytest.param("multiprocess", id="multiprocess", marks=pytest.mark.slow),
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


def create_c64_with_disk(drive_runner: bool) -> C64:
    """Create a C64 instance with sector-chain test disk."""
    c64 = C64(
        rom_dir=C64_ROMS_DIR,
        display_mode='headless',
        video_chip='6569',
    )
    c64.cpu.reset()

    c64.attach_drive(
        drive_rom_path=C64_ROMS_DIR / "1541.rom",
        disk_path=SECTOR_CHAIN_DISK,
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


@requires_sector_chain_fixtures
class TestInterleavePattern:
    """Test loading files with interleaved sector allocation."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_interleaved_sector_chain(self, drive_runner):
        """Load INTERLEAVE: Sectors allocated with interleave 10 pattern.

        Sector chain: S0, S10, S20, S9, S19, S8, S18, S7, S17, S6, ...
        This is the standard 1541 allocation pattern for performance.
        Tests that non-sequential sector reads work correctly.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"INTERLEAVE",8\r')

        assert wait_for_load(c64), "Load of INTERLEAVE timed out"

        program_size = get_loaded_program_size(c64)
        assert program_size > 4000, f"Program should be >4KB, got {program_size} bytes"


@requires_sector_chain_fixtures
class TestWraparoundPattern:
    """Test loading files where sector chain wraps within a track."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_wraparound_sector_chain(self, drive_runner):
        """Load WRAPAROUND: Sector chain wraps S20 -> S0 within track.

        Sector chain: S15, S16, S17, S18, S19, S20, S0, S1, S2, ...
        Tests that the drive correctly handles sector number wrap-around.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"WRAPAROUND",8\r')

        assert wait_for_load(c64), "Load of WRAPAROUND timed out"

        program_size = get_loaded_program_size(c64)
        assert program_size > 4000, f"Program should be >4KB, got {program_size} bytes"


@requires_sector_chain_fixtures
class TestFragmentedFile:
    """Test loading files with non-contiguous sector allocation."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_fragmented_file_load(self, drive_runner):
        """Load FRAGMENTED: Sectors scattered across multiple tracks.

        Sector chain jumps between tracks 3, 4, 5 in non-sequential order.
        Tests head seeking during file load.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"FRAGMENTED",8\r')

        assert wait_for_load(c64), "Load of FRAGMENTED timed out"

        program_size = get_loaded_program_size(c64)
        assert program_size > 2000, f"Program should be >2KB, got {program_size} bytes"


@requires_sector_chain_fixtures
class TestBackwardTrackReferences:
    """Test loading files with backward track references in chain."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_backward_track_chain(self, drive_runner):
        """Load BACKWARD: Sector chain includes backward track jumps.

        Chain pattern: T6/S0 -> T5/S0 -> T4/S0 -> T6/S1 -> T5/S1 -> ...
        Tests that the drive correctly handles head movement in both directions.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"BACKWARD",8\r')

        assert wait_for_load(c64), "Load of BACKWARD timed out"

        program_size = get_loaded_program_size(c64)
        assert program_size > 4000, f"Program should be >4KB, got {program_size} bytes"
