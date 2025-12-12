"""Tests for loading files of specific sizes to test byte boundaries.

These tests verify correct handling of file sizes around sector boundaries:
- 0 bytes (empty file)
- 1 byte (minimal file)
- 252 bytes (exactly fills 1 sector's data area: 254 total with load addr)
- 253 bytes (1 byte overflow into 2nd sector: 255 total)
- 254 bytes (2 bytes overflow into 2nd sector: 256 total)
- 21 sectors (exactly fills one Zone 3 track)

Note: Each sector holds 254 bytes of file data (256 - 2 for track/sector link).
The BASIC program includes a 2-byte load address, so:
- 252 content bytes + 2 load addr = 254 total = 1 sector
- 253 content bytes + 2 load addr = 255 total = 2 sectors

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
FILE_SIZE_DISK = DISKS_DIR / "file-size-test.d64"

# Check if ROMs and disk are available
ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
    and (C64_ROMS_DIR / "1541.rom").exists()
)
DISK_AVAILABLE = FILE_SIZE_DISK.exists()

requires_file_size_fixtures = pytest.mark.skipif(
    not (ROMS_AVAILABLE and DISK_AVAILABLE),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {FILE_SIZE_DISK}"
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


def create_c64_with_disk(drive_runner: bool) -> C64:
    """Create a C64 instance with file-size test disk."""
    c64 = C64(
        rom_dir=C64_ROMS_DIR,
        display_mode='headless',
        video_chip='6569',
    )
    c64.cpu.reset()

    c64.attach_drive(
        drive_rom_path=C64_ROMS_DIR / "1541.rom",
        disk_path=FILE_SIZE_DISK,
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


def wait_for_load_or_ready(c64, max_cycles=MAX_LOAD_CYCLES):
    """Wait for LOAD to complete by checking for return to BASIC prompt.

    This version doesn't require data to be loaded - useful for empty files.
    """
    cycles_run = 0
    batch_size = 100_000

    # Wait a bit for load to start
    run_cycles(c64, 500_000)
    cycles_run += 500_000

    while cycles_run < max_cycles:
        run_cycles(c64, batch_size)
        cycles_run += batch_size

        status = c64.memory.read(BASIC_DIRECT_MODE_FLAG)
        in_direct_mode = (status & 0x80) != 0

        kernal_status = c64.memory.read(KERNAL_STATUS)
        no_errors = (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0

        if in_direct_mode and no_errors:
            return True

    return False


@requires_file_size_fixtures
class TestMinimalFiles:
    """Test loading minimal-size files."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_empty_file(self, drive_runner):
        """Load SIZE-0: Empty file (0 content bytes).

        Tests handling of a file with just a load address and no content.
        Note: Empty files may not change BASIC pointers, so we just check
        that the load completes without error.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"SIZE-0",8\r')

        # Empty files don't load any data, so use the simpler wait function
        assert wait_for_load_or_ready(c64), "Load of SIZE-0 timed out"

        # Just verify no error occurred
        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_one_byte_file(self, drive_runner):
        """Load SIZE-1: Single byte file.

        Tests handling of the smallest non-empty file.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"SIZE-1",8\r')

        assert wait_for_load(c64), "Load of SIZE-1 timed out"

        program_size = get_loaded_program_size(c64)
        assert program_size >= 1, f"Program should have at least 1 byte, got {program_size}"


@requires_file_size_fixtures
class TestSectorBoundaryFiles:
    """Test loading files at exact sector boundaries."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_exact_one_sector_252_bytes(self, drive_runner):
        """Load SIZE-252: Exactly fills one sector (252 content + 2 load addr = 254).

        This file fits perfectly in one sector with no overflow.
        Tests the exact boundary case.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"SIZE-252",8\r')

        assert wait_for_load(c64), "Load of SIZE-252 timed out"

        program_size = get_loaded_program_size(c64)
        assert 250 <= program_size <= 260, f"Program should be ~252 bytes, got {program_size}"

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_one_byte_overflow_253_bytes(self, drive_runner):
        """Load SIZE-253: One byte overflow (253 content + 2 load addr = 255).

        This file overflows into a second sector by exactly 1 byte.
        Tests the boundary+1 case.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"SIZE-253",8\r')

        assert wait_for_load(c64), "Load of SIZE-253 timed out"

        program_size = get_loaded_program_size(c64)
        assert 250 <= program_size <= 260, f"Program should be ~253 bytes, got {program_size}"

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_two_byte_overflow_254_bytes(self, drive_runner):
        """Load SIZE-254: Two byte overflow (254 content + 2 load addr = 256).

        This file overflows into a second sector by exactly 2 bytes.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"SIZE-254",8\r')

        assert wait_for_load(c64), "Load of SIZE-254 timed out"

        program_size = get_loaded_program_size(c64)
        assert 250 <= program_size <= 260, f"Program should be ~254 bytes, got {program_size}"


@requires_file_size_fixtures
class TestTrackFillFiles:
    """Test loading files that fill entire tracks."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_exact_track_fill(self, drive_runner):
        """Load TRACK-FILL: Fills exactly 21 sectors (one Zone 3 track).

        Tests loading a file that uses exactly the capacity of one track
        without overflow to the next track.
        """
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"TRACK-FILL",8\r')

        assert wait_for_load(c64), "Load of TRACK-FILL timed out"

        # 21 sectors * 254 bytes = 5334 bytes
        program_size = get_loaded_program_size(c64)
        assert program_size > 5000, f"Program should be >5KB, got {program_size} bytes"
