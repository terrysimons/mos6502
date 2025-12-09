"""Tests for stress scenarios and edge cases.

These tests verify correct handling of:
1. Completely full disk (0 blocks free) with max loadable file (153 sectors)
2. Memory overflow (negative test): 154-sector file exceeds BASIC memory
3. Maximum directory entries (144 files)
4. Reverse zone spanning (Zone 1 -> Zone 2)

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

FULL_DISK = DISKS_DIR / "full-disk.d64"
OVERFLOW_DISK = DISKS_DIR / "overflow-test.d64"
MAX_DIR_DISK = DISKS_DIR / "max-directory.d64"
REVERSE_DISK = DISKS_DIR / "reverse-zone-span.d64"

# Check if ROMs are available
ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
    and (C64_ROMS_DIR / "1541.rom").exists()
)

requires_full_fixtures = pytest.mark.skipif(
    not ROMS_AVAILABLE or not FULL_DISK.exists(),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {FULL_DISK}"
)

requires_overflow_fixtures = pytest.mark.skipif(
    not ROMS_AVAILABLE or not OVERFLOW_DISK.exists(),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {OVERFLOW_DISK}"
)

requires_max_dir_fixtures = pytest.mark.skipif(
    not ROMS_AVAILABLE or not MAX_DIR_DISK.exists(),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {MAX_DIR_DISK}"
)

requires_reverse_fixtures = pytest.mark.skipif(
    not ROMS_AVAILABLE or not REVERSE_DISK.exists(),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {REVERSE_DISK}"
)

# Drive modes to test
DRIVE_MODES = [
    pytest.param(True, id="threaded-drive"),
    pytest.param(False, id="synchronous-drive"),
]

# Maximum cycles for operations
MAX_BOOT_CYCLES = 5_000_000
MAX_LOAD_CYCLES = 50_000_000  # Large files need more time

# C64 BASIC memory limits:
# BASIC programs load at $0801 and can extend up to $A000 (screen memory)
# $A000 - $0801 = 38911 bytes maximum
# Each disk sector holds 254 bytes of file data (256 - 2 byte link)
# Max loadable file: 38911 / 254 ≈ 153 sectors
MAX_BASIC_PROGRAM_SIZE = 0xA000 - 0x0801  # 38911 bytes
MAX_LOADABLE_SECTORS = MAX_BASIC_PROGRAM_SIZE // 254  # ~153 sectors

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


def create_c64_with_disk(disk_path: Path, threaded_drive: bool) -> C64:
    """Create a C64 instance with the specified disk."""
    c64 = C64(
        rom_dir=C64_ROMS_DIR,
        display_mode='headless',
        video_chip='6569',
    )
    c64.cpu.reset()

    c64.attach_drive(
        drive_rom_path=C64_ROMS_DIR / "1541.rom",
        disk_path=disk_path,
        threaded=threaded_drive,
    )
    return c64


@requires_full_fixtures
class TestCompletelyFullDisk:
    """Test loading from a completely full disk (0 blocks free)."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_load_from_full_disk(self, threaded_drive):
        """Load FULLFILE from a completely full disk.

        Tests that the emulator handles disks with no free space.
        The file uses 153 sectors (max that fits in BASIC memory $0801-$A000),
        with remaining sectors filled to make disk completely full.
        """
        c64 = create_c64_with_disk(FULL_DISK, threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"FULLFILE",8\r')

        # 153 sectors at ~300 bytes/sec = ~130 seconds, ~130M cycles
        # Add margin for IEC protocol overhead
        assert wait_for_load(c64, max_cycles=200_000_000), \
            "Load of FULLFILE timed out (full disk)"

        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"


@requires_overflow_fixtures
class TestMemoryOverflow:
    """Test that loading a file larger than BASIC memory overflows past $A000.

    A 154-sector file (~39KB) exceeds the BASIC memory area ($0801-$A000 = ~38KB).
    Loading such a file will set VARTAB past the normal BASIC limit, demonstrating
    the memory overflow behavior.
    """

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_overflow_exceeds_basic_memory(self, threaded_drive):
        """Load OVERFLOW (154 sectors) - VARTAB should exceed $A000.

        This test verifies that loading a 154-sector file causes BASIC's
        VARTAB pointer to be set past $A000, confirming the file overflows
        the normal BASIC memory area. The C64 KERNAL doesn't prevent this -
        it's the programmer's responsibility to not load files too large.
        """
        c64 = create_c64_with_disk(OVERFLOW_DISK, threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"OVERFLOW",8\r')

        # Wait for load to complete
        assert wait_for_load(c64, max_cycles=250_000_000), \
            "Load of OVERFLOW timed out"

        # Verify VARTAB exceeds $A000 (BASIC memory limit)
        vartab = (c64.memory.read(BASIC_VARTAB_LO) |
                  (c64.memory.read(BASIC_VARTAB_HI) << 8))

        assert vartab > 0xA000, \
            f"VARTAB ${vartab:04X} should exceed $A000 for 154-sector file"


@requires_max_dir_fixtures
class TestMaxDirectoryEntries:
    """Test loading from a disk with maximum directory entries."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_load_first_of_144_files(self, threaded_drive):
        """Load F001 (first file in a 144-file directory).

        Tests that the emulator handles maximum directory entries.
        """
        c64 = create_c64_with_disk(MAX_DIR_DISK, threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"F001",8\r')

        assert wait_for_load(c64), "Load of F001 timed out"

        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_load_last_of_144_files(self, threaded_drive):
        """Load F144 (last file in a 144-file directory).

        Tests that the emulator can traverse an 18-sector directory chain.
        """
        c64 = create_c64_with_disk(MAX_DIR_DISK, threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"F144",8\r')

        assert wait_for_load(c64), "Load of F144 timed out (last of 144 files)"

        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_load_directory_with_144_files(self, threaded_drive):
        """LOAD"$",8 on a disk with 144 files.

        Tests directory listing with maximum entries across 18 directory sectors.
        """
        c64 = create_c64_with_disk(MAX_DIR_DISK, threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"$",8\r')

        # Directory listing needs more time with 144 entries
        assert wait_for_load(c64, max_cycles=30_000_000), \
            "Directory listing timed out (144 files)"

        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"


@requires_reverse_fixtures
class TestReverseZoneSpan:
    """Test loading files that span zones in reverse order."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_reverse_zone_span(self, threaded_drive):
        """Load REVERSE which spans from Zone 1 back to Zone 2.

        Tests that the emulator handles backward zone transitions correctly.
        File starts on track 25 (Zone 1) and jumps back to track 24 (Zone 2).
        """
        c64 = create_c64_with_disk(REVERSE_DISK, threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        c64.inject_keyboard_string('LOAD"REVERSE",8\r')

        assert wait_for_load(c64), "Load of REVERSE timed out (reverse zone span)"

        kernal_status = c64.memory.read(KERNAL_STATUS)
        assert (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0, \
            f"KERNAL error: ${kernal_status:02X}"
