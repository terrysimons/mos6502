"""Tests for disk loading from all 4 speed zones.

D64 disk format uses 4 speed zones with different sector counts:
- Zone 3: Tracks 1-17 (21 sectors/track)
- Zone 2: Tracks 18-24 (19 sectors/track) - Track 18 is directory
- Zone 1: Tracks 25-30 (18 sectors/track)
- Zone 0: Tracks 31-35 (17 sectors/track)

This test uses simple-zone-test.d64 which has files on each zone
to verify disk loading works correctly across all zones.
"""

import pytest
from systems.c64 import C64
from mos6502 import errors

from .conftest import (
    C64_ROMS_DIR,
    DISKS_DIR,
    ROMS_AVAILABLE,
    DRIVE_MODES,
    MAX_BOOT_CYCLES,
    MAX_LOAD_CYCLES,
    KERNAL_KEYBOARD_BUFFER,
    KERNAL_KEYBOARD_COUNT,
    BASIC_DIRECT_MODE_FLAG,
    KERNAL_STATUS,
    BASIC_VARTAB_LO,
    BASIC_VARTAB_HI,
    PETSCII_RETURN,
    KERNAL_STATUS_EOF,
    KERNAL_STATUS_ERROR_MASK,
)

ZONE_TEST_DISK = DISKS_DIR / "simple-zone-test.d64"
DISK_AVAILABLE = ZONE_TEST_DISK.exists()

requires_disk_test_fixtures = pytest.mark.skipif(
    not (ROMS_AVAILABLE and DISK_AVAILABLE),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {ZONE_TEST_DISK}"
)


def run_cycles(c64, cycles):
    """Run CPU for specified cycles, catching exhaustion exception."""
    try:
        c64.cpu.execute(cycles=cycles)
    except errors.CPUCycleExhaustionError:
        pass  # Expected when cycles run out


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


def create_c64_with_disk(drive_runner: str) -> C64:
    """Create a C64 instance with disk drive.

    Args:
        drive_runner: Drive runner mode ("threaded", "synchronous", "multiprocess")
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
        runner=drive_runner,
    )
    return c64


@requires_disk_test_fixtures
class TestDirectoryListing:
    """Test loading directory listing from disk."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_load_directory(self, drive_runner, c64_cleanup):
        """Test LOAD"$",8 loads directory listing."""
        c64 = c64_cleanup.register(create_c64_with_disk(drive_runner=drive_runner))

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

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_track01_first_track(self, drive_runner):
        """Load file from Track 1 (first track in Zone 3)."""
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST1*",8\r')
        assert wait_for_load(c64), "Load from Track 1 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_track17_last_before_directory(self, drive_runner):
        """Load file from Track 17 (last track before directory in Zone 3)."""
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST2*",8\r')
        assert wait_for_load(c64), "Load from Track 17 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801


@requires_disk_test_fixtures
class TestZone2Loading:
    """Test loading files from Zone 2 (Tracks 18-24, 19 sectors/track)."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_track19_first_after_directory(self, drive_runner):
        """Load file from Track 19 (first track after directory in Zone 2)."""
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST3*",8\r')
        assert wait_for_load(c64), "Load from Track 19 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_track24_last_in_zone(self, drive_runner):
        """Load file from Track 24 (last track in Zone 2)."""
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST4*",8\r')
        assert wait_for_load(c64), "Load from Track 24 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801


@requires_disk_test_fixtures
class TestZone1Loading:
    """Test loading files from Zone 1 (Tracks 25-30, 18 sectors/track)."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_track25_first_in_zone(self, drive_runner):
        """Load file from Track 25 (first track in Zone 1)."""
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST5*",8\r')
        assert wait_for_load(c64), "Load from Track 25 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_track30_last_in_zone(self, drive_runner):
        """Load file from Track 30 (last track in Zone 1)."""
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST6*",8\r')
        assert wait_for_load(c64), "Load from Track 30 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801


@requires_disk_test_fixtures
class TestZone0Loading:
    """Test loading files from Zone 0 (Tracks 31-35, 17 sectors/track)."""

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_track31_first_in_zone(self, drive_runner):
        """Load file from Track 31 (first track in Zone 0)."""
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST7*",8\r')
        assert wait_for_load(c64), "Load from Track 31 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801

    @pytest.mark.parametrize("drive_runner", DRIVE_MODES)
    def test_track35_last_track(self, drive_runner):
        """Load file from Track 35 (last track on disk, Zone 0)."""
        c64 = create_c64_with_disk(drive_runner=drive_runner)

        assert wait_for_ready(c64), "Failed to boot to BASIC"
        inject_keyboard_command(c64, 'LOAD"TEST8*",8\r')
        assert wait_for_load(c64), "Load from Track 35 timed out"

        basic_start = c64.memory.read(0x2B) | (c64.memory.read(0x2C) << 8)
        assert basic_start == 0x0801
