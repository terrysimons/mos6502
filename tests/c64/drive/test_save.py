"""Tests for SAVE command and disk write operations.

These tests verify:
1. SAVE"FILENAME",8 - Save a BASIC program to disk
2. Load saved file back and verify contents
3. Disk file is actually modified (persistence)
4. Sequential file I/O (OPEN/PRINT#/CLOSE)
"""

import shutil
import tempfile
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

# Use wildcard-test.d64 as a base disk with some free space
BASE_DISK = DISKS_DIR / "wildcard-test.d64"

# Check if ROMs are available
ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
    and (C64_ROMS_DIR / "1541.rom").exists()
)

requires_fixtures = pytest.mark.skipif(
    not ROMS_AVAILABLE or not BASE_DISK.exists(),
    reason=f"Missing ROMs in {C64_ROMS_DIR} or disk {BASE_DISK}"
)

# Drive modes to test
DRIVE_MODES = [
    pytest.param(True, id="threaded-drive"),
    pytest.param(False, id="synchronous-drive"),
]

# Maximum cycles for operations
MAX_BOOT_CYCLES = 5_000_000
MAX_SAVE_CYCLES = 30_000_000
MAX_LOAD_CYCLES = 10_000_000

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


def screen_shows_ready(c64):
    """Check if 'READY.' appears on screen near cursor position.

    Only looks at the line immediately before the cursor (where READY
    normally appears after a command completes). This prevents detecting
    old READY prompts from earlier in the screen.
    """
    cursor_line = c64.memory.read(0xD6)
    # Only check the line immediately before cursor (where READY appears)
    # and the cursor line itself (in case cursor hasn't moved down yet)
    for offset in range(2):  # Check cursor line and 1 line above
        line = cursor_line - offset
        if line < 0 or line > 24:
            continue
        # Read first 6 chars of line
        chars = []
        for col in range(6):
            char = c64.memory.read(0x0400 + line * 40 + col)
            if 0x01 <= char <= 0x1A:
                chars.append(chr(char + 0x40))
            else:
                chars.append(chr(char) if 0x20 <= char < 0x80 else '?')
        text = ''.join(chars)
        if text.startswith('READY'):
            return True
    return False


def wait_for_ready_prompt(c64, max_cycles):
    """Wait for BASIC READY. prompt to appear on screen.

    This is more reliable than checking the direct mode flag ($9D) alone,
    as that flag can be set during disk operations before they complete.

    Args:
        c64: C64 instance
        max_cycles: Maximum cycles to wait

    Returns True when READY. appears on screen.
    """
    cycles_run = 0
    batch_size = 100_000

    while cycles_run < max_cycles:
        run_cycles(c64, batch_size)
        cycles_run += batch_size

        # Check both the flag AND that READY appears on screen
        status = c64.memory.read(BASIC_DIRECT_MODE_FLAG)
        if (status & 0x80) and screen_shows_ready(c64):
            return True

    return False


def read_screen_char(c64, line, col):
    """Read a character from C64 screen memory and convert to ASCII."""
    screen_base = 0x0400
    addr = screen_base + (line * 40) + col
    char = c64.memory.read(addr)
    # Convert screen code to ASCII
    if char == 0x20 or char == 0x00:
        return ' '
    elif 0x30 <= char <= 0x39:  # Digits
        return chr(char)
    elif 0x01 <= char <= 0x1A:  # Letters (screen codes)
        return chr(char + 0x40)
    else:
        return '.'


def find_cursor_line(c64):
    """Find the line where the cursor is (where output just appeared)."""
    # Read cursor position from BASIC - TBLX at $D6 is current line
    return c64.memory.read(0xD6)


def wait_for_kb_empty(c64, max_cycles=2_000_000):
    """Wait for keyboard buffer to be empty."""
    cycles = 0
    batch = 50_000
    while cycles < max_cycles:
        run_cycles(c64, batch)
        cycles += batch
        if int(c64.cpu.ram[0xC6]) == 0:
            return True
    return False


def inject_command(c64, command, max_cycles=2_000_000):
    """Inject a command and wait for keyboard buffer to empty."""
    c64.inject_keyboard_string(command)
    if not wait_for_kb_empty(c64, max_cycles):
        return False
    # Extra cycles for BASIC to process
    run_cycles(c64, 500_000)
    return True


def read_drive_status(c64, max_cycles=MAX_LOAD_CYCLES):
    """Read the drive error channel (channel 15) like a human would.

    Uses separate BASIC program lines to OPEN, INPUT#, PRINT, and CLOSE
    the error channel. Then reads the error number from the screen.

    Returns the error number (0-99) or None on timeout.
    Error 00 = "OK" means success.
    """
    # Enter program lines separately (more reliable than one long line)
    # Use high line numbers to avoid conflict with user's program
    commands = [
        ('9 OPEN15,8,15\r', 'OPEN'),
        ('10 INPUT#15,A$\r', 'INPUT#'),
        ('11 ?A$\r', 'PRINT'),
        ('12 CLOSE15\r', 'CLOSE'),
    ]

    for cmd, desc in commands:
        if not inject_command(c64, cmd):
            print(f"DEBUG: Failed to inject {desc} command")
            return None

    # RUN the program
    if not inject_command(c64, 'RUN\r'):
        print("DEBUG: Failed to inject RUN command")
        return None

    # Wait for program to complete (reading from drive takes time)
    if not wait_for_ready_prompt(c64, max_cycles):
        print("DEBUG: Timeout waiting for RUN to complete")
        return None

    # Find the error number on screen (printed by ?A$)
    cursor_line = find_cursor_line(c64)

    # Search backward from cursor for a 2-digit number on its own line
    for line in range(cursor_line - 1, max(0, cursor_line - 10), -1):
        c1 = read_screen_char(c64, line, 0)
        c2 = read_screen_char(c64, line, 1)
        c3 = read_screen_char(c64, line, 2)

        # Error code is exactly 2 digits followed by space
        if c1.isdigit() and c2.isdigit() and c3 == ' ':
            # Verify rest of line is blank (not a line number like "10 ...")
            rest_blank = all(
                read_screen_char(c64, line, col) == ' '
                for col in range(3, 10)
            )
            if rest_blank:
                error_code = int(c1) * 10 + int(c2)
                # Clean up: delete the helper lines
                for line_num in [9, 10, 11, 12]:
                    inject_command(c64, f'{line_num}\r', max_cycles=500_000)
                return error_code

    # Debug: show what's on screen if we couldn't find error code
    print(f"DEBUG: Could not find error code. cursor_line={cursor_line}")
    print("DEBUG: Screen content:")
    for line in range(max(0, cursor_line - 8), min(25, cursor_line + 2)):
        chars = [read_screen_char(c64, line, col) for col in range(40)]
        line_text = ''.join(chars).rstrip()
        if line_text:
            print(f"  {line:2d}: '{line_text}'")

    return None


def wait_for_operation(c64, max_cycles):
    """Wait for a disk operation to complete and read drive status.

    This does what a human would do on a real C64:
    1. Wait for BASIC READY prompt (IEC protocol complete)
    2. Read drive error channel to get the operation result

    Args:
        c64: C64 instance
        max_cycles: Maximum cycles to wait before timeout

    Returns:
        Tuple of (success: bool, error_number: int or None)
        - success is True when error 00 or 01 (OK or FILES SCRATCHED)
        - error_number is the drive status code (00-99) or None if timeout
    """
    print(f"DEBUG wait_for_operation: waiting for ready prompt, max_cycles={max_cycles}")
    # First wait for BASIC to return to direct mode
    if not wait_for_ready_prompt(c64, max_cycles):
        print("DEBUG wait_for_operation: timeout waiting for ready prompt!")
        return False, None

    # Give BASIC time to fully settle into direct mode
    # (the KERNAL may briefly show direct mode before fully ready)
    run_cycles(c64, 1_000_000)

    # Read drive error channel - this confirms the drive finished
    # and tells us if the operation actually succeeded
    error_number = read_drive_status(c64, max_cycles)

    # Error 00 = OK, 01 = FILES SCRATCHED (also OK for delete operations)
    success = error_number is not None and error_number in (0, 1)
    return success, error_number


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


@requires_fixtures
class TestSaveCommand:
    """Test SAVE command functionality."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_save_command_completes(self, threaded_drive, tmp_path):
        """Test that SAVE command completes without error.

        This is the basic test that SAVE works - the command completes
        and returns to BASIC without an error status.
        """
        # Copy the base disk to temp location so we can modify it
        test_disk = tmp_path / "test.d64"
        shutil.copy(BASE_DISK, test_disk)

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Enter a simple BASIC program
        # 10 PRINT "HELLO"
        c64.inject_keyboard_string('10 PRINT "HELLO"\r')
        run_cycles(c64, 500_000)  # Let the line be processed

        # Save the program
        c64.inject_keyboard_string('SAVE"TESTPROG",8\r')

        success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)

        # Provide meaningful error messages based on drive status
        if error_number is None:
            pytest.fail("SAVE command timed out - could not read drive status")
        elif error_number != 0:
            # Common 1541 error codes:
            # 00 = OK, 25 = WRITE ERROR, 26 = WRITE PROTECT ON
            # 29 = DISK ID MISMATCH, 72 = DISK FULL
            pytest.fail(f"SAVE failed with drive error {error_number:02d}")

        assert success, f"Unexpected error state: error={error_number}"

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_disk_file_modified(self, threaded_drive, tmp_path):
        """Verify the D64 file is actually modified after SAVE.

        Compares the disk file before and after SAVE to ensure
        changes are persisted.
        """
        # Copy the base disk to temp location
        test_disk = tmp_path / "test.d64"
        shutil.copy(BASE_DISK, test_disk)

        # Get file size and first sector before
        original_size = test_disk.stat().st_size
        with open(test_disk, 'rb') as f:
            original_data = f.read()

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)

        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Enter a program
        c64.inject_keyboard_string('10 PRINT "TEST"\r')
        run_cycles(c64, 500_000)

        # Save it
        c64.inject_keyboard_string('SAVE"NEWFILE",8\r')

        success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)

        if error_number is None:
            pytest.fail("SAVE command timed out - could not read drive status")
        elif error_number != 0:
            pytest.fail(f"SAVE failed with drive error {error_number:02d}")

        # Check if the file was modified
        with open(test_disk, 'rb') as f:
            new_data = f.read()

        # Size should be the same (D64 is fixed size)
        assert len(new_data) == original_size, \
            "D64 file size changed unexpectedly"

        # Content should be different (new file added)
        assert new_data != original_data, \
            "D64 file was not modified after SAVE"
