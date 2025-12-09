"""Tests for directory edge cases.

These tests verify correct handling of:
1. Multi-sector directories (>8 entries, requiring 2+ directory sectors)
2. Deleted file entries ($00 file type in directory)
3. Loading files from various positions in directory

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
DIR_EDGE_DISK = DISKS_DIR / "directory-edge-test.d64"

# Check if ROMs and disk are available
ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
    and (C64_ROMS_DIR / "1541.rom").exists()
)
DISK_AVAILABLE = DIR_EDGE_DISK.exists()

requires_dir_edge_fixtures = pytest.mark.skipif(
    not (ROMS_AVAILABLE and DISK_AVAILABLE),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {DIR_EDGE_DISK}"
)

# Drive modes to test
DRIVE_MODES = [
    pytest.param(True, id="threaded-drive"),
    pytest.param(False, id="synchronous-drive"),
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
    """Wait for LOAD operation to complete.

    Detects completion by checking for BASIC_VARTAB change.
    For minimal files that don't change VARTAB, use wait_for_load_or_ready.
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


def create_c64_with_disk(threaded_drive: bool) -> C64:
    """Create a C64 instance with directory edge case test disk."""
    c64 = C64(
        rom_dir=C64_ROMS_DIR,
        display_mode='headless',
        video_chip='6569',
    )
    c64.cpu.reset()

    c64.attach_drive(
        drive_rom_path=C64_ROMS_DIR / "1541.rom",
        disk_path=DIR_EDGE_DISK,
        threaded=threaded_drive,
    )
    return c64


@requires_dir_edge_fixtures
class TestMultiSectorDirectory:
    """Test loading files from multi-sector directories."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_load_from_first_directory_sector(self, threaded_drive):
        """Load FILE-01 from first directory sector.

        Tests that files in the first 8 entries (first dir sector) load correctly.
        """
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"FILE-01",8\r')

        assert wait_for_load(c64), "Load of FILE-01 timed out"

        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_load_from_second_directory_sector(self, threaded_drive):
        """Load FILE-11 from second directory sector.

        Tests that files in entries 9+ (second dir sector) load correctly.
        The drive must follow the directory chain from sector 1 to sector 2.
        """
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"FILE-11",8\r')

        assert wait_for_load(c64), "Load of FILE-11 timed out (second dir sector)"

        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_load_last_file_in_directory(self, threaded_drive):
        """Load FILE-12 (last file in directory).

        Tests that the last file in a multi-sector directory loads correctly.
        """
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"FILE-12",8\r')

        assert wait_for_load(c64), "Load of FILE-12 timed out (last file)"

        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"


@requires_dir_edge_fixtures
class TestDeletedFileEntries:
    """Test directory parsing with deleted file entries."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_load_file_after_deleted_entry(self, threaded_drive):
        """Load FILE-06 which comes after a deleted entry (FILE-05).

        Tests that the drive correctly skips deleted entries ($00 file type)
        when searching for files.
        """
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"FILE-06",8\r')

        assert wait_for_load(c64), "Load of FILE-06 timed out (after deleted entry)"

        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_load_file_after_multiple_deletions(self, threaded_drive):
        """Load FILE-11 which comes after FILE-10 (deleted in second sector).

        Tests directory parsing across sectors with deleted entries.
        """
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"FILE-11",8\r')

        assert wait_for_load(c64), "Load of FILE-11 timed out"

        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"


@requires_dir_edge_fixtures
class TestDirectoryListing:
    """Test directory listing with edge cases."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_load_directory_multi_sector(self, threaded_drive):
        """LOAD"$",8 on a disk with multi-sector directory.

        Tests that directory listing correctly follows sector chain.
        """
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"$",8\r')

        assert wait_for_load(c64), "Directory listing timed out"

        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"
