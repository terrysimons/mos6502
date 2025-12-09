"""Tests for disk loading from all 4 speed zones.

D64 disk format uses 4 speed zones with different sector counts:
- Zone 3: Tracks 1-17 (21 sectors/track)
- Zone 2: Tracks 18-24 (19 sectors/track) - Track 18 is directory
- Zone 1: Tracks 25-30 (18 sectors/track)
- Zone 0: Tracks 31-35 (17 sectors/track)

This test uses simple-zone-test.d64 which has files on each zone
to verify disk loading works correctly across all zones.

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
ZONE_TEST_DISK = DISKS_DIR / "simple-zone-test.d64"

# Check if ROMs and disk are available
ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
    and (C64_ROMS_DIR / "1541.rom").exists()
)
DISK_AVAILABLE = ZONE_TEST_DISK.exists()

requires_disk_test_fixtures = pytest.mark.skipif(
    not (ROMS_AVAILABLE and DISK_AVAILABLE),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {ZONE_TEST_DISK}"
)

# Drive modes to test
DRIVE_MODES = [
    pytest.param(True, id="threaded-drive"),
    pytest.param(False, id="synchronous-drive"),
]

# Maximum cycles for operations (~20 seconds at 1MHz)
MAX_BOOT_CYCLES = 5_000_000
MAX_LOAD_CYCLES = 20_000_000


def run_cycles(c64, cycles):
    """Run CPU for specified cycles, catching exhaustion exception."""
    try:
        c64.cpu.execute(cycles=cycles)
    except errors.CPUCycleExhaustionError:
        pass  # Expected when cycles run out


# C64 zero page and I/O addresses
KERNAL_KEYBOARD_BUFFER = 0x0277  # Keyboard buffer ($0277-$0280, 10 bytes)
KERNAL_KEYBOARD_COUNT = 0x00C6  # Number of characters in keyboard buffer
BASIC_DIRECT_MODE_FLAG = 0x9D   # Bit 7 set = direct mode (READY prompt)
KERNAL_STATUS = 0x90            # KERNAL I/O status byte
BASIC_VARTAB_LO = 0x2D          # Start of BASIC variables (end of program) low byte
BASIC_VARTAB_HI = 0x2E          # Start of BASIC variables (end of program) high byte
PETSCII_RETURN = 0x0D           # PETSCII code for RETURN key

# KERNAL status byte flags ($90)
KERNAL_STATUS_EOF = 0x40         # Bit 6: End of file (normal after successful load)
KERNAL_STATUS_DEVICE_NOT_PRESENT = 0x80  # Bit 7: Device not present
KERNAL_STATUS_TIMEOUT = 0x03     # Bits 0-1: Read/write timeout errors
KERNAL_STATUS_ERROR_MASK = 0x83  # Mask for error bits (excludes EOF which is normal)


def inject_keyboard_command(c64, text):
    """Inject a command string into the C64 keyboard buffer.

    This uses the C64's inject_keyboard_string method which handles
    strings longer than 10 characters by chunking and running CPU
    cycles between chunks to let the KERNAL process the buffer.
    """
    c64.inject_keyboard_string(text)


def wait_for_ready(c64, max_cycles=MAX_BOOT_CYCLES):
    """Wait for BASIC READY prompt by checking direct mode flag."""
    cycles_run = 0
    batch_size = 100_000

    while cycles_run < max_cycles:
        run_cycles(c64, batch_size)
        cycles_run += batch_size

        # Check if BASIC is in direct mode (bit 7 set = ready for input)
        status = c64.memory.read(BASIC_DIRECT_MODE_FLAG)
        if status & 0x80:
            return True

    return False


def wait_for_load(c64, max_cycles=MAX_LOAD_CYCLES):
    """Wait for LOAD operation to complete.

    Returns True if load completed successfully (READY prompt appears).
    Detects completion by checking if BASIC variable table pointer changed
    (indicating data was loaded into BASIC memory).
    """
    cycles_run = 0
    batch_size = 100_000

    # Record initial BASIC end pointer - it should change after successful load
    initial_basic_end = (c64.memory.read(BASIC_VARTAB_LO) |
                         (c64.memory.read(BASIC_VARTAB_HI) << 8))

    while cycles_run < max_cycles:
        run_cycles(c64, batch_size)
        cycles_run += batch_size

        # Check if BASIC is in direct mode (bit 7 set = ready for input)
        status = c64.memory.read(BASIC_DIRECT_MODE_FLAG)
        in_direct_mode = (status & 0x80) != 0

        # KERNAL status - check for errors (EOF flag $40 is normal after load)
        kernal_status = c64.memory.read(KERNAL_STATUS)
        no_errors = (kernal_status & KERNAL_STATUS_ERROR_MASK) == 0

        # Check if BASIC end pointer changed (indicates something was loaded)
        current_basic_end = (c64.memory.read(BASIC_VARTAB_LO) |
                             (c64.memory.read(BASIC_VARTAB_HI) << 8))
        data_loaded = current_basic_end != initial_basic_end

        # Load complete when: in direct mode, no errors, and data was loaded
        if in_direct_mode and no_errors and data_loaded:
            return True

    return False


def create_c64_with_disk(threaded_drive: bool) -> C64:
    """Create a C64 instance with disk drive.

    Args:
        threaded_drive: True for threaded IEC bus, False for synchronous
    """
    c64 = C64(
        rom_dir=C64_ROMS_DIR,
        display_mode='headless',
        video_chip='6569',
    )
    # Must reset CPU after creating C64 to read reset vectors from ROM
    c64.cpu.reset()

    # Attach drive and insert disk
    c64.attach_drive(
        drive_rom_path=C64_ROMS_DIR / "1541.rom",
        disk_path=ZONE_TEST_DISK,
        threaded=threaded_drive,
    )
    return c64


@requires_disk_test_fixtures
class TestDirectoryListing:
    """Test loading directory listing from disk."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_load_directory(self, threaded_drive):
        """Test LOAD"$",8 loads directory listing."""
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        inject_keyboard_command(c64, 'LOAD"$",8\r')

        assert wait_for_load(c64), "Directory listing load timed out"

        # Verify directory loaded - check BASIC end pointer moved
        basic_end_lo = c64.memory.read(0x2D)  # VARTAB low
        basic_end_hi = c64.memory.read(0x2E)  # VARTAB high
        basic_end = basic_end_lo | (basic_end_hi << 8)

        assert basic_end > 0x0801, f"Directory should have loaded data, end=${basic_end:04X}"


@requires_disk_test_fixtures
class TestZone3Loading:
    """Test loading files from Zone 3 (Tracks 1-17, 21 sectors/track)."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_track01_first_track(self, threaded_drive):
        """Load file from Track 1 (first track in Zone 3)."""
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST1*",8\r')
        assert wait_for_load(c64), "Load from Track 1 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_track17_last_before_directory(self, threaded_drive):
        """Load file from Track 17 (last track before directory in Zone 3)."""
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST2*",8\r')
        assert wait_for_load(c64), "Load from Track 17 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801


@requires_disk_test_fixtures
class TestZone2Loading:
    """Test loading files from Zone 2 (Tracks 18-24, 19 sectors/track)."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_track19_first_after_directory(self, threaded_drive):
        """Load file from Track 19 (first track after directory in Zone 2)."""
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST3*",8\r')
        assert wait_for_load(c64), "Load from Track 19 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_track24_last_in_zone(self, threaded_drive):
        """Load file from Track 24 (last track in Zone 2)."""
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST4*",8\r')
        assert wait_for_load(c64), "Load from Track 24 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801


@requires_disk_test_fixtures
class TestZone1Loading:
    """Test loading files from Zone 1 (Tracks 25-30, 18 sectors/track)."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_track25_first_in_zone(self, threaded_drive):
        """Load file from Track 25 (first track in Zone 1)."""
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST5*",8\r')
        assert wait_for_load(c64), "Load from Track 25 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_track30_last_in_zone(self, threaded_drive):
        """Load file from Track 30 (last track in Zone 1)."""
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST6*",8\r')
        assert wait_for_load(c64), "Load from Track 30 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801


@requires_disk_test_fixtures
class TestZone0Loading:
    """Test loading files from Zone 0 (Tracks 31-35, 17 sectors/track)."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_track31_first_in_zone(self, threaded_drive):
        """Load file from Track 31 (first track in Zone 0)."""
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST7*",8\r')
        assert wait_for_load(c64), "Load from Track 31 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_track35_last_track(self, threaded_drive):
        """Load file from Track 35 (last track on disk, Zone 0)."""
        c64 = create_c64_with_disk(threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST8*",8\r')
        assert wait_for_load(c64), "Load from Track 35 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801
