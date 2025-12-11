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


def get_loaded_program_size(c64) -> int:
    """Get the size of the loaded BASIC program in bytes."""
    basic_start = (c64.memory.read(BASIC_TXTTAB_LO) |
                   (c64.memory.read(BASIC_TXTTAB_HI) << 8))
    basic_end = (c64.memory.read(BASIC_VARTAB_LO) |
                 (c64.memory.read(BASIC_VARTAB_HI) << 8))
    return basic_end - basic_start


def create_basic_program_of_size(target_bytes: int) -> str:
    """Generate BASIC code that creates a program of approximately the target size.

    Each BASIC line takes approximately:
    - 4 bytes overhead (next line ptr + line number)
    - Plus the tokenized statement length

    A line like '10 REM AAAA...' takes: 4 + 1 (REM token) + padding = ~5 + padding bytes

    Returns BASIC commands to type that will create a program of the target size.
    """
    if target_bytes <= 0:
        return ""

    # BASIC program structure:
    # Each line: 2 bytes next ptr, 2 bytes line num, tokenized code, 0 terminator
    # Program ends with 0x00 0x00 (null next ptr)
    # So minimum program with one line: ~8 bytes

    # For simple sizing, we'll use lines of REM statements
    # REM token is $8F, followed by text
    # Line overhead: 5 bytes (2 ptr + 2 linenum + 1 terminator)
    # REM adds 1 byte for token

    # For a program of N bytes, we need content of about N-2 bytes (for final 00 00)
    content_needed = target_bytes - 2

    if content_needed <= 0:
        return ""

    commands = []
    line_num = 10
    bytes_added = 0

    while bytes_added < content_needed:
        # Each line: 5 overhead + 1 REM token + padding text
        # Keep lines under ~80 chars for keyboard buffer
        remaining = content_needed - bytes_added
        # Line overhead is ~6 bytes, so text length determines size
        text_len = min(remaining - 6, 60)  # Max 60 chars of text per line
        if text_len < 1:
            text_len = 1

        # Use 'A' repeated for padding text
        padding = 'A' * text_len
        commands.append(f'{line_num} REM {padding}\r')

        # Estimate bytes: 5 overhead + 1 REM + space + text_len
        bytes_added += 6 + text_len + 1
        line_num += 10

    return commands


@requires_fixtures
class TestSaveSizeBoundaries:
    """Test SAVE with files of specific sizes to test sector boundaries.

    Each sector holds 254 bytes of file data (256 - 2 byte track/sector link).
    File includes 2-byte load address, so:
    - 252 content bytes + 2 load addr = 254 total = 1 sector
    - 253 content bytes + 2 load addr = 255 total = 2 sectors
    """

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_save_minimal_program(self, threaded_drive, tmp_path):
        """Save a minimal BASIC program (just one short line).

        Tests that very small files save correctly.
        """
        test_disk = tmp_path / "test.d64"
        shutil.copy(BASE_DISK, test_disk)

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)
        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Enter minimal program: just '10 ?' which prints a blank line
        c64.inject_keyboard_string('10 ?\r')
        run_cycles(c64, 500_000)

        c64.inject_keyboard_string('SAVE"MINIMAL",8\r')
        success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)

        if error_number is None:
            pytest.fail("SAVE command timed out")
        elif error_number != 0:
            pytest.fail(f"SAVE failed with drive error {error_number:02d}")

        assert success

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_save_one_sector_program(self, threaded_drive, tmp_path):
        """Save a program that fits in exactly one sector (~254 bytes).

        Tests the boundary case where file fits in one sector with no overflow.
        """
        test_disk = tmp_path / "test.d64"
        shutil.copy(BASE_DISK, test_disk)

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)
        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Create a program that's about 240 bytes (well within one sector)
        # 3 lines of ~80 bytes each
        for i in range(3):
            line_num = 10 + i * 10
            padding = 'A' * 65
            c64.inject_keyboard_string(f'{line_num} REM {padding}\r')
            run_cycles(c64, 500_000)

        c64.inject_keyboard_string('SAVE"ONESECTOR",8\r')
        success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)

        if error_number is None:
            pytest.fail("SAVE command timed out")
        elif error_number != 0:
            pytest.fail(f"SAVE failed with drive error {error_number:02d}")

        assert success

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_save_two_sector_program(self, threaded_drive, tmp_path):
        """Save a program that requires exactly two sectors (~300-400 bytes).

        Tests the sector boundary crossing case.
        """
        test_disk = tmp_path / "test.d64"
        shutil.copy(BASE_DISK, test_disk)

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)
        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Create a program that's about 350 bytes (needs 2 sectors)
        # 5 lines of ~70 bytes each
        for i in range(5):
            line_num = 10 + i * 10
            padding = 'A' * 60
            c64.inject_keyboard_string(f'{line_num} REM {padding}\r')
            run_cycles(c64, 500_000)

        c64.inject_keyboard_string('SAVE"TWOSECTOR",8\r')
        success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)

        if error_number is None:
            pytest.fail("SAVE command timed out")
        elif error_number != 0:
            pytest.fail(f"SAVE failed with drive error {error_number:02d}")

        assert success

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_save_multi_sector_program(self, threaded_drive, tmp_path):
        """Save a program spanning multiple sectors (~1KB, needs 4+ sectors).

        Tests handling of multiple sector writes.
        """
        test_disk = tmp_path / "test.d64"
        shutil.copy(BASE_DISK, test_disk)

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)
        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Create a program that's about 1000 bytes (needs ~4 sectors)
        # 14 lines of ~70 bytes each
        for i in range(14):
            line_num = 10 + i * 10
            padding = 'A' * 60
            c64.inject_keyboard_string(f'{line_num} REM {padding}\r')
            run_cycles(c64, 500_000)

        c64.inject_keyboard_string('SAVE"MULTISEC",8\r')
        success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)

        if error_number is None:
            pytest.fail("SAVE command timed out")
        elif error_number != 0:
            pytest.fail(f"SAVE failed with drive error {error_number:02d}")

        assert success


@requires_fixtures
class TestSaveLoadRoundtrip:
    """Test that saved files can be loaded back correctly.

    This is the strongest verification that SAVE works - the data
    survives a roundtrip through save and load operations.
    """

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_save_load_roundtrip_small(self, threaded_drive, tmp_path):
        """Save a program, NEW, load it back, verify it's correct.

        Uses a small program with known content.
        """
        test_disk = tmp_path / "test.d64"
        shutil.copy(BASE_DISK, test_disk)

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)
        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Enter a specific program we can verify
        c64.inject_keyboard_string('10 PRINT "HELLO"\r')
        run_cycles(c64, 500_000)
        c64.inject_keyboard_string('20 PRINT "WORLD"\r')
        run_cycles(c64, 500_000)

        # Record the program size before saving
        original_size = get_loaded_program_size(c64)

        # Save the program
        c64.inject_keyboard_string('SAVE"ROUNDTRIP",8\r')
        success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)

        if error_number is None:
            pytest.fail("SAVE command timed out")
        elif error_number != 0:
            pytest.fail(f"SAVE failed with drive error {error_number:02d}")

        # Clear the program with NEW
        c64.inject_keyboard_string('NEW\r')
        run_cycles(c64, 500_000)

        # Verify program is gone
        size_after_new = get_loaded_program_size(c64)
        assert size_after_new < original_size, "NEW didn't clear program"

        # Load it back
        c64.inject_keyboard_string('LOAD"ROUNDTRIP",8\r')
        assert wait_for_load(c64), "LOAD timed out"

        # Verify program size matches
        loaded_size = get_loaded_program_size(c64)
        assert loaded_size == original_size, \
            f"Loaded size {loaded_size} != original size {original_size}"

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_save_load_roundtrip_larger(self, threaded_drive, tmp_path):
        """Save and load a larger program spanning multiple sectors.

        Tests data integrity across sector boundaries.

        Uses a fresh blank disk to avoid filename conflicts with
        existing files on BASE_DISK.
        """
        # Create a fresh blank disk to avoid filename conflicts
        d64 = D64Image(None)
        test_disk = tmp_path / "roundtrip.d64"
        d64.save(test_disk)

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)
        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Create a larger program (~800 bytes, ~3 sectors)
        for i in range(10):
            line_num = 10 + i * 10
            padding = 'X' * 60
            c64.inject_keyboard_string(f'{line_num} REM {padding}\r')
            run_cycles(c64, 500_000)

        # Record program size and first bytes of memory
        original_size = get_loaded_program_size(c64)

        # Read first 32 bytes of program for verification
        basic_start = 0x0801
        original_bytes = [c64.memory.read(basic_start + i) for i in range(32)]

        # Save
        c64.inject_keyboard_string('SAVE"BIGPROG",8\r')
        success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)

        if error_number is None:
            pytest.fail("SAVE command timed out")
        elif error_number != 0:
            pytest.fail(f"SAVE failed with drive error {error_number:02d}")

        # Clear with NEW
        c64.inject_keyboard_string('NEW\r')
        run_cycles(c64, 500_000)

        # Load back
        c64.inject_keyboard_string('LOAD"BIGPROG",8\r')
        assert wait_for_load(c64), "LOAD timed out"

        # Verify size
        loaded_size = get_loaded_program_size(c64)
        assert loaded_size == original_size, \
            f"Loaded size {loaded_size} != original size {original_size}"

        # Verify first 32 bytes match
        loaded_bytes = [c64.memory.read(basic_start + i) for i in range(32)]
        assert loaded_bytes == original_bytes, \
            "Program content doesn't match after roundtrip"


@requires_fixtures
class TestSaveOverwrite:
    """Test overwriting existing files with SAVE."""

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_save_replace_existing(self, threaded_drive, tmp_path):
        """Save a file, then save a different file with same name using @:.

        The @: prefix tells the drive to replace an existing file.
        """
        test_disk = tmp_path / "test.d64"
        shutil.copy(BASE_DISK, test_disk)

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)
        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Save first version
        c64.inject_keyboard_string('10 PRINT "V1"\r')
        run_cycles(c64, 500_000)

        c64.inject_keyboard_string('SAVE"REPLACE",8\r')
        success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)
        assert error_number == 0, f"First SAVE failed: error {error_number}"

        # Clear and create second version
        c64.inject_keyboard_string('NEW\r')
        run_cycles(c64, 500_000)

        c64.inject_keyboard_string('10 PRINT "V2"\r')
        run_cycles(c64, 500_000)
        c64.inject_keyboard_string('20 PRINT "NEW"\r')
        run_cycles(c64, 500_000)

        second_version_size = get_loaded_program_size(c64)

        # Save with replace prefix @:
        c64.inject_keyboard_string('SAVE"@:REPLACE",8\r')
        success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)

        if error_number is None:
            pytest.fail("SAVE @: timed out")
        elif error_number != 0:
            pytest.fail(f"SAVE @: failed with error {error_number:02d}")

        # Clear and load to verify we get version 2
        c64.inject_keyboard_string('NEW\r')
        run_cycles(c64, 500_000)

        c64.inject_keyboard_string('LOAD"REPLACE",8\r')
        assert wait_for_load(c64), "LOAD timed out"

        loaded_size = get_loaded_program_size(c64)
        assert loaded_size == second_version_size, \
            "Loaded file doesn't match replaced version"


# Import D64Image for creating blank disks
from systems.c64.drive.d64 import D64Image


def create_program_lines(identifier: str, target_sectors: int) -> list:
    """Create BASIC program lines that will produce a program of approximately target_sectors.

    Each sector holds 254 bytes.
    Each line: ~5 byte overhead + 1 REM token + 1 space + padding

    Args:
        identifier: Unique string to identify this program
        target_sectors: Target number of sectors (254 bytes each)

    Returns:
        List of BASIC line strings to type (without \\r)
    """
    target_bytes = target_sectors * 254 - 2  # -2 for load address
    lines = []
    line_num = 10
    bytes_so_far = 0

    # First line identifies the file
    first_line = f'{line_num} REM FILE{identifier}'
    lines.append(first_line)
    bytes_so_far += 7 + len(f'FILE{identifier}')  # overhead + REM + space + text
    line_num += 10

    # Fill remaining space with padding lines
    while bytes_so_far < target_bytes:
        remaining = target_bytes - bytes_so_far
        # Line overhead ~7 bytes (2 ptr + 2 linenum + 1 REM + 1 space + 1 terminator)
        padding_len = min(remaining - 7, 55)  # Keep lines manageable
        if padding_len < 1:
            break

        padding = 'P' * padding_len
        line = f'{line_num} REM {padding}'
        lines.append(line)
        bytes_so_far += 7 + padding_len
        line_num += 10

        if line_num > 60000:
            break  # Safety limit

    return lines


@requires_fixtures
@pytest.mark.slow
class TestSaveFillDisk:
    """Test saving multiple files until disk is nearly full.

    A standard 35-track D64 has 664 free sectors (683 total - 19 for BAM/directory).
    We'll save multiple files of varying sizes to fill the disk, then verify
    each file survives a save/load roundtrip.

    Note: These tests are marked as slow and skipped in CI. Run with:
        pytest -m slow tests/c64/drive/test_save.py
    """

    @pytest.mark.parametrize("threaded_drive", DRIVE_MODES)
    def test_fill_disk_with_multiple_files(self, threaded_drive, tmp_path):
        """Save multiple files and verify each via roundtrip.

        Creates 4 files of various sizes to test saving multiple files
        on a single disk without excessive test duration:
        - 1 small file (1-2 sectors)
        - 2 medium files (3-5 sectors)
        - 1 larger file (8 sectors)

        Total: approximately 20 sectors

        After saving all files, verifies each one by:
        1. Loading it back
        2. Comparing size and first 32 bytes of content
        """
        # Create a fresh blank disk
        d64 = D64Image(None)  # Creates formatted blank disk
        test_disk = tmp_path / "filltest.d64"
        d64.save(test_disk)

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)
        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Define files with varying sizes (reduced for test speed)
        # Format: (filename, sector_count)
        files_to_save = [
            ('FILE01', 2),    # ~508 bytes, 2 sectors
            ('FILE02', 3),    # ~762 bytes, 3 sectors
            ('FILE03', 5),    # ~1.2KB, 5 sectors
            ('FILE04', 8),    # ~2KB, 8 sectors
        ]

        # Store metadata for verification
        saved_files = []

        for filename, sectors in files_to_save:
            # Create the program
            lines = create_program_lines(filename[-2:], sectors)

            # Enter each line
            for line in lines:
                c64.inject_keyboard_string(f'{line}\r')
                run_cycles(c64, 500_000)

            # Record program details before saving
            program_size = get_loaded_program_size(c64)
            basic_start = 0x0801
            first_32_bytes = [c64.memory.read(basic_start + i) for i in range(32)]

            saved_files.append({
                'filename': filename,
                'expected_sectors': sectors,
                'size': program_size,
                'first_bytes': first_32_bytes,
            })

            # Save the file
            c64.inject_keyboard_string(f'SAVE"{filename}",8\r')
            success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)

            if error_number is None:
                pytest.fail(f"SAVE {filename} timed out")
            elif error_number != 0:
                pytest.fail(f"SAVE {filename} failed with error {error_number:02d}")

            # Clear for next file
            c64.inject_keyboard_string('NEW\r')
            run_cycles(c64, 500_000)

        # Now verify each file by loading it back
        for file_info in saved_files:
            filename = file_info['filename']

            # Load the file
            c64.inject_keyboard_string(f'LOAD"{filename}",8\r')
            if not wait_for_load(c64):
                pytest.fail(f"LOAD {filename} timed out during verification")

            # Verify size
            loaded_size = get_loaded_program_size(c64)
            if loaded_size != file_info['size']:
                pytest.fail(
                    f"File {filename}: size mismatch. "
                    f"Expected {file_info['size']}, got {loaded_size}"
                )

            # Verify first 32 bytes
            basic_start = 0x0801
            loaded_bytes = [c64.memory.read(basic_start + i) for i in range(32)]
            if loaded_bytes != file_info['first_bytes']:
                pytest.fail(
                    f"File {filename}: content mismatch in first 32 bytes"
                )

            # Clear for next file
            c64.inject_keyboard_string('NEW\r')
            run_cycles(c64, 500_000)

        # All files verified successfully

    @pytest.mark.parametrize("threaded_drive", [
        pytest.param(False, id="synchronous-drive"),
    ])
    def test_fill_disk_larger_files(self, threaded_drive, tmp_path):
        """Test saving larger multi-sector files.

        Creates 2 larger files (15-20 sectors each) to test saving
        files that span many sectors.

        Note: Only runs synchronous mode to save test time since the
        test_fill_disk_with_multiple_files covers both modes.
        """
        # Create a fresh blank disk
        d64 = D64Image(None)
        test_disk = tmp_path / "capacity.d64"
        d64.save(test_disk)

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)
        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Save 2 larger files
        files_to_save = [
            ('BIGF01', 15),  # ~3.8KB, 15 sectors
            ('BIGF02', 20),  # ~5KB, 20 sectors
        ]
        files_saved = []

        for filename, sectors in files_to_save:
            # Create the program
            lines = create_program_lines(filename[-2:], sectors)

            for line in lines:
                c64.inject_keyboard_string(f'{line}\r')
                run_cycles(c64, 500_000)

            program_size = get_loaded_program_size(c64)
            basic_start = 0x0801
            first_bytes = [c64.memory.read(basic_start + j) for j in range(32)]

            files_saved.append({
                'filename': filename,
                'size': program_size,
                'first_bytes': first_bytes,
            })

            c64.inject_keyboard_string(f'SAVE"{filename}",8\r')
            success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES * 2)

            if error_number is None:
                pytest.fail(f"SAVE {filename} timed out")
            elif error_number != 0:
                pytest.fail(f"SAVE {filename} failed with error {error_number:02d}")

            c64.inject_keyboard_string('NEW\r')
            run_cycles(c64, 500_000)

        # Verify all successfully saved files
        for file_info in files_saved:
            filename = file_info['filename']

            c64.inject_keyboard_string(f'LOAD"{filename}",8\r')
            if not wait_for_load(c64, max_cycles=MAX_LOAD_CYCLES * 2):
                pytest.fail(f"LOAD {filename} timed out during verification")

            loaded_size = get_loaded_program_size(c64)
            assert loaded_size == file_info['size'], \
                f"File {filename}: size {loaded_size} != expected {file_info['size']}"

            basic_start = 0x0801
            loaded_bytes = [c64.memory.read(basic_start + j) for j in range(32)]
            assert loaded_bytes == file_info['first_bytes'], \
                f"File {filename}: content mismatch"

            c64.inject_keyboard_string('NEW\r')
            run_cycles(c64, 500_000)


@requires_fixtures
class TestSaveZones:
    """Test saving to different disk speed zones.

    D64 disk format uses 4 speed zones with different sector counts:
    - Zone 3: Tracks 1-17 (21 sectors/track) - fastest
    - Zone 2: Tracks 18-24 (19 sectors/track) - Track 18 is directory
    - Zone 1: Tracks 25-30 (18 sectors/track)
    - Zone 0: Tracks 31-35 (17 sectors/track) - slowest

    These tests verify save works correctly when file data is allocated
    to different zones by pre-filling zone 3 to force allocation elsewhere.
    """

    @pytest.mark.parametrize("threaded_drive", [
        pytest.param(False, id="synchronous-drive"),
    ])
    def test_save_to_zone_2(self, threaded_drive, tmp_path):
        """Test saving when allocation is forced to zone 2 (tracks 18-24).

        Pre-fills zone 3 (tracks 1-17) to force new file allocation to zone 2.
        """
        # Create a disk with zone 3 pre-filled
        d64 = D64Image(None)

        # Fill tracks 1-17 (zone 3) by marking them as allocated in BAM
        # Read the BAM sector
        bam = bytearray(d64.read_sector(18, 0))

        # BAM format: bytes 4-143 are track entries (4 bytes per track)
        # Each track entry: free count + 3 bytes bitmap
        # Mark tracks 1-17 as fully allocated
        for track in range(1, 18):
            bam_offset = 4 + (track - 1) * 4
            bam[bam_offset] = 0  # 0 free sectors
            bam[bam_offset + 1] = 0  # All sectors allocated
            bam[bam_offset + 2] = 0
            bam[bam_offset + 3] = 0

        d64.write_sector(18, 0, bytes(bam))

        test_disk = tmp_path / "zone2test.d64"
        d64.save(test_disk)

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)
        assert wait_for_ready(c64), "Failed to boot to BASIC"

        # Create a small program (3 sectors to span zone 2)
        lines = create_program_lines("Z2", 3)
        for line in lines:
            c64.inject_keyboard_string(f'{line}\r')
            run_cycles(c64, 500_000)

        original_size = get_loaded_program_size(c64)
        basic_start = 0x0801
        original_bytes = [c64.memory.read(basic_start + i) for i in range(32)]

        # Save the file
        c64.inject_keyboard_string('SAVE"ZONE2FILE",8\r')
        success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)

        if error_number is None:
            pytest.fail("SAVE timed out")
        elif error_number != 0:
            pytest.fail(f"SAVE failed with error {error_number:02d}")

        # Clear and reload
        c64.inject_keyboard_string('NEW\r')
        run_cycles(c64, 500_000)

        c64.inject_keyboard_string('LOAD"ZONE2FILE",8\r')
        assert wait_for_load(c64), "LOAD timed out"

        # Verify
        loaded_size = get_loaded_program_size(c64)
        assert loaded_size == original_size, \
            f"Zone 2 save: size {loaded_size} != expected {original_size}"

        loaded_bytes = [c64.memory.read(basic_start + i) for i in range(32)]
        assert loaded_bytes == original_bytes, "Zone 2 save: content mismatch"

    @pytest.mark.parametrize("threaded_drive", [
        pytest.param(False, id="synchronous-drive"),
    ])
    def test_save_to_zone_1(self, threaded_drive, tmp_path):
        """Test saving when allocation is forced to zone 1 (tracks 25-30).

        Pre-fills zones 3 and 2 to force new file allocation to zone 1.
        """
        d64 = D64Image(None)
        bam = bytearray(d64.read_sector(18, 0))

        # Mark tracks 1-24 (zones 3 and 2) as fully allocated
        for track in range(1, 25):
            if track == 18:
                continue  # Don't touch directory track
            bam_offset = 4 + (track - 1) * 4
            bam[bam_offset] = 0
            bam[bam_offset + 1] = 0
            bam[bam_offset + 2] = 0
            bam[bam_offset + 3] = 0

        d64.write_sector(18, 0, bytes(bam))

        test_disk = tmp_path / "zone1test.d64"
        d64.save(test_disk)

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)
        assert wait_for_ready(c64), "Failed to boot to BASIC"

        lines = create_program_lines("Z1", 3)
        for line in lines:
            c64.inject_keyboard_string(f'{line}\r')
            run_cycles(c64, 500_000)

        original_size = get_loaded_program_size(c64)
        basic_start = 0x0801
        original_bytes = [c64.memory.read(basic_start + i) for i in range(32)]

        c64.inject_keyboard_string('SAVE"ZONE1FILE",8\r')
        success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)

        if error_number is None:
            pytest.fail("SAVE timed out")
        elif error_number != 0:
            pytest.fail(f"SAVE failed with error {error_number:02d}")

        c64.inject_keyboard_string('NEW\r')
        run_cycles(c64, 500_000)

        c64.inject_keyboard_string('LOAD"ZONE1FILE",8\r')
        assert wait_for_load(c64), "LOAD timed out"

        loaded_size = get_loaded_program_size(c64)
        assert loaded_size == original_size, \
            f"Zone 1 save: size {loaded_size} != expected {original_size}"

        loaded_bytes = [c64.memory.read(basic_start + i) for i in range(32)]
        assert loaded_bytes == original_bytes, "Zone 1 save: content mismatch"

    @pytest.mark.parametrize("threaded_drive", [
        pytest.param(False, id="synchronous-drive"),
    ])
    def test_save_to_zone_0(self, threaded_drive, tmp_path):
        """Test saving when allocation is forced to zone 0 (tracks 31-35).

        Pre-fills zones 3, 2, and 1 to force new file allocation to zone 0.
        This is the slowest zone with 17 sectors per track.
        """
        d64 = D64Image(None)
        bam = bytearray(d64.read_sector(18, 0))

        # Mark tracks 1-30 (zones 3, 2, and 1) as fully allocated
        for track in range(1, 31):
            if track == 18:
                continue  # Don't touch directory track
            bam_offset = 4 + (track - 1) * 4
            bam[bam_offset] = 0
            bam[bam_offset + 1] = 0
            bam[bam_offset + 2] = 0
            bam[bam_offset + 3] = 0

        d64.write_sector(18, 0, bytes(bam))

        test_disk = tmp_path / "zone0test.d64"
        d64.save(test_disk)

        c64 = create_c64_with_disk(test_disk, threaded_drive=threaded_drive)
        assert wait_for_ready(c64), "Failed to boot to BASIC"

        lines = create_program_lines("Z0", 3)
        for line in lines:
            c64.inject_keyboard_string(f'{line}\r')
            run_cycles(c64, 500_000)

        original_size = get_loaded_program_size(c64)
        basic_start = 0x0801
        original_bytes = [c64.memory.read(basic_start + i) for i in range(32)]

        c64.inject_keyboard_string('SAVE"ZONE0FILE",8\r')
        success, error_number = wait_for_operation(c64, MAX_SAVE_CYCLES)

        if error_number is None:
            pytest.fail("SAVE timed out")
        elif error_number != 0:
            pytest.fail(f"SAVE failed with error {error_number:02d}")

        c64.inject_keyboard_string('NEW\r')
        run_cycles(c64, 500_000)

        c64.inject_keyboard_string('LOAD"ZONE0FILE",8\r')
        assert wait_for_load(c64), "LOAD timed out"

        loaded_size = get_loaded_program_size(c64)
        assert loaded_size == original_size, \
            f"Zone 0 save: size {loaded_size} != expected {original_size}"

        loaded_bytes = [c64.memory.read(basic_start + i) for i in range(32)]
        assert loaded_bytes == original_bytes, "Zone 0 save: content mismatch"
