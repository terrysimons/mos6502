#!/usr/bin/env python3
"""Create test cartridges that display messages on screen.

Usage:
    python scripts/create_test_carts.py

Creates:
    tests/fixtures/c64/cartridge_types/  - All test cartridges (CRT and BIN formats)
    systems/c64/cartridges/error_cartridges/ - Pre-generated error display cartridges (if enabled)
"""

# Configuration flags
# Error cartridges are now generated dynamically at runtime, so pre-built files
# are no longer needed. Set to True only if you need to regenerate them for testing.
GENERATE_ERROR_CARTS = True
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "systems"))

from c64 import C64
from c64.memory import KERNAL_ROM_START
from c64.cartridges import (
    CartridgeTestResults,
    create_error_cartridge_rom,
    generate_mapper_tests,
    MAPPER_REQUIREMENTS,
    CARTRIDGE_TYPES,
)

# Import 6502 instruction opcodes from the existing module
from mos6502.instructions import (
    # Load
    LDA_IMMEDIATE_0xA9,
    LDA_ZEROPAGE_0xA5,
    LDA_ABSOLUTE_0xAD,
    LDX_IMMEDIATE_0xA2,
    LDY_IMMEDIATE_0xA0,
    # Store
    STA_ZEROPAGE_0x85,
    STA_ABSOLUTE_0x8D,
    STA_ABSOLUTE_X_0x9D,
    STX_ABSOLUTE_0x8E,
    STY_ABSOLUTE_0x8C,
    # Arithmetic
    INC_ZEROPAGE_0xE6,
    INX_IMPLIED_0xE8,
    INY_IMPLIED_0xC8,
    DEX_IMPLIED_0xCA,
    DEY_IMPLIED_0x88,
    # Compare
    CMP_IMMEDIATE_0xC9,
    CPX_IMMEDIATE_0xE0,
    CPY_IMMEDIATE_0xC0,
    # Branch
    BNE_RELATIVE_0xD0,
    BEQ_RELATIVE_0xF0,
    BCC_RELATIVE_0x90,
    BCS_RELATIVE_0xB0,
    # Jump/Subroutines
    JMP_ABSOLUTE_0x4C,
    JSR_ABSOLUTE_0x20,
    RTS_IMPLIED_0x60,
    RTI_IMPLIED_0x40,
    # Stack
    TXS_IMPLIED_0x9A,
    PHA_IMPLIED_0x48,
    PLA_IMPLIED_0x68,
    # Flags
    SEI_IMPLIED_0x78,
    CLI_IMPLIED_0x58,
    CLC_IMPLIED_0x18,
    SEC_IMPLIED_0x38,
    # Logic
    ORA_IMMEDIATE_0x09,
)


# C64 color constants
COLOR_BLACK = 0x00
COLOR_WHITE = 0x01
COLOR_RED = 0x02
COLOR_CYAN = 0x03
COLOR_PURPLE = 0x04
COLOR_GREEN = 0x05
COLOR_BLUE = 0x06
COLOR_YELLOW = 0x07
COLOR_ORANGE = 0x08
COLOR_BROWN = 0x09
COLOR_LIGHT_RED = 0x0A
COLOR_DARK_GRAY = 0x0B
COLOR_MEDIUM_GRAY = 0x0C
COLOR_LIGHT_GREEN = 0x0D
COLOR_LIGHT_BLUE = 0x0E
COLOR_LIGHT_GRAY = 0x0F

# Colors used for test display
COLOR_PASS = COLOR_GREEN
COLOR_FAIL = COLOR_LIGHT_RED  # Light red so it's visible on red background
COLOR_TITLE = COLOR_WHITE
COLOR_INFO = COLOR_YELLOW
COLOR_TEST_NAME = COLOR_LIGHT_GRAY
COLOR_ERROR_BORDER = COLOR_RED

# Zero-page location for fail counter
# Bits 0-6: failure count (0-127)
# Bit 7: tests complete flag
# Values: 0x00-0x7F = running, 0x80 = done/pass, 0x81-0xFF = done/fail
FAIL_COUNTER_ZP = 0x02


def emit_init_fail_counter() -> list[int]:
    """Emit code to initialize fail counter to zero."""
    return [
        LDA_IMMEDIATE_0xA9, 0x00,
        STA_ZEROPAGE_0x85, FAIL_COUNTER_ZP,
    ]


def emit_inc_fail_counter() -> list[int]:
    """Emit code to increment the fail counter."""
    return [INC_ZEROPAGE_0xE6, FAIL_COUNTER_ZP]


def emit_load_fail_counter() -> list[int]:
    """Emit code to load fail counter into A."""
    return [LDA_ZEROPAGE_0xA5, FAIL_COUNTER_ZP]


def emit_mark_tests_complete() -> list[int]:
    """Emit code to set bit 7 of fail counter, indicating tests are complete.

    Result values:
    - 0x80 = tests done, 0 failures (success)
    - 0x81-0xFF = tests done, 1-127 failures
    """
    return [
        LDA_ZEROPAGE_0xA5, FAIL_COUNTER_ZP,  # Load fail counter
        ORA_IMMEDIATE_0x09, 0x80,             # Set bit 7 (tests complete)
        STA_ZEROPAGE_0x85, FAIL_COUNTER_ZP,   # Store back
    ]


def text_to_screen_codes(text: str) -> list[int]:
    """Convert ASCII text to C64 screen codes."""
    screen_codes = []
    for ch in text:
        if 'A' <= ch <= 'Z':
            screen_codes.append(ord(ch) - ord('A') + 1)
        elif 'a' <= ch <= 'z':
            screen_codes.append(ord(ch) - ord('a') + 1)
        elif '0' <= ch <= '9':
            screen_codes.append(ord(ch) - ord('0') + 0x30)
        elif ch == ' ':
            screen_codes.append(0x20)
        elif ch == '!':
            screen_codes.append(0x21)
        elif ch == '.':
            screen_codes.append(0x2E)
        elif ch == ',':
            screen_codes.append(0x2C)
        elif ch == ':':
            screen_codes.append(0x3A)
        elif ch == '-':
            screen_codes.append(0x2D)
        elif ch == '+':
            screen_codes.append(0x2B)
        elif ch == '=':
            screen_codes.append(0x3D)
        elif ch == '$':
            screen_codes.append(0x24)
        else:
            screen_codes.append(0x20)  # space for unknown
    return screen_codes


def create_display_code(message: str, line: int = 0, color: int = 0x01) -> list[int]:
    """Create code to display a message on a specific screen line.

    Args:
        message: Text to display (max 40 chars)
        line: Screen line (0-24)
        color: Color value (0-15)

    Returns:
        List of machine code bytes
    """
    code = []
    screen_codes = text_to_screen_codes(message)
    start_pos = (40 - len(message)) // 2
    screen_addr = 0x0400 + (line * 40) + start_pos
    color_addr = 0xD800 + (line * 40) + start_pos

    # Write each character and its color
    for i, sc in enumerate(screen_codes):
        # Write character to screen RAM
        code.extend([
            LDA_IMMEDIATE_0xA9, sc,
            STA_ABSOLUTE_0x8D, (screen_addr + i) & 0xFF, (screen_addr + i) >> 8,
        ])
        # Write color to color RAM
        code.extend([
            LDA_IMMEDIATE_0xA9, color,
            STA_ABSOLUTE_0x8D, (color_addr + i) & 0xFF, (color_addr + i) >> 8,
        ])

    return code


def create_8k_cartridge() -> tuple[bytes, str]:
    """Create an 8KB test cartridge.

    Returns:
        Tuple of (cartridge bytes, description)
    """
    cart = bytearray(C64.ROML_SIZE)

    # Cartridge header at $8000-$8008
    cart[0x0000] = 0x09  # Cold start lo -> $8009
    cart[0x0001] = 0x80  # Cold start hi
    cart[0x0002] = 0x09  # Warm start lo -> $8009
    cart[0x0003] = 0x80  # Warm start hi
    cart[0x0004] = 0xC3  # 'C' (CBM80 signature)
    cart[0x0005] = 0xC2  # 'B'
    cart[0x0006] = 0xCD  # 'M'
    cart[0x0007] = 0x38  # '8'
    cart[0x0008] = 0x30  # '0'

    # Code starts at $8009
    code_offset = 0x0009
    code = []

    # Initialize - disable interrupts, set up stack
    code.extend([
        SEI_IMPLIED_0x78,
        LDX_IMMEDIATE_0xA2, 0xFF,
        TXS_IMPLIED_0x9A,
    ])

    # Clear screen by filling $0400-$07E7 with spaces (0x20)
    code.extend([
        LDA_IMMEDIATE_0xA9, 0x20,  # space character
        LDX_IMMEDIATE_0xA2, 0x00,
    ])
    # clear_loop:
    code.extend([
        STA_ABSOLUTE_X_0x9D, 0x00, 0x04,  # STA $0400,X
        STA_ABSOLUTE_X_0x9D, 0x00, 0x05,  # STA $0500,X
        STA_ABSOLUTE_X_0x9D, 0x00, 0x06,  # STA $0600,X
        STA_ABSOLUTE_X_0x9D, 0x00, 0x07,  # STA $0700,X
        INX_IMPLIED_0xE8,
        BNE_RELATIVE_0xD0, 0xF1,  # branch back -15 bytes
    ])

    # Set border and background to blue
    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_BLUE,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # $D020 border color
        STA_ABSOLUTE_0x8D, 0x21, 0xD0,  # $D021 background color
    ])

    # Display messages
    code.extend(create_display_code("8K CARTRIDGE TEST", line=0, color=COLOR_WHITE))
    code.extend(create_display_code("ROML AT $8000-$9FFF", line=2, color=COLOR_YELLOW))
    code.extend(create_display_code("EXROM=0 GAME=1", line=4, color=COLOR_GREEN))

    # Infinite loop
    loop_addr = C64.ROML_START + code_offset + len(code)
    code.extend([
        JMP_ABSOLUTE_0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,
    ])

    # Copy code into cartridge
    for i, byte in enumerate(code):
        cart[code_offset + i] = byte

    return bytes(cart), f"Code size: {len(code)} bytes starting at $8009"


def create_16k_cartridge() -> tuple[bytes, bytes, str]:
    """Create a 16KB test cartridge with code split between ROML and ROMH.

    The cartridge demonstrates that both ROML ($8000) and ROMH ($A000) are
    accessible by calling a subroutine in ROMH from ROML.

    Returns:
        Tuple of (ROML bytes, ROMH bytes, description)
    """
    roml = bytearray(C64.ROML_SIZE)
    romh = bytearray(C64.ROMH_SIZE)

    # === ROML at $8000-$9FFF ===

    # Cartridge header at $8000-$8008
    roml[0x0000] = 0x09  # Cold start lo -> $8009
    roml[0x0001] = 0x80  # Cold start hi
    roml[0x0002] = 0x09  # Warm start lo -> $8009
    roml[0x0003] = 0x80  # Warm start hi
    roml[0x0004] = 0xC3  # 'C' (CBM80 signature)
    roml[0x0005] = 0xC2  # 'B'
    roml[0x0006] = 0xCD  # 'M'
    roml[0x0007] = 0x38  # '8'
    roml[0x0008] = 0x30  # '0'

    # Code starts at $8009
    code_offset = 0x0009
    code = []

    # Initialize - disable interrupts, set up stack
    code.extend([
        SEI_IMPLIED_0x78,
        LDX_IMMEDIATE_0xA2, 0xFF,
        TXS_IMPLIED_0x9A,
    ])

    # Clear screen
    code.extend([
        LDA_IMMEDIATE_0xA9, 0x20,  # space character
        LDX_IMMEDIATE_0xA2, 0x00,
    ])
    code.extend([
        STA_ABSOLUTE_X_0x9D, 0x00, 0x04,  # STA $0400,X
        STA_ABSOLUTE_X_0x9D, 0x00, 0x05,  # STA $0500,X
        STA_ABSOLUTE_X_0x9D, 0x00, 0x06,  # STA $0600,X
        STA_ABSOLUTE_X_0x9D, 0x00, 0x07,  # STA $0700,X
        INX_IMPLIED_0xE8,
        BNE_RELATIVE_0xD0, 0xF1,  # branch back -15 bytes
    ])

    # Set border and background to dark gray
    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_DARK_GRAY,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # $D020 border color
        STA_ABSOLUTE_0x8D, 0x21, 0xD0,  # $D021 background color
    ])

    # Display ROML messages
    code.extend(create_display_code("16K CARTRIDGE TEST", line=0, color=COLOR_WHITE))
    code.extend(create_display_code("CODE IN ROML $8000", line=2, color=COLOR_YELLOW))

    # Call subroutine in ROMH to prove it's accessible
    code.extend([
        JSR_ABSOLUTE_0x20, 0x00, 0xA0,  # JSR $A000 (subroutine in ROMH)
    ])

    # Display success message (we returned from ROMH!)
    code.extend(create_display_code("RETURNED FROM ROMH!", line=6, color=COLOR_GREEN))
    code.extend(create_display_code("EXROM=0 GAME=0", line=8, color=COLOR_CYAN))

    # Infinite loop
    loop_addr = C64.ROML_START + code_offset + len(code)
    code.extend([
        JMP_ABSOLUTE_0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,
    ])

    # Copy code into ROML
    for i, byte in enumerate(code):
        roml[code_offset + i] = byte

    # === ROMH at $A000-$BFFF ===

    # Subroutine at $A000 that displays a message and returns
    romh_code = []

    # Display message from ROMH
    romh_code.extend(create_display_code("HELLO FROM ROMH $A000", line=4, color=COLOR_LIGHT_BLUE))

    # Return to caller
    romh_code.extend([
        RTS_IMPLIED_0x60,
    ])

    # Copy code into ROMH
    for i, byte in enumerate(romh_code):
        romh[i] = byte

    desc = f"ROML code: {len(code)} bytes, ROMH code: {len(romh_code)} bytes"
    return bytes(roml), bytes(romh), desc


def write_raw_cartridge(path: Path, roml: bytes, romh: bytes | None = None) -> None:
    """Write a raw binary cartridge file."""
    with open(path, 'wb') as f:
        f.write(roml)
        if romh is not None:
            f.write(romh)


class MapperTestBuilder:
    """Builder for mapper verification test code.

    Generates 6502 machine code that tests mapper hardware and displays
    PASS/FAIL for each test. Used by both verification and error cartridges.
    """

    def __init__(self, hw_type: int, type_name: str):
        self.hw_type = hw_type
        self.type_name = type_name
        self.code = []
        self.code_offset = 0x0009  # Code starts after CBM80 header
        self.current_line = 0
        self.test_count = 0
        self.branches_to_fix = []  # (code_index, target_label)
        self.jumps_to_fix = []     # (code_index, target_label)
        self.labels = {}           # label_name -> address

    def _addr(self, code_index: int) -> int:
        """Convert code index to absolute address."""
        return C64.ROML_START + self.code_offset + code_index

    def _current_addr(self) -> int:
        """Get current code address."""
        return self._addr(len(self.code))

    def label(self, name: str) -> None:
        """Define a label at current position."""
        self.labels[name] = self._current_addr()

    def emit_init(self) -> None:
        """Emit initialization code: SEI, set stack, clear screen."""
        # Disable interrupts, set up stack
        self.code.extend([
            SEI_IMPLIED_0x78,
            LDX_IMMEDIATE_0xA2, 0xFF,
            TXS_IMPLIED_0x9A,
        ])

        # Clear screen
        self.code.extend([
            LDA_IMMEDIATE_0xA9, 0x20,  # space character
            LDX_IMMEDIATE_0xA2, 0x00,
        ])
        self.code.extend([
            STA_ABSOLUTE_X_0x9D, 0x00, 0x04,  # STA $0400,X
            STA_ABSOLUTE_X_0x9D, 0x00, 0x05,  # STA $0500,X
            STA_ABSOLUTE_X_0x9D, 0x00, 0x06,  # STA $0600,X
            STA_ABSOLUTE_X_0x9D, 0x00, 0x07,  # STA $0700,X
            INX_IMPLIED_0xE8,
            BNE_RELATIVE_0xD0, 0xF1,  # branch back -15 bytes
        ])

        # Initialize fail counter
        self.code.extend(emit_init_fail_counter())

    def emit_set_border(self, color: int) -> None:
        """Set border color only (keeps background for text visibility)."""
        self.code.extend([
            LDA_IMMEDIATE_0xA9, color,
            STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # $D020 border only
        ])

    def emit_set_border_and_background(self, color: int) -> None:
        """Set both border and background color."""
        self.code.extend([
            LDA_IMMEDIATE_0xA9, color,
            STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # $D020 border
            STA_ABSOLUTE_0x8D, 0x21, 0xD0,  # $D021 background
        ])

    def emit_title(self, title: str, line: int = 0) -> None:
        """Display title text."""
        self.code.extend(create_display_code(title, line=line, color=COLOR_WHITE))
        self.current_line = line + 1

    def emit_type_info(self) -> None:
        """Display TYPE: n and NAME: info."""
        self.code.extend(create_display_code(f"TYPE: {self.hw_type}", line=self.current_line, color=COLOR_YELLOW))
        self.current_line += 1
        # Truncate name to fit screen
        name = self.type_name.upper()[:32]
        self.code.extend(create_display_code(f"NAME: {name}", line=self.current_line, color=COLOR_YELLOW))
        self.current_line += 2  # Skip a line

    def emit_test_start(self, test_name: str) -> str:
        """Start a test - displays test name, returns test ID for pass/fail."""
        self.test_count += 1
        test_id = f"test_{self.test_count}"

        # Display test name (leave room for PASS/FAIL at end)
        display_name = test_name[:30]  # Leave room for " PASS" or " FAIL"
        self.code.extend(create_display_code(display_name, line=self.current_line, color=COLOR_LIGHT_GRAY))

        return test_id

    def emit_check_byte(self, addr: int, expected: int, fail_label: str) -> None:
        """Emit code to check a byte at addr equals expected, branch to fail_label if not."""
        self.code.extend([
            LDA_ABSOLUTE_0xAD, addr & 0xFF, (addr >> 8) & 0xFF,
            CMP_IMMEDIATE_0xC9, expected,
            BNE_RELATIVE_0xD0,
        ])
        self.branches_to_fix.append((len(self.code), fail_label))
        self.code.append(0x00)  # Placeholder

    def emit_write_byte(self, addr: int, value: int) -> None:
        """Emit code to write a byte."""
        self.code.extend([
            LDA_IMMEDIATE_0xA9, value,
            STA_ABSOLUTE_0x8D, addr & 0xFF, (addr >> 8) & 0xFF,
        ])

    def emit_test_pass(self, test_id: str) -> None:
        """Emit PASS result for current test and jump to next."""
        # Display "PASS" in green at position 35 on current line
        pass_pos = 35
        screen_addr = 0x0400 + (self.current_line * 40) + pass_pos
        color_addr = 0xD800 + (self.current_line * 40) + pass_pos

        # Write "PASS"
        for i, ch in enumerate([0x10, 0x01, 0x13, 0x13]):  # P A S S in screen codes
            self.code.extend([
                LDA_IMMEDIATE_0xA9, ch,
                STA_ABSOLUTE_0x8D, (screen_addr + i) & 0xFF, (screen_addr + i) >> 8,
                LDA_IMMEDIATE_0xA9, COLOR_PASS,
                STA_ABSOLUTE_0x8D, (color_addr + i) & 0xFF, (color_addr + i) >> 8,
            ])

        # Jump to next test
        self.code.append(JMP_ABSOLUTE_0x4C)
        self.jumps_to_fix.append((len(self.code), f"{test_id}_done"))
        self.code.extend([0x00, 0x00])

    def emit_test_fail(self, test_id: str) -> None:
        """Emit FAIL result for current test."""
        self.label(f"{test_id}_fail")

        # Increment fail counter
        self.code.extend(emit_inc_fail_counter())

        # Display "FAIL" in light red at position 35 on current line
        fail_pos = 35
        screen_addr = 0x0400 + (self.current_line * 40) + fail_pos
        color_addr = 0xD800 + (self.current_line * 40) + fail_pos

        # Write "FAIL"
        for i, ch in enumerate([0x06, 0x01, 0x09, 0x0C]):  # F A I L in screen codes
            self.code.extend([
                LDA_IMMEDIATE_0xA9, ch,
                STA_ABSOLUTE_0x8D, (screen_addr + i) & 0xFF, (screen_addr + i) >> 8,
                LDA_IMMEDIATE_0xA9, COLOR_FAIL,
                STA_ABSOLUTE_0x8D, (color_addr + i) & 0xFF, (color_addr + i) >> 8,
            ])

        self.label(f"{test_id}_done")
        self.current_line += 1

    def emit_final_status(self) -> None:
        """Emit code to check fail counter and set final border color.

        Sets bit 7 of fail counter ($02) to indicate tests are complete:
        - 0x80 = tests done, 0 failures (success)
        - 0x81-0xFF = tests done, 1-127 failures
        """
        self.current_line += 1  # Skip a line

        # Check fail counter - use BEQ to short jump, JMP for far jump
        self.code.extend(emit_load_fail_counter())
        self.code.extend([
            BEQ_RELATIVE_0xF0, 0x03,  # BEQ +3 (skip the JMP if zero/pass)
            JMP_ABSOLUTE_0x4C,
        ])
        self.jumps_to_fix.append((len(self.code), "show_fail"))
        self.code.extend([0x00, 0x00])

        # All passed - green border
        self.emit_set_border(COLOR_GREEN)
        self.code.extend(create_display_code("ALL TESTS PASSED", line=self.current_line, color=COLOR_GREEN))
        # Show cartridge type supported message
        pass_msg = f"TYPE {self.hw_type} SUPPORTED: PASS"
        self.code.extend(create_display_code(pass_msg, line=self.current_line + 1, color=COLOR_GREEN))
        self.code.append(JMP_ABSOLUTE_0x4C)
        self.jumps_to_fix.append((len(self.code), "loop"))
        self.code.extend([0x00, 0x00])

        # Some failures - red border
        self.label("show_fail")
        self.emit_set_border(COLOR_RED)
        self.code.extend(create_display_code("VERIFICATION FAILED", line=self.current_line, color=COLOR_FAIL))
        # Show cartridge type not supported message
        fail_msg = f"TYPE {self.hw_type} SUPPORTED: FAIL"
        self.code.extend(create_display_code(fail_msg, line=self.current_line + 1, color=COLOR_FAIL))

        # Mark tests complete (set bit 7, preserve failure count)
        self.label("loop")
        self.code.extend(emit_mark_tests_complete())

        # Infinite loop
        loop_addr = self._current_addr()
        self.code.extend([
            JMP_ABSOLUTE_0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,
        ])

    def fixup_branches(self) -> None:
        """Fix up all branch and jump targets."""
        for code_idx, label in self.branches_to_fix:
            target = self.labels[label]
            # Branch offset is relative to instruction after the branch
            offset = target - self._addr(code_idx + 1)
            if offset < -128 or offset > 127:
                raise ValueError(f"Branch to {label} out of range: {offset}")
            self.code[code_idx] = offset & 0xFF

        for code_idx, label in self.jumps_to_fix:
            target = self.labels[label]
            self.code[code_idx] = target & 0xFF
            self.code[code_idx + 1] = (target >> 8) & 0xFF

    def build_cartridge(self) -> bytes:
        """Build final cartridge ROM."""
        self.fixup_branches()

        cart = bytearray(C64.ROML_SIZE)

        # CBM80 header
        cart[0x0000] = 0x09  # Cold start lo
        cart[0x0001] = 0x80  # Cold start hi
        cart[0x0002] = 0x09  # Warm start lo
        cart[0x0003] = 0x80  # Warm start hi
        cart[0x0004] = 0xC3  # 'C'
        cart[0x0005] = 0xC2  # 'B'
        cart[0x0006] = 0xCD  # 'M'
        cart[0x0007] = 0x38  # '8'
        cart[0x0008] = 0x30  # '0'

        # Copy code
        for i, byte in enumerate(self.code):
            cart[self.code_offset + i] = byte

        return bytes(cart)


def create_type0_8k_test_cart(is_error_cart: bool = False) -> tuple[bytes, str]:
    """Create Type 0 8KB mode test cartridge with PASS/FAIL for each test.

    8KB mode: EXROM=0, GAME=1 - ROML only at $8000-$9FFF

    Args:
        is_error_cart: If True, this is for error/regression testing

    Returns:
        Tuple of (ROML bytes, description)
    """
    builder = MapperTestBuilder(0, "8KB Mode")

    builder.emit_init()

    title = "TYPE 0 8K ERROR" if is_error_cart else "TYPE 0 8K TEST"
    builder.emit_set_border_and_background(COLOR_BLUE)
    builder.emit_title(title, line=0)
    builder.code.extend(create_display_code("EXROM=0 GAME=1", line=builder.current_line, color=COLOR_YELLOW))
    builder.current_line += 2

    # Test 1: ROML readable at $8000
    test1 = builder.emit_test_start("ROML START $8000")
    # Check CBM80 signature which we know is there
    builder.emit_check_byte(0x8004, 0xC3, f"{test1}_fail")  # 'C'
    builder.emit_check_byte(0x8005, 0xC2, f"{test1}_fail")  # 'B'
    builder.emit_test_pass(test1)
    builder.emit_test_fail(test1)

    # Test 2: ROML end at $9FFF
    test2 = builder.emit_test_start("ROML END $9FFF")
    builder.emit_check_byte(0x9FF0, 0x52, f"{test2}_fail")  # 'R' from "ROML-OK!"
    builder.emit_check_byte(0x9FF1, 0x4F, f"{test2}_fail")  # 'O'
    builder.emit_test_pass(test2)
    builder.emit_test_fail(test2)

    # Test 3: ROMH should NOT be visible (should read BASIC ROM or RAM)
    # In 8KB mode, $A000-$BFFF is BASIC ROM, not cartridge ROMH
    # We check that we DON'T see the ROMH signature
    test3 = builder.emit_test_start("NO ROMH AT $A000")
    # If ROMH were mapped, $BFF0 would be 'R' (0x52) - we expect it NOT to be
    # This is tricky - we need to check it's NOT equal
    # Load the byte and check it's not 'R' - if it IS 'R', that's a fail
    builder.code.extend([
        LDA_ABSOLUTE_0xAD, 0xF0, 0xBF,  # LDA $BFF0
        CMP_IMMEDIATE_0xC9, 0x52,        # CMP #$52 ('R')
        BEQ_RELATIVE_0xF0,               # BEQ -> fail (if equal, ROMH is visible = bad)
    ])
    builder.branches_to_fix.append((len(builder.code), f"{test3}_fail"))
    builder.code.append(0x00)
    builder.emit_test_pass(test3)
    builder.emit_test_fail(test3)

    builder.emit_final_status()

    roml = bytearray(builder.build_cartridge())

    # Add ROML signature at $9FF0
    roml_sig_offset = 0x1FF0
    for i, b in enumerate(b"ROML-OK!"):
        roml[roml_sig_offset + i] = b

    desc = "Type 0 8KB mode" if not is_error_cart else "Type 0 8KB error"
    return bytes(roml), desc


def create_type0_16k_test_cart(is_error_cart: bool = False) -> tuple[bytes, bytes, str]:
    """Create Type 0 16KB mode test cartridge with PASS/FAIL for each test.

    16KB mode: EXROM=0, GAME=0 - ROML at $8000-$9FFF + ROMH at $A000-$BFFF

    Args:
        is_error_cart: If True, this is for error/regression testing

    Returns:
        Tuple of (ROML bytes, ROMH bytes, description)
    """
    builder = MapperTestBuilder(0, "16KB Mode")

    # We need ROMH for 16KB mode
    romh = bytearray(C64.ROMH_SIZE)

    # Place signature in ROMH for verification
    romh_sig_offset = 0x1FF0
    for i, b in enumerate(b"ROMH-OK!"):
        romh[romh_sig_offset + i] = b

    builder.emit_init()

    title = "TYPE 0 16K ERROR" if is_error_cart else "TYPE 0 16K TEST"
    builder.emit_set_border_and_background(COLOR_DARK_GRAY)
    builder.emit_title(title, line=0)
    builder.code.extend(create_display_code("EXROM=0 GAME=0", line=builder.current_line, color=COLOR_YELLOW))
    builder.current_line += 2

    # Test 1: ROML readable at $8000
    test1 = builder.emit_test_start("ROML START $8000")
    builder.emit_check_byte(0x8004, 0xC3, f"{test1}_fail")  # 'C'
    builder.emit_check_byte(0x8005, 0xC2, f"{test1}_fail")  # 'B'
    builder.emit_test_pass(test1)
    builder.emit_test_fail(test1)

    # Test 2: ROML end at $9FFF
    test2 = builder.emit_test_start("ROML END $9FFF")
    builder.emit_check_byte(0x9FF0, 0x52, f"{test2}_fail")  # 'R' from "ROML-OK!"
    builder.emit_check_byte(0x9FF1, 0x4F, f"{test2}_fail")  # 'O'
    builder.emit_test_pass(test2)
    builder.emit_test_fail(test2)

    # Test 3: ROMH visible at $A000
    test3 = builder.emit_test_start("ROMH START $A000")
    builder.emit_check_byte(0xA000, 0x00, f"{test3}_fail")  # First byte (we'll set it)
    builder.emit_test_pass(test3)
    builder.emit_test_fail(test3)

    # Test 4: ROMH end at $BFFF
    test4 = builder.emit_test_start("ROMH END $BFFF")
    builder.emit_check_byte(0xBFF0, 0x52, f"{test4}_fail")  # 'R' from "ROMH-OK!"
    builder.emit_check_byte(0xBFF3, 0x48, f"{test4}_fail")  # 'H'
    builder.emit_test_pass(test4)
    builder.emit_test_fail(test4)

    builder.emit_final_status()

    roml = bytearray(builder.build_cartridge())

    # Add ROML signature at $9FF0
    roml_sig_offset = 0x1FF0
    for i, b in enumerate(b"ROML-OK!"):
        roml[roml_sig_offset + i] = b

    # Add marker at ROMH start for test 3
    romh[0x0000] = 0x00  # We check for this

    desc = "Type 0 16KB mode" if not is_error_cart else "Type 0 16KB error"
    return bytes(roml), bytes(romh), desc


def create_type0_ultimax_test_cart(is_error_cart: bool = False, include_roml: bool = False) -> tuple[bytes, bytes | None, str]:
    """Create Type 0 Ultimax mode test cartridge with PASS/FAIL for each test.

    Ultimax mode: EXROM=1, GAME=0 - ROMH at $E000-$FFFF (replaces KERNAL)
    Optional ROML at $8000-$9FFF

    Args:
        is_error_cart: If True, this is for error/regression testing
        include_roml: If True, include optional ROML at $8000-$9FFF

    Returns:
        Tuple of (ROMH bytes for $E000, optional ROML bytes, description)
    """
    # For Ultimax, the main ROM is at $E000-$FFFF and contains the reset vector
    ultimax_rom = bytearray(C64.ROML_SIZE)  # 8KB for $E000-$FFFF

    # Reset vector at $FFFC-$FFFD points to start of our code
    code_start = 0xE009

    # Put reset vector at the end of ROM
    ultimax_rom[0x1FFC] = code_start & 0xFF        # $FFFC
    ultimax_rom[0x1FFD] = (code_start >> 8) & 0xFF  # $FFFD

    # NMI and IRQ vectors point to RTI
    rti_addr = 0xE000 + 0x1FF0
    ultimax_rom[0x1FFA] = rti_addr & 0xFF          # NMI
    ultimax_rom[0x1FFB] = (rti_addr >> 8) & 0xFF
    ultimax_rom[0x1FFE] = rti_addr & 0xFF          # IRQ
    ultimax_rom[0x1FFF] = (rti_addr >> 8) & 0xFF
    ultimax_rom[0x1FF0] = RTI_IMPLIED_0x40

    # Build test code manually (can't use MapperTestBuilder directly since
    # it assumes code at $8000, but Ultimax has code at $E000)
    code_offset = 0x0009
    code = []

    # Initialize
    code.extend([
        SEI_IMPLIED_0x78,
        LDX_IMMEDIATE_0xA2, 0xFF,
        TXS_IMPLIED_0x9A,
    ])

    # Set up VIC for text mode (KERNAL not available)
    code.extend([
        LDA_IMMEDIATE_0xA9, 0x1B,
        STA_ABSOLUTE_0x8D, 0x11, 0xD0,  # $D011
        LDA_IMMEDIATE_0xA9, 0x08,
        STA_ABSOLUTE_0x8D, 0x16, 0xD0,  # $D016
        LDA_IMMEDIATE_0xA9, 0x14,
        STA_ABSOLUTE_0x8D, 0x18, 0xD0,  # $D018
    ])

    # Clear screen
    code.extend([
        LDA_IMMEDIATE_0xA9, 0x20,
        LDX_IMMEDIATE_0xA2, 0x00,
    ])
    code.extend([
        STA_ABSOLUTE_X_0x9D, 0x00, 0x04,
        STA_ABSOLUTE_X_0x9D, 0x00, 0x05,
        STA_ABSOLUTE_X_0x9D, 0x00, 0x06,
        STA_ABSOLUTE_X_0x9D, 0x00, 0x07,
        INX_IMPLIED_0xE8,
        BNE_RELATIVE_0xD0, 0xF1,
    ])

    # Initialize fail counter
    code.extend(emit_init_fail_counter())

    # Set border/background to purple
    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_PURPLE,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,
        STA_ABSOLUTE_0x8D, 0x21, 0xD0,
    ])

    # Title
    title = "TYPE 0 ULTIMAX ERR" if is_error_cart else "TYPE 0 ULTIMAX"
    code.extend(create_display_code(title, line=0, color=COLOR_WHITE))
    code.extend(create_display_code("EXROM=1 GAME=0", line=1, color=COLOR_YELLOW))

    current_line = 3

    # Test 1: We're running from $E000 (check signature we placed)
    code.extend(create_display_code("ROM AT $E000", line=current_line, color=COLOR_LIGHT_GRAY))

    # Check our signature at $EFF0
    code.extend([
        LDA_ABSOLUTE_0xAD, 0xF0, 0xEF,  # LDA $EFF0
        CMP_IMMEDIATE_0xC9, 0x55,        # CMP #$55 ('U' for ULTIMAX)
        BNE_RELATIVE_0xD0,               # BNE fail1
    ])
    fail1_offset = len(code)
    code.append(0x00)

    # PASS
    pass_pos = 35
    screen_addr = 0x0400 + (current_line * 40) + pass_pos
    color_addr = 0xD800 + (current_line * 40) + pass_pos
    for i, ch in enumerate([0x10, 0x01, 0x13, 0x13]):  # PASS
        code.extend([
            LDA_IMMEDIATE_0xA9, ch,
            STA_ABSOLUTE_0x8D, (screen_addr + i) & 0xFF, (screen_addr + i) >> 8,
            LDA_IMMEDIATE_0xA9, COLOR_PASS,
            STA_ABSOLUTE_0x8D, (color_addr + i) & 0xFF, (color_addr + i) >> 8,
        ])
    code.extend([JMP_ABSOLUTE_0x4C])  # JMP to test2
    jmp_test2 = len(code)
    code.extend([0x00, 0x00])

    # FAIL
    fail1_addr = 0xE000 + code_offset + len(code)
    code.extend(emit_inc_fail_counter())
    for i, ch in enumerate([0x06, 0x01, 0x09, 0x0C]):  # FAIL
        code.extend([
            LDA_IMMEDIATE_0xA9, ch,
            STA_ABSOLUTE_0x8D, (screen_addr + i) & 0xFF, (screen_addr + i) >> 8,
            LDA_IMMEDIATE_0xA9, COLOR_FAIL,
            STA_ABSOLUTE_0x8D, (color_addr + i) & 0xFF, (color_addr + i) >> 8,
        ])

    # Fix branch
    code[fail1_offset] = (fail1_addr - (0xE000 + code_offset + fail1_offset + 1)) & 0xFF

    test2_addr = 0xE000 + code_offset + len(code)
    code[jmp_test2] = test2_addr & 0xFF
    code[jmp_test2 + 1] = (test2_addr >> 8) & 0xFF

    current_line += 1

    # Test 2: Reset vector at $FFFC
    code.extend(create_display_code("RESET VEC $FFFC", line=current_line, color=COLOR_LIGHT_GRAY))

    code.extend([
        LDA_ABSOLUTE_0xAD, 0xFC, 0xFF,  # LDA $FFFC
        CMP_IMMEDIATE_0xC9, code_start & 0xFF,  # CMP #lo
        BNE_RELATIVE_0xD0,
    ])
    fail2_offset = len(code)
    code.append(0x00)

    code.extend([
        LDA_ABSOLUTE_0xAD, 0xFD, 0xFF,  # LDA $FFFD
        CMP_IMMEDIATE_0xC9, (code_start >> 8) & 0xFF,  # CMP #hi
        BNE_RELATIVE_0xD0,
    ])
    fail2_offset2 = len(code)
    code.append(0x00)

    # PASS
    screen_addr = 0x0400 + (current_line * 40) + pass_pos
    color_addr = 0xD800 + (current_line * 40) + pass_pos
    for i, ch in enumerate([0x10, 0x01, 0x13, 0x13]):
        code.extend([
            LDA_IMMEDIATE_0xA9, ch,
            STA_ABSOLUTE_0x8D, (screen_addr + i) & 0xFF, (screen_addr + i) >> 8,
            LDA_IMMEDIATE_0xA9, COLOR_PASS,
            STA_ABSOLUTE_0x8D, (color_addr + i) & 0xFF, (color_addr + i) >> 8,
        ])
    code.extend([JMP_ABSOLUTE_0x4C])
    jmp_done = len(code)
    code.extend([0x00, 0x00])

    # FAIL
    fail2_addr = 0xE000 + code_offset + len(code)
    code.extend(emit_inc_fail_counter())
    for i, ch in enumerate([0x06, 0x01, 0x09, 0x0C]):
        code.extend([
            LDA_IMMEDIATE_0xA9, ch,
            STA_ABSOLUTE_0x8D, (screen_addr + i) & 0xFF, (screen_addr + i) >> 8,
            LDA_IMMEDIATE_0xA9, COLOR_FAIL,
            STA_ABSOLUTE_0x8D, (color_addr + i) & 0xFF, (color_addr + i) >> 8,
        ])

    code[fail2_offset] = (fail2_addr - (0xE000 + code_offset + fail2_offset + 1)) & 0xFF
    code[fail2_offset2] = (fail2_addr - (0xE000 + code_offset + fail2_offset2 + 1)) & 0xFF

    current_line += 2

    # Final status
    done_addr = 0xE000 + code_offset + len(code)
    code[jmp_done] = done_addr & 0xFF
    code[jmp_done + 1] = (done_addr >> 8) & 0xFF

    # Check fail counter
    code.extend(emit_load_fail_counter())
    code.extend([
        BEQ_RELATIVE_0xF0, 0x03,
        JMP_ABSOLUTE_0x4C,
    ])
    jmp_show_fail = len(code)
    code.extend([0x00, 0x00])

    # All passed - green border (keep black background for text visibility)
    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_GREEN,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # Border green
    ])
    code.extend(create_display_code("ALL TESTS PASSED", line=current_line, color=COLOR_GREEN))
    code.extend(create_display_code("TYPE 0 SUPPORTED: PASS", line=current_line + 1, color=COLOR_GREEN))
    code.extend([JMP_ABSOLUTE_0x4C])
    jmp_loop = len(code)
    code.extend([0x00, 0x00])

    # Show fail - red border (keep black background for text visibility)
    show_fail_addr = 0xE000 + code_offset + len(code)
    code[jmp_show_fail] = show_fail_addr & 0xFF
    code[jmp_show_fail + 1] = (show_fail_addr >> 8) & 0xFF

    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_RED,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # Border red
    ])
    code.extend(create_display_code("VERIFICATION FAILED", line=current_line, color=COLOR_FAIL))
    code.extend(create_display_code("TYPE 0 SUPPORTED: FAIL", line=current_line + 1, color=COLOR_FAIL))

    # Mark tests complete (set bit 7, preserve failure count)
    loop_addr = 0xE000 + code_offset + len(code)
    code[jmp_loop] = loop_addr & 0xFF
    code[jmp_loop + 1] = (loop_addr >> 8) & 0xFF
    code.extend(emit_mark_tests_complete())

    # Infinite loop
    inf_loop_addr = 0xE000 + code_offset + len(code)
    code.extend([
        JMP_ABSOLUTE_0x4C, inf_loop_addr & 0xFF, (inf_loop_addr >> 8) & 0xFF,
    ])

    # Copy code
    for i, byte in enumerate(code):
        ultimax_rom[code_offset + i] = byte

    # Add signature at $EFF0
    ultimax_rom[0x0FF0] = 0x55  # 'U' for ULTIMAX

    # Optionally create ROML at $8000-$9FFF
    roml_data = None
    if include_roml:
        roml_data = bytearray(C64.ROML_SIZE)  # 8KB for $8000-$9FFF
        # Add signature at $8FF0 for ROML detection test
        roml_data[0x0FF0] = 0x52  # 'R' for ROML
        roml_data = bytes(roml_data)

    if include_roml:
        desc = "Type 0 Ultimax+ROML" if not is_error_cart else "Type 0 Ultimax+ROML error"
    else:
        desc = "Type 0 Ultimax mode" if not is_error_cart else "Type 0 Ultimax error"
    return bytes(ultimax_rom), roml_data, desc


def create_type0_test_cart(is_error_cart: bool = False) -> tuple[bytes, bytes, str]:
    """Create Type 0 (Static ROM) 16KB test cartridge - for backwards compatibility.

    This is the default 16KB mode test for error cart generation.

    Args:
        is_error_cart: If True, this is for error/regression testing

    Returns:
        Tuple of (ROML bytes, ROMH bytes, description)
    """
    return create_type0_16k_test_cart(is_error_cart)


def create_type1_test_cart(is_error_cart: bool = False) -> tuple[list[bytes], str]:
    """Create Type 1 (Action Replay) test cartridge with PASS/FAIL for each test.

    Uses generate_mapper_tests() as the single source of truth for test names,
    ensuring consistency with error cart display.

    IMPORTANT: Bank switching tests must execute from RAM because when we switch
    ROM banks, the code we're executing from (in ROML) gets replaced with the
    new bank's data. The solution is to copy a small test routine to RAM,
    execute it there, and return the result.

    TEST PATTERN: For each test:
    1. Display test name with "FAIL" (assumes failure)
    2. Run the test
    3. If test passes, overwrite "FAIL" with "PASS"
    4. If test fails, FAIL is already displayed, increment fail counter

    This ensures any crash/hang leaves FAIL visible.

    Args:
        is_error_cart: If True, this is for error/regression testing

    Returns:
        Tuple of (list of 4 bank bytes, description)
    """
    # We need to build this cart manually since we need RAM-based bank testing
    cart = bytearray(C64.ROML_SIZE)

    # Cartridge header at $8000-$8008
    cart[0x0000] = 0x09  # Cold start lo -> $8009
    cart[0x0001] = 0x80  # Cold start hi
    cart[0x0002] = 0x09  # Warm start lo -> $8009
    cart[0x0003] = 0x80  # Warm start hi
    cart[0x0004] = 0xC3  # 'C' (CBM80 signature)
    cart[0x0005] = 0xC2  # 'B'
    cart[0x0006] = 0xCD  # 'M'
    cart[0x0007] = 0x38  # '8'
    cart[0x0008] = 0x30  # '0'

    code = []
    code_base = 0x8009

    # Initialize - disable interrupts, set up stack
    code.extend([
        SEI_IMPLIED_0x78,
        LDX_IMMEDIATE_0xA2, 0xFF,
        TXS_IMPLIED_0x9A,
    ])

    # Clear screen
    code.extend([
        LDA_IMMEDIATE_0xA9, 0x20,
        LDX_IMMEDIATE_0xA2, 0x00,
    ])
    code.extend([
        STA_ABSOLUTE_X_0x9D, 0x00, 0x04,
        STA_ABSOLUTE_X_0x9D, 0x00, 0x05,
        STA_ABSOLUTE_X_0x9D, 0x00, 0x06,
        STA_ABSOLUTE_X_0x9D, 0x00, 0x07,
        INX_IMPLIED_0xE8,
        BNE_RELATIVE_0xD0, 0xF1,
    ])

    # Initialize fail counter
    code.extend(emit_init_fail_counter())

    # Set border/background to black
    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_BLACK,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,
        STA_ABSOLUTE_0x8D, 0x21, 0xD0,
    ])

    # Display title and type info
    title = "TYPE 1 ERROR CART" if is_error_cart else "TYPE 1 VERIFY"
    code.extend(create_display_code(title, line=0, color=COLOR_WHITE))
    code.extend(create_display_code("TYPE: 1", line=1, color=COLOR_YELLOW))
    code.extend(create_display_code("NAME: ACTION REPLAY", line=2, color=COLOR_YELLOW))

    # Get test names from generate_mapper_tests()
    mapper_tests = generate_mapper_tests(1)
    test_names = {t.test_id: t.name for t in mapper_tests}

    current_line = 4

    # === Bank Test Routine in RAM ===
    # We'll copy a small routine to $C000 (free RAM area) that:
    # 1. Switches to the requested bank (bank number in A)
    # 2. Reads signature byte at $9FF5
    # 3. Switches back to bank 0
    # 4. Returns with signature byte in A
    #
    # RAM routine at $C000:
    #   ASL A           ; $0A - multiply by 8 (shift left 3 times)
    #   ASL A           ; $0A
    #   ASL A           ; $0A
    #   STA $DE00       ; $8D $00 $DE - switch bank
    #   LDA $9FF5       ; $AD $F5 $9F - read signature
    #   PHA             ; $48 - save result
    #   LDA #$00        ; $A9 $00 - bank 0
    #   STA $DE00       ; $8D $00 $DE - switch back
    #   PLA             ; $68 - restore result
    #   RTS             ; $60

    ram_routine = [
        0x0A,              # ASL A
        0x0A,              # ASL A
        0x0A,              # ASL A
        0x8D, 0x00, 0xDE,  # STA $DE00
        0xAD, 0xF5, 0x9F,  # LDA $9FF5
        0x48,              # PHA
        0xA9, 0x00,        # LDA #$00
        0x8D, 0x00, 0xDE,  # STA $DE00
        0x68,              # PLA
        0x60,              # RTS
    ]

    # Copy RAM routine to $C000
    for i, byte in enumerate(ram_routine):
        code.extend([
            LDA_IMMEDIATE_0xA9, byte,
            STA_ABSOLUTE_0x8D, (0xC000 + i) & 0xFF, (0xC000 + i) >> 8,
        ])

    # Helper function to emit a test with FAIL-first pattern
    def emit_test(test_name, line, test_code_emitter):
        """Emit test code with FAIL displayed first, updated to PASS on success.

        Args:
            test_name: Display name for the test
            line: Screen line number
            test_code_emitter: Function that emits test code and returns (pass_branch_idx, is_beq)
                              where pass_branch_idx is the index of the branch placeholder
                              and is_beq indicates if it's BEQ (True) or BNE (False)
        """
        nonlocal code

        # Calculate screen positions
        result_screen = 0x0400 + (line * 40) + 35
        result_color = 0xD800 + (line * 40) + 35

        # 1. Display test name with FAIL
        code.extend(create_display_code(test_name, line=line, color=COLOR_LIGHT_GRAY))
        for i, ch in enumerate([0x06, 0x01, 0x09, 0x0C]):  # FAIL
            code.extend([
                LDA_IMMEDIATE_0xA9, ch,
                STA_ABSOLUTE_0x8D, (result_screen + i) & 0xFF, (result_screen + i) >> 8,
                LDA_IMMEDIATE_0xA9, COLOR_FAIL,
                STA_ABSOLUTE_0x8D, (result_color + i) & 0xFF, (result_color + i) >> 8,
            ])

        # 2. Run the test - emitter adds test code and returns branch info
        pass_branch_idx, is_beq = test_code_emitter()

        # 3. If we get here without branching, test failed - increment counter and jump to next
        code.extend(emit_inc_fail_counter())
        code.extend([JMP_ABSOLUTE_0x4C, 0x00, 0x00])  # JMP to next test (placeholder)
        fail_done_jmp = len(code) - 2

        # 4. PASS label - overwrite FAIL with PASS
        pass_addr = len(code)
        # Fix up the branch to point here
        branch_offset = pass_addr - (pass_branch_idx + 1)
        if branch_offset < -128 or branch_offset > 127:
            raise ValueError(f"Branch offset {branch_offset} out of range")
        code[pass_branch_idx] = branch_offset & 0xFF

        for i, ch in enumerate([0x10, 0x01, 0x13, 0x13]):  # PASS
            code.extend([
                LDA_IMMEDIATE_0xA9, ch,
                STA_ABSOLUTE_0x8D, (result_screen + i) & 0xFF, (result_screen + i) >> 8,
                LDA_IMMEDIATE_0xA9, COLOR_PASS,
                STA_ABSOLUTE_0x8D, (result_color + i) & 0xFF, (result_color + i) >> 8,
            ])

        # 5. Next test label - fix up fail jump
        next_addr = len(code)
        code[fail_done_jmp] = (code_base + next_addr) & 0xFF
        code[fail_done_jmp + 1] = ((code_base + next_addr) >> 8) & 0xFF

    # === Test 1: Bank 0 (no switch needed, test directly) ===
    def bank0_test():
        # Check signature directly (we're already in bank 0)
        # Test passes if $9FF0='B' AND $9FF5='0'
        code.extend([
            LDA_ABSOLUTE_0xAD, 0xF0, 0x9F,  # LDA $9FF0
            CMP_IMMEDIATE_0xC9, 0x42,        # CMP #'B'
            BNE_RELATIVE_0xD0, 0x00,         # BNE to fail-continue (placeholder)
        ])
        first_fail_branch = len(code) - 1

        code.extend([
            LDA_ABSOLUTE_0xAD, 0xF5, 0x9F,  # LDA $9FF5
            CMP_IMMEDIATE_0xC9, 0x30,        # CMP #'0'
            BEQ_RELATIVE_0xF0, 0x00,         # BEQ to pass (placeholder)
        ])
        pass_branch = len(code) - 1

        # First fail branch jumps here (to fall through to fail)
        fail_continue = len(code)
        code[first_fail_branch] = (fail_continue - (first_fail_branch + 1)) & 0xFF

        return pass_branch, True  # BEQ branches to pass

    emit_test(test_names.get("bank_0", "Bank 0 $0000"), current_line, bank0_test)
    current_line += 1

    # === Tests 2-4: Banks 1-3 (use RAM routine) ===
    for bank_num in range(1, 4):
        def bank_test(bn=bank_num):
            expected_char = 0x30 + bn  # '1', '2', '3'
            # Call RAM routine with bank number in A
            code.extend([
                LDA_IMMEDIATE_0xA9, bn,
                JSR_ABSOLUTE_0x20, 0x00, 0xC0,  # JSR $C000
                CMP_IMMEDIATE_0xC9, expected_char,
                BEQ_RELATIVE_0xF0, 0x00,  # BEQ to pass (placeholder)
            ])
            return len(code) - 1, True  # BEQ branches to pass

        test_name = test_names.get(f"bank_{bank_num}", f"Bank {bank_num} ${bank_num * 0x2000:04X}")
        emit_test(test_name, current_line, bank_test)
        current_line += 1

    # === Test 5: IO2 RAM at $DF00 ===
    # This test must run from RAM because enabling RAM mode remaps ROML.
    # If we execute from ROML when RAM is enabled, we'd execute garbage and crash.
    #
    # RAM routine at $C020 (after bank test routine):
    #   LDA #$A5          ; Test pattern
    #   STA $9F00         ; Write to ROML RAM area (while RAM disabled - goes nowhere)
    #   LDA #$20          ; Enable RAM mode
    #   STA $DE00
    #   LDA $9F00         ; Read from ROML (should now be RAM, should read $A5 if we wrote it)
    #   CMP #$A5          ; Check ROML RAM works
    #   BNE fail          ; ROML RAM not working
    #   LDA #$5A          ; Different test pattern for IO2
    #   STA $DF00         ; Write to IO2 RAM
    #   LDA $DF00         ; Read back
    #   PHA               ; Save IO2 result
    #   LDA #$00          ; Disable RAM
    #   STA $DE00
    #   PLA               ; Restore IO2 result
    #   CMP #$5A          ; Check IO2 RAM works
    #   BEQ pass          ; Return with Z=1 for pass
    # fail:
    #   LDA #$00          ; Ensure RAM disabled on fail path too
    #   STA $DE00
    #   LDA #$01          ; Return with Z=0 for fail
    # pass:
    #   RTS

    io2_ram_routine = [
        # Enable RAM mode first, then write/read test patterns
        0xA9, 0x20,        # LDA #$20 (enable RAM)
        0x8D, 0x00, 0xDE,  # STA $DE00
        # Now ROML ($8000-$9FFF) is mapped to RAM, and IO2 ($DF00-$DFFF) too
        # Write test pattern to ROML RAM area
        0xA9, 0xA5,        # LDA #$A5
        0x8D, 0x00, 0x9F,  # STA $9F00 (ROML RAM)
        0xAD, 0x00, 0x9F,  # LDA $9F00 (read back)
        0xC9, 0xA5,        # CMP #$A5
        0xD0, 0x13,        # BNE fail (ROML RAM not working) - skip 19 bytes to fail
        # Test IO2 RAM
        0xA9, 0x5A,        # LDA #$5A (IO2 test pattern)
        0x8D, 0x00, 0xDF,  # STA $DF00
        0xAD, 0x00, 0xDF,  # LDA $DF00
        0x48,              # PHA (save result)
        0xA9, 0x00,        # LDA #$00 (disable RAM)
        0x8D, 0x00, 0xDE,  # STA $DE00
        0x68,              # PLA (restore result)
        0xC9, 0x5A,        # CMP #$5A
        0xF0, 0x07,        # BEQ pass (skip fail path)
        # fail:
        0xA9, 0x00,        # LDA #$00 (disable RAM on fail)
        0x8D, 0x00, 0xDE,  # STA $DE00
        0xA9, 0x01,        # LDA #$01 (set Z=0 for fail)
        # pass:
        0x60,              # RTS (Z flag indicates pass/fail)
    ]

    # Copy IO2 RAM test routine to $C020
    io2_routine_addr = 0xC020
    for i, byte in enumerate(io2_ram_routine):
        code.extend([
            LDA_IMMEDIATE_0xA9, byte,
            STA_ABSOLUTE_0x8D, (io2_routine_addr + i) & 0xFF, (io2_routine_addr + i) >> 8,
        ])

    def io2_test():
        # Call RAM routine - returns with Z=1 for pass, Z=0 for fail
        code.extend([
            JSR_ABSOLUTE_0x20, io2_routine_addr & 0xFF, (io2_routine_addr >> 8) & 0xFF,
            BEQ_RELATIVE_0xF0, 0x00,  # BEQ to pass (placeholder)
        ])
        return len(code) - 1, True  # BEQ branches to pass

    emit_test(test_names.get("io2_ram", "IO2 $DF00 RAM"), current_line, io2_test)
    current_line += 2  # Skip a line

    # === Final status ===
    # Check fail counter
    code.extend(emit_load_fail_counter())
    code.extend([
        BEQ_RELATIVE_0xF0, 0x03,  # BEQ +3 (skip JMP) - no failures
        JMP_ABSOLUTE_0x4C, 0x00, 0x00,  # JMP to show_fail (placeholder)
    ])
    show_fail_jmp = len(code) - 2

    # All passed - green border (keep black background for text visibility)
    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_GREEN,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # Border green
    ])
    code.extend(create_display_code("ALL TESTS PASSED", line=current_line, color=COLOR_GREEN))
    code.extend(create_display_code("TYPE 1 SUPPORTED: PASS", line=current_line + 1, color=COLOR_GREEN))
    code.extend([JMP_ABSOLUTE_0x4C, 0x00, 0x00])  # JMP to loop (placeholder)
    loop_jmp = len(code) - 2

    # Show fail - red border (keep black background for text visibility)
    show_fail_addr = len(code)
    code[show_fail_jmp] = (code_base + show_fail_addr) & 0xFF
    code[show_fail_jmp + 1] = ((code_base + show_fail_addr) >> 8) & 0xFF

    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_RED,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # Border red
    ])
    code.extend(create_display_code("VERIFICATION FAILED", line=current_line, color=COLOR_FAIL))
    code.extend(create_display_code("TYPE 1 SUPPORTED: FAIL", line=current_line + 1, color=COLOR_FAIL))

    # Mark tests complete (set bit 7, preserve failure count)
    loop_addr = len(code)
    code[loop_jmp] = (code_base + loop_addr) & 0xFF
    code[loop_jmp + 1] = ((code_base + loop_addr) >> 8) & 0xFF
    code.extend(emit_mark_tests_complete())

    # Infinite loop
    inf_loop_addr = len(code)
    code.extend([JMP_ABSOLUTE_0x4C, (code_base + inf_loop_addr) & 0xFF, ((code_base + inf_loop_addr) >> 8) & 0xFF])

    # Copy code into cartridge
    for i, byte in enumerate(code):
        cart[0x0009 + i] = byte

    # Add signature to bank 0
    sig_offset = 0x1FF0
    for i, b in enumerate(b"BANK-0"):
        cart[sig_offset + i] = b

    # Create banks 1-3 with their signatures
    banks = [bytes(cart)]
    for bank_num in range(1, 4):
        bank = bytearray(C64.ROML_SIZE)
        sig = f"BANK-{bank_num}".encode('ascii')
        for i, b in enumerate(sig):
            bank[sig_offset + i] = b
        banks.append(bytes(bank))

    desc = "Type 1 verification" if not is_error_cart else "Type 1 error cart"
    return banks, desc


def create_error_cartridge(hw_type: int, type_name: str, exrom: int = 0, game: int = 1) -> bytes:
    """Create an 8KB error/test cartridge that tests mapper hardware.

    For supported types (0, 1), this runs the same tests as the verification
    cart. For unsupported types, it uses CartridgeTestResults to create a
    display that matches the dynamic error carts generated at runtime.

    Args:
        hw_type: CRT hardware type number
        type_name: Human-readable name of the cartridge type
        exrom: EXROM line value (for determining relevant tests)
        game: GAME line value (for determining relevant tests)

    Returns:
        8KB cartridge ROM data (or tuple for multi-bank types)
    """
    # For supported types, use the test builder
    if hw_type == 0:
        roml, romh, _ = create_type0_test_cart(is_error_cart=True)
        return roml  # Note: ROMH tests will fail without ROMH data
    elif hw_type == 1:
        banks, _ = create_type1_test_cart(is_error_cart=True)
        return banks[0]  # Return just bank 0 for error cart
    elif hw_type == 5:
        banks, _ = create_type5_test_cart(is_error_cart=True, num_banks=8)
        return banks[0]  # Return just bank 0 for error cart

    # For unsupported types, use CartridgeTestResults for consistent display
    # with runtime-generated error carts (single source of truth)
    results = CartridgeTestResults(
        signature_valid=True,
        header_size_valid=True,
        version_valid=True,
        hardware_type=hw_type,
        hardware_name=type_name,
        exrom_line=exrom,
        game_line=game,
        cart_name=f"TYPE {hw_type} ERROR",
        chip_packets_found=False,  # Pre-generated, no actual CHIP data parsed
        chip_count=0,
        roml_valid=False,
        romh_valid=False,
        ultimax_romh_valid=False,
        mapper_supported=False,  # Unsupported type
        fully_loaded=False,
    )

    error_lines = results.to_display_lines()
    return create_error_cartridge_rom(error_lines, border_color=0x02)


def write_crt_cartridge(
    path: Path,
    roml: bytes,
    romh: bytes | None = None,
    name: str = "TEST",
    single_chip: bool = False,
    hardware_type: int = 0,
    exrom: int | None = None,
    game: int | None = None,
) -> None:
    """Write a CRT format cartridge file.

    Args:
        path: Output file path
        roml: ROML data (8KB, $8000-$9FFF)
        romh: ROMH data (8KB, $A000-$BFFF) or None for 8K carts
        name: Cartridge name (max 32 chars)
        single_chip: If True and romh is provided, write as single 16KB CHIP packet
                     at $8000 (like many real-world cartridges). If False, write
                     as two separate CHIP packets (ROML at $8000, ROMH at $A000).
        hardware_type: CRT hardware type ID (0-85)
        exrom: EXROM line state (0=active, 1=inactive). If None, defaults based on size.
        game: GAME line state (0=active, 1=inactive). If None, defaults based on size.
    """
    is_16k = romh is not None

    # Default EXROM/GAME based on cartridge size if not specified
    if exrom is None:
        exrom = 0  # Active (cartridge present)
    if game is None:
        game = 0 if is_16k else 1  # 0 for 16K, 1 for 8K

    # CRT Header (64 bytes)
    header = bytearray(64)
    header[0:16] = b'C64 CARTRIDGE   '  # Signature
    header[0x10:0x14] = (64).to_bytes(4, 'big')  # Header length
    header[0x14] = 1  # Version hi
    header[0x15] = 0  # Version lo
    header[0x16:0x18] = hardware_type.to_bytes(2, 'big')  # Hardware type
    header[0x18] = exrom  # EXROM
    header[0x19] = game   # GAME
    name_bytes = name.encode('ascii')[:32].ljust(32, b'\x00')
    header[0x20:0x40] = name_bytes

    with open(path, 'wb') as f:
        f.write(bytes(header))

        if is_16k and single_chip:
            # Write as single 16KB CHIP packet at $8000 (common real-world format)
            combined_rom = roml + romh
            chip = bytearray(16)
            chip[0:4] = b'CHIP'
            chip[4:8] = (16 + len(combined_rom)).to_bytes(4, 'big')  # Packet length
            chip[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
            chip[10:12] = (0).to_bytes(2, 'big')  # Bank (0)
            chip[12:14] = (C64.ROML_START).to_bytes(2, 'big')  # Load address ($8000)
            chip[14:16] = (len(combined_rom)).to_bytes(2, 'big')  # ROM size (16384)
            f.write(bytes(chip))
            f.write(combined_rom)
        else:
            # Write ROML as separate CHIP packet
            chip_roml = bytearray(16)
            chip_roml[0:4] = b'CHIP'
            chip_roml[4:8] = (16 + len(roml)).to_bytes(4, 'big')  # Packet length
            chip_roml[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
            chip_roml[10:12] = (0).to_bytes(2, 'big')  # Bank (0)
            chip_roml[12:14] = (C64.ROML_START).to_bytes(2, 'big')  # Load address
            chip_roml[14:16] = (len(roml)).to_bytes(2, 'big')  # ROM size
            f.write(bytes(chip_roml))
            f.write(roml)

            if romh is not None:
                # Write ROMH as separate CHIP packet
                chip_romh = bytearray(16)
                chip_romh[0:4] = b'CHIP'
                chip_romh[4:8] = (16 + len(romh)).to_bytes(4, 'big')
                chip_romh[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
                chip_romh[10:12] = (0).to_bytes(2, 'big')  # Bank (0)
                chip_romh[12:14] = (C64.ROMH_START).to_bytes(2, 'big')  # Load address ($A000)
                chip_romh[14:16] = (len(romh)).to_bytes(2, 'big')
                f.write(bytes(chip_romh))
                f.write(romh)


def create_ultimax_cartridge() -> tuple[bytes, str]:
    """Create an Ultimax mode test cartridge with ROM at $E000.

    Ultimax mode has EXROM=1, GAME=0 and places ROM at $E000-$FFFF,
    replacing the KERNAL ROM. This is used by diagnostic cartridges
    like the Dead Test ROM.

    Returns:
        Tuple of (cartridge bytes for $E000, description)
    """
    # Ultimax ROM is 8KB at $E000-$FFFF
    cart = bytearray(C64.ROML_SIZE)

    # Reset vector at $FFFC-$FFFD points to start of our code
    # Code starts at $E009 (after the CBM80-style header area)
    code_start = 0xE009

    # Put reset vector at the end of ROM
    # $FFFC = lo byte, $FFFD = hi byte of reset vector
    cart[0x1FFC] = code_start & 0xFF        # $FFFC - reset vector lo
    cart[0x1FFD] = (code_start >> 8) & 0xFF  # $FFFD - reset vector hi

    # Also put a valid NMI vector (point to RTI)
    rti_addr = 0xE000 + 0x1FF0  # Put RTI near end
    cart[0x1FFA] = rti_addr & 0xFF          # $FFFA - NMI vector lo
    cart[0x1FFB] = (rti_addr >> 8) & 0xFF   # $FFFB - NMI vector hi
    cart[0x1FF0] = RTI_IMPLIED_0x40         # RTI instruction

    # IRQ vector (also point to RTI)
    cart[0x1FFE] = rti_addr & 0xFF          # $FFFE - IRQ vector lo
    cart[0x1FFF] = (rti_addr >> 8) & 0xFF   # $FFFF - IRQ vector hi

    # Code starts at $E009
    code_offset = 0x0009
    code = []

    # Initialize - disable interrupts, set up stack
    code.extend([
        SEI_IMPLIED_0x78,
        LDX_IMMEDIATE_0xA2, 0xFF,
        TXS_IMPLIED_0x9A,
    ])

    # In Ultimax mode, we need to initialize the VIC and screen RAM ourselves
    # since KERNAL is not available

    # Set up VIC for text mode
    code.extend([
        LDA_IMMEDIATE_0xA9, 0x1B,  # enable screen, text mode
        STA_ABSOLUTE_0x8D, 0x11, 0xD0,  # $D011
        LDA_IMMEDIATE_0xA9, 0x08,  # 40 columns
        STA_ABSOLUTE_0x8D, 0x16, 0xD0,  # $D016
        LDA_IMMEDIATE_0xA9, 0x14,  # screen at $0400, charset at $1000
        STA_ABSOLUTE_0x8D, 0x18, 0xD0,  # $D018
    ])

    # Clear screen by filling $0400-$07E7 with spaces (0x20)
    code.extend([
        LDA_IMMEDIATE_0xA9, 0x20,  # space character
        LDX_IMMEDIATE_0xA2, 0x00,
    ])
    # clear_loop:
    code.extend([
        STA_ABSOLUTE_X_0x9D, 0x00, 0x04,  # STA $0400,X
        STA_ABSOLUTE_X_0x9D, 0x00, 0x05,  # STA $0500,X
        STA_ABSOLUTE_X_0x9D, 0x00, 0x06,  # STA $0600,X
        STA_ABSOLUTE_X_0x9D, 0x00, 0x07,  # STA $0700,X
        INX_IMPLIED_0xE8,
        BNE_RELATIVE_0xD0, 0xF1,  # branch back -15 bytes
    ])

    # Set border and background to purple
    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_PURPLE,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # $D020 border color
        STA_ABSOLUTE_0x8D, 0x21, 0xD0,  # $D021 background color
    ])

    # Display messages
    code.extend(create_display_code("ULTIMAX CARTRIDGE TEST", line=0, color=COLOR_WHITE))
    code.extend(create_display_code("ROM AT $E000-$FFFF", line=2, color=COLOR_YELLOW))
    code.extend(create_display_code("REPLACES KERNAL ROM", line=4, color=COLOR_YELLOW))
    code.extend(create_display_code("EXROM=1 GAME=0", line=6, color=COLOR_GREEN))

    # Infinite loop
    loop_addr = 0xE000 + code_offset + len(code)
    code.extend([
        JMP_ABSOLUTE_0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,
    ])

    # Copy code into cartridge
    for i, byte in enumerate(code):
        cart[code_offset + i] = byte

    return bytes(cart), f"Code size: {len(code)} bytes starting at $E009"


def write_ultimax_crt_cartridge(
    path: Path,
    ultimax_romh: bytes,
    roml: bytes | None = None,
    name: str = "TEST",
) -> None:
    """Write a CRT format Ultimax cartridge file.

    Args:
        path: Output file path
        ultimax_romh: ROM data for $E000-$FFFF (8KB, replaces KERNAL)
        roml: Optional ROM data for $8000-$9FFF (8KB)
        name: Cartridge name (max 32 chars)
    """
    # CRT Header (64 bytes)
    header = bytearray(64)
    header[0:16] = b'C64 CARTRIDGE   '  # Signature
    header[0x10:0x14] = (64).to_bytes(4, 'big')  # Header length
    header[0x14] = 1  # Version hi
    header[0x15] = 0  # Version lo
    header[0x16:0x18] = (0).to_bytes(2, 'big')  # Hardware type (0 = normal)
    header[0x18] = 1  # EXROM = 1 (inactive)
    header[0x19] = 0  # GAME = 0 (active) -> Ultimax mode
    name_bytes = name.encode('ascii')[:32].ljust(32, b'\x00')
    header[0x20:0x40] = name_bytes

    with open(path, 'wb') as f:
        f.write(bytes(header))

        # Write optional ROML CHIP packet
        if roml is not None:
            chip_roml = bytearray(16)
            chip_roml[0:4] = b'CHIP'
            chip_roml[4:8] = (16 + len(roml)).to_bytes(4, 'big')
            chip_roml[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
            chip_roml[10:12] = (0).to_bytes(2, 'big')  # Bank (0)
            chip_roml[12:14] = (C64.ROML_START).to_bytes(2, 'big')  # $8000
            chip_roml[14:16] = (len(roml)).to_bytes(2, 'big')
            f.write(bytes(chip_roml))
            f.write(roml)

        # Write Ultimax ROMH CHIP packet at $E000
        chip_romh = bytearray(16)
        chip_romh[0:4] = b'CHIP'
        chip_romh[4:8] = (16 + len(ultimax_romh)).to_bytes(4, 'big')
        chip_romh[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
        chip_romh[10:12] = (0).to_bytes(2, 'big')  # Bank (0)
        chip_romh[12:14] = (KERNAL_ROM_START).to_bytes(2, 'big')  # $E000
        chip_romh[14:16] = (len(ultimax_romh)).to_bytes(2, 'big')
        f.write(bytes(chip_romh))
        f.write(ultimax_romh)


def create_mapper_test_cartridge(hw_type: int, type_name: str) -> bytes:
    """Create an 8KB test cartridge that displays the mapper type info.

    This creates a valid cartridge ROM that can be used to test that
    a specific hardware type is correctly identified and handled.

    Args:
        hw_type: CRT hardware type number
        type_name: Human-readable name of the cartridge type

    Returns:
        8KB cartridge ROM data
    """
    cart = bytearray(C64.ROML_SIZE)

    # Cartridge header at $8000-$8008
    cart[0x0000] = 0x09  # Cold start lo -> $8009
    cart[0x0001] = 0x80  # Cold start hi
    cart[0x0002] = 0x09  # Warm start lo -> $8009
    cart[0x0003] = 0x80  # Warm start hi
    cart[0x0004] = 0xC3  # 'C' (CBM80 signature)
    cart[0x0005] = 0xC2  # 'B'
    cart[0x0006] = 0xCD  # 'M'
    cart[0x0007] = 0x38  # '8'
    cart[0x0008] = 0x30  # '0'

    # Code starts at $8009
    code_offset = 0x0009
    code = []

    # Initialize - disable interrupts, set up stack
    code.extend([
        SEI_IMPLIED_0x78,
        LDX_IMMEDIATE_0xA2, 0xFF,
        TXS_IMPLIED_0x9A,
    ])

    # Clear screen by filling $0400-$07E7 with spaces (0x20)
    code.extend([
        LDA_IMMEDIATE_0xA9, 0x20,  # space character
        LDX_IMMEDIATE_0xA2, 0x00,
    ])
    # clear_loop:
    code.extend([
        STA_ABSOLUTE_X_0x9D, 0x00, 0x04,  # STA $0400,X
        STA_ABSOLUTE_X_0x9D, 0x00, 0x05,  # STA $0500,X
        STA_ABSOLUTE_X_0x9D, 0x00, 0x06,  # STA $0600,X
        STA_ABSOLUTE_X_0x9D, 0x00, 0x07,  # STA $0700,X
        INX_IMPLIED_0xE8,
        BNE_RELATIVE_0xD0, 0xF1,  # branch back -15 bytes
    ])

    # Set border and background to dark blue
    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_BLUE,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # $D020 border color
        STA_ABSOLUTE_0x8D, 0x21, 0xD0,  # $D021 background color
    ])

    # Display messages - showing the mapper type
    lines = [
        ("MAPPER TEST CARTRIDGE", 1, COLOR_WHITE),
        ("", 3, COLOR_WHITE),
        (f"TYPE: {hw_type}", 4, COLOR_YELLOW),
        (f"NAME: {type_name.upper()[:30]}", 6, COLOR_YELLOW),
        ("", 8, COLOR_WHITE),
        ("THIS CARTRIDGE IS FOR TESTING", 10, COLOR_GREEN),
        ("THE MAPPER TYPE IDENTIFICATION", 11, COLOR_GREEN),
        ("AND BANK SWITCHING LOGIC.", 12, COLOR_GREEN),
        ("", 14, COLOR_WHITE),
        ("CODE IS EXECUTING IN ROML", 16, COLOR_LIGHT_BLUE),
        ("AT $8000-$9FFF", 17, COLOR_LIGHT_BLUE),
    ]

    for text, line, color in lines:
        code.extend(create_display_code(text, line=line, color=color))

    # Infinite loop
    loop_addr = C64.ROML_START + code_offset + len(code)
    code.extend([
        JMP_ABSOLUTE_0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,
    ])

    # Copy code into cartridge
    for i, byte in enumerate(code):
        cart[code_offset + i] = byte

    return bytes(cart)


def write_action_replay_crt(path: Path, banks: list[bytes], name: str = "TEST") -> None:
    """Write an Action Replay CRT file with multiple banks.

    Args:
        path: Output file path
        banks: List of 8KB ROM banks
        name: Cartridge name
    """
    # CRT Header (64 bytes)
    header = bytearray(64)
    header[0:16] = b'C64 CARTRIDGE   '
    header[0x10:0x14] = (64).to_bytes(4, 'big')  # Header length
    header[0x14] = 1  # Version hi
    header[0x15] = 0  # Version lo
    header[0x16:0x18] = (1).to_bytes(2, 'big')  # Hardware type 1 = Action Replay
    header[0x18] = 0  # EXROM = 0 (active)
    header[0x19] = 0  # GAME = 0 (active) -> 16KB mode
    name_bytes = name.encode('ascii')[:32].ljust(32, b'\x00')
    header[0x20:0x40] = name_bytes

    with open(path, 'wb') as f:
        f.write(bytes(header))

        # Write each bank as a CHIP packet
        for bank_num, bank_data in enumerate(banks):
            chip = bytearray(16)
            chip[0:4] = b'CHIP'
            chip[4:8] = (16 + len(bank_data)).to_bytes(4, 'big')
            chip[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
            chip[10:12] = bank_num.to_bytes(2, 'big')  # Bank number
            chip[12:14] = (C64.ROML_START).to_bytes(2, 'big')  # Load address
            chip[14:16] = (len(bank_data)).to_bytes(2, 'big')
            f.write(bytes(chip))
            f.write(bank_data)


def write_simons_basic_crt(path: Path, roml_data: bytes, romh_data: bytes, name: str = "TEST") -> None:
    """Write a Simons' BASIC CRT file with ROML and ROMH.

    Args:
        path: Output file path
        roml_data: 8KB ROM data for ROML region
        romh_data: 8KB ROM data for ROMH region
        name: Cartridge name
    """
    # CRT Header (64 bytes)
    header = bytearray(64)
    header[0:16] = b'C64 CARTRIDGE   '
    header[0x10:0x14] = (64).to_bytes(4, 'big')  # Header length
    header[0x14] = 1  # Version hi
    header[0x15] = 0  # Version lo
    header[0x16:0x18] = (4).to_bytes(2, 'big')  # Hardware type 4 = Simons' BASIC
    header[0x18] = 0  # EXROM = 0 (active)
    header[0x19] = 1  # GAME = 1 (inactive) -> 8KB mode initially
    name_bytes = name.encode('ascii')[:32].ljust(32, b'\x00')
    header[0x20:0x40] = name_bytes

    with open(path, 'wb') as f:
        f.write(bytes(header))

        # Write ROML CHIP packet (bank 0 at $8000)
        chip_roml = bytearray(16)
        chip_roml[0:4] = b'CHIP'
        chip_roml[4:8] = (16 + len(roml_data)).to_bytes(4, 'big')
        chip_roml[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
        chip_roml[10:12] = (0).to_bytes(2, 'big')  # Bank 0
        chip_roml[12:14] = (C64.ROML_START).to_bytes(2, 'big')  # Load address $8000
        chip_roml[14:16] = (len(roml_data)).to_bytes(2, 'big')
        f.write(bytes(chip_roml))
        f.write(roml_data)

        # Write ROMH CHIP packet (bank 0 at $A000)
        chip_romh = bytearray(16)
        chip_romh[0:4] = b'CHIP'
        chip_romh[4:8] = (16 + len(romh_data)).to_bytes(4, 'big')
        chip_romh[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
        chip_romh[10:12] = (0).to_bytes(2, 'big')  # Bank 0
        chip_romh[12:14] = (C64.ROMH_START).to_bytes(2, 'big')  # Load address $A000
        chip_romh[14:16] = (len(romh_data)).to_bytes(2, 'big')
        f.write(bytes(chip_romh))
        f.write(romh_data)


def create_type4_test_cart(is_error_cart: bool = False) -> tuple[bytes, bytes, str]:
    """Create Type 4 (Simons' BASIC) test cartridge with ROMH toggle tests.

    Simons' BASIC uses IO1/IO2 writes to toggle ROMH visibility:
    - Write to $DE00: Enable ROMH (16KB mode)
    - Write to $DF00: Disable ROMH (8KB mode)

    We test this by:
    1. Verifying ROML is readable at $8000
    2. Enabling ROMH via $DE00 write, verifying $A000 has our signature
    3. Disabling ROMH via $DF00 write, verifying $A000 no longer has signature

    Args:
        is_error_cart: If True, this is for error/regression testing

    Returns:
        Tuple of (roml_data, romh_data, description)
    """
    roml = bytearray(C64.ROML_SIZE)
    romh = bytearray(C64.ROMH_SIZE)

    # Cartridge header at $8000-$8008
    roml[0x0000] = 0x09  # Cold start lo -> $8009
    roml[0x0001] = 0x80  # Cold start hi
    roml[0x0002] = 0x09  # Warm start lo -> $8009
    roml[0x0003] = 0x80  # Warm start hi
    roml[0x0004] = 0xC3  # 'C' (CBM80 signature)
    roml[0x0005] = 0xC2  # 'B'
    roml[0x0006] = 0xCD  # 'M'
    roml[0x0007] = 0x38  # '8'
    roml[0x0008] = 0x30  # '0'

    # Put a signature at the end of ROML for testing
    ROML_SIG_OFFSET = 0x1FF5
    roml[ROML_SIG_OFFSET] = 0x04  # Type 4 signature

    # Put a signature at the start of ROMH for testing ROMH visibility
    ROMH_SIG_OFFSET = 0x0000  # $A000
    romh[ROMH_SIG_OFFSET] = 0xA4  # Distinct signature for ROMH (0xA for $A000, 4 for type 4)

    code = []
    code_base = 0x8009

    # Initialize - disable interrupts, set up stack
    code.extend([
        SEI_IMPLIED_0x78,
        LDX_IMMEDIATE_0xA2, 0xFF,
        TXS_IMPLIED_0x9A,
    ])

    # Clear screen
    code.extend([
        LDA_IMMEDIATE_0xA9, 0x20,
        LDX_IMMEDIATE_0xA2, 0x00,
    ])
    code.extend([
        STA_ABSOLUTE_X_0x9D, 0x00, 0x04,
        STA_ABSOLUTE_X_0x9D, 0x00, 0x05,
        STA_ABSOLUTE_X_0x9D, 0x00, 0x06,
        STA_ABSOLUTE_X_0x9D, 0x00, 0x07,
        INX_IMPLIED_0xE8,
        BNE_RELATIVE_0xD0, 0xF1,
    ])

    # Initialize fail counter
    code.extend(emit_init_fail_counter())

    # Set border/background to black
    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_BLACK,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,
        STA_ABSOLUTE_0x8D, 0x21, 0xD0,
    ])

    # Display title and type info
    title = "TYPE 4 ERROR CART" if is_error_cart else "TYPE 4 VERIFY"
    code.extend(create_display_code(title, line=0, color=COLOR_WHITE))
    code.extend(create_display_code("TYPE: 4", line=1, color=COLOR_YELLOW))
    code.extend(create_display_code("NAME: SIMONS BASIC", line=2, color=COLOR_YELLOW))

    current_line = 4

    # Helper function to emit a test with FAIL-first pattern
    def emit_test(test_name, line, test_code_emitter):
        """Emit test code with FAIL displayed first, updated to PASS on success."""
        nonlocal code

        # Calculate screen positions
        result_screen = 0x0400 + (line * 40) + 35
        result_color = 0xD800 + (line * 40) + 35

        # 1. Display test name with FAIL
        code.extend(create_display_code(test_name, line=line, color=COLOR_LIGHT_GRAY))
        for i, ch in enumerate([0x06, 0x01, 0x09, 0x0C]):  # FAIL
            code.extend([
                LDA_IMMEDIATE_0xA9, ch,
                STA_ABSOLUTE_0x8D, (result_screen + i) & 0xFF, (result_screen + i) >> 8,
                LDA_IMMEDIATE_0xA9, COLOR_FAIL,
                STA_ABSOLUTE_0x8D, (result_color + i) & 0xFF, (result_color + i) >> 8,
            ])

        # 2. Run the test - emitter adds test code and returns branch info
        pass_branch_idx, is_beq = test_code_emitter()

        # 3. If we get here without branching, test failed - increment counter and jump to next
        code.extend(emit_inc_fail_counter())
        code.extend([JMP_ABSOLUTE_0x4C, 0x00, 0x00])  # JMP to next test (placeholder)
        fail_done_jmp = len(code) - 2

        # 4. PASS label - overwrite FAIL with PASS
        pass_addr = len(code)
        # Fix up the branch to point here
        branch_offset = pass_addr - (pass_branch_idx + 1)
        if branch_offset < -128 or branch_offset > 127:
            raise ValueError(f"Branch offset {branch_offset} out of range")
        code[pass_branch_idx] = branch_offset & 0xFF

        for i, ch in enumerate([0x10, 0x01, 0x13, 0x13]):  # PASS
            code.extend([
                LDA_IMMEDIATE_0xA9, ch,
                STA_ABSOLUTE_0x8D, (result_screen + i) & 0xFF, (result_screen + i) >> 8,
                LDA_IMMEDIATE_0xA9, COLOR_PASS,
                STA_ABSOLUTE_0x8D, (result_color + i) & 0xFF, (result_color + i) >> 8,
            ])

        # 5. Next test label - fix up fail jump
        next_addr = len(code)
        code[fail_done_jmp] = (code_base + next_addr) & 0xFF
        code[fail_done_jmp + 1] = ((code_base + next_addr) >> 8) & 0xFF

    # Test 1: Verify ROML is readable at $9FF5
    def roml_test():
        code.extend([
            LDA_ABSOLUTE_0xAD, 0xF5, 0x9F,   # LDA $9FF5 (ROML signature)
            CMP_IMMEDIATE_0xC9, 0x04,         # Compare to expected signature
            BEQ_RELATIVE_0xF0, 0x00,          # BEQ to pass (placeholder)
        ])
        return len(code) - 1, True

    emit_test("ROML $9FF5", current_line, roml_test)
    current_line += 1

    # Test 2: Enable ROMH via $DE00, verify ROMH signature at $A000
    def romh_enable_test():
        code.extend([
            LDA_IMMEDIATE_0xA9, 0x00,         # Any value
            STA_ABSOLUTE_0x8D, 0x00, 0xDE,    # STA $DE00 - enable ROMH
            LDA_ABSOLUTE_0xAD, 0x00, 0xA0,    # LDA $A000 (ROMH signature)
            CMP_IMMEDIATE_0xC9, 0xA4,         # Compare to expected signature
            BEQ_RELATIVE_0xF0, 0x00,          # BEQ to pass (placeholder)
        ])
        return len(code) - 1, True

    emit_test("$DE00 ENABLE ROMH", current_line, romh_enable_test)
    current_line += 1

    # Test 3: Disable ROMH via $DF00, verify ROMH is gone (shouldn't read 0xA4)
    def romh_disable_test():
        code.extend([
            LDA_IMMEDIATE_0xA9, 0x00,         # Any value
            STA_ABSOLUTE_0x8D, 0x00, 0xDF,    # STA $DF00 - disable ROMH
            LDA_ABSOLUTE_0xAD, 0x00, 0xA0,    # LDA $A000 (should NOT be cart ROMH)
            CMP_IMMEDIATE_0xC9, 0xA4,         # Compare to cart signature
            BNE_RELATIVE_0xD0, 0x00,          # BNE to pass (should NOT match)
        ])
        return len(code) - 1, False  # BNE, not BEQ

    emit_test("$DF00 DISABLE ROMH", current_line, romh_disable_test)
    current_line += 1

    # Test 4: Re-enable ROMH to confirm toggle works
    def romh_reenable_test():
        code.extend([
            LDA_IMMEDIATE_0xA9, 0x00,         # Any value
            STA_ABSOLUTE_0x8D, 0x00, 0xDE,    # STA $DE00 - enable ROMH
            LDA_ABSOLUTE_0xAD, 0x00, 0xA0,    # LDA $A000 (ROMH signature)
            CMP_IMMEDIATE_0xC9, 0xA4,         # Compare to expected signature
            BEQ_RELATIVE_0xF0, 0x00,          # BEQ to pass (placeholder)
        ])
        return len(code) - 1, True

    emit_test("$DE00 RE-ENABLE", current_line, romh_reenable_test)
    current_line += 1

    current_line += 1  # Skip a line before final status

    # === Final status ===
    # Check fail counter
    code.extend(emit_load_fail_counter())
    code.extend([
        BEQ_RELATIVE_0xF0, 0x03,  # BEQ +3 (skip JMP) - no failures
        JMP_ABSOLUTE_0x4C, 0x00, 0x00,  # JMP to show_fail (placeholder)
    ])
    show_fail_jmp = len(code) - 2

    # All passed - green border (keep black background for text visibility)
    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_GREEN,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # Border green
        # Background stays black for text visibility
    ])
    code.extend(create_display_code("ALL TESTS PASSED", line=current_line, color=COLOR_GREEN))
    code.extend(create_display_code("TYPE 4 SUPPORTED: PASS", line=current_line + 1, color=COLOR_GREEN))
    code.extend([JMP_ABSOLUTE_0x4C, 0x00, 0x00])  # JMP to loop (placeholder)
    loop_jmp = len(code) - 2

    # Show fail - red border
    show_fail_addr = len(code)
    code[show_fail_jmp] = (code_base + show_fail_addr) & 0xFF
    code[show_fail_jmp + 1] = ((code_base + show_fail_addr) >> 8) & 0xFF

    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_RED,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # Border red
        # Background stays black for text visibility
    ])
    code.extend(create_display_code("VERIFICATION FAILED", line=current_line, color=COLOR_FAIL))
    code.extend(create_display_code("TYPE 4 SUPPORTED: FAIL", line=current_line + 1, color=COLOR_FAIL))

    # Mark tests complete (set bit 7, preserve failure count)
    loop_addr = len(code)
    code[loop_jmp] = (code_base + loop_addr) & 0xFF
    code[loop_jmp + 1] = ((code_base + loop_addr) >> 8) & 0xFF
    code.extend(emit_mark_tests_complete())

    # Infinite loop
    inf_loop_addr = len(code)
    code.extend([JMP_ABSOLUTE_0x4C, (code_base + inf_loop_addr) & 0xFF, ((code_base + inf_loop_addr) >> 8) & 0xFF])

    # Copy code into ROML
    for i, byte in enumerate(code):
        roml[0x0009 + i] = byte

    desc = "Type 4 verification" if not is_error_cart else "Type 4 error cart"
    return bytes(roml), bytes(romh), desc


def write_ocean_type1_crt(path: Path, banks: list[bytes], name: str = "TEST") -> None:
    """Write an Ocean Type 1 CRT file with multiple banks.

    Args:
        path: Output file path
        banks: List of 8KB ROM banks
        name: Cartridge name
    """
    # CRT Header (64 bytes)
    header = bytearray(64)
    header[0:16] = b'C64 CARTRIDGE   '
    header[0x10:0x14] = (64).to_bytes(4, 'big')  # Header length
    header[0x14] = 1  # Version hi
    header[0x15] = 0  # Version lo
    header[0x16:0x18] = (5).to_bytes(2, 'big')  # Hardware type 5 = Ocean Type 1
    header[0x18] = 0  # EXROM = 0 (active)
    header[0x19] = 1  # GAME = 1 (inactive) -> 8KB mode (typical for Ocean)
    name_bytes = name.encode('ascii')[:32].ljust(32, b'\x00')
    header[0x20:0x40] = name_bytes

    with open(path, 'wb') as f:
        f.write(bytes(header))

        # Write each bank as a CHIP packet
        for bank_num, bank_data in enumerate(banks):
            chip = bytearray(16)
            chip[0:4] = b'CHIP'
            chip[4:8] = (16 + len(bank_data)).to_bytes(4, 'big')
            chip[8:10] = (0).to_bytes(2, 'big')  # Type (0 = ROM)
            chip[10:12] = bank_num.to_bytes(2, 'big')  # Bank number
            chip[12:14] = (C64.ROML_START).to_bytes(2, 'big')  # Load address $8000
            chip[14:16] = (len(bank_data)).to_bytes(2, 'big')
            f.write(bytes(chip))
            f.write(bank_data)


def create_type5_test_cart(is_error_cart: bool = False, num_banks: int = 8) -> tuple[list[bytes], str]:
    """Create Type 5 (Ocean Type 1) test cartridge with bank switching tests.

    Ocean Type 1 uses simple bank selection via $DE00 (bits 0-5).
    We test bank switching by:
    1. Copying a bank test routine to RAM
    2. For each bank, switch and verify the signature

    Args:
        is_error_cart: If True, this is for error/regression testing
        num_banks: Number of 8KB banks to create (default 8 for 64KB)

    Returns:
        Tuple of (list of bank bytes, description)
    """
    cart = bytearray(C64.ROML_SIZE)

    # Cartridge header at $8000-$8008
    cart[0x0000] = 0x09  # Cold start lo -> $8009
    cart[0x0001] = 0x80  # Cold start hi
    cart[0x0002] = 0x09  # Warm start lo -> $8009
    cart[0x0003] = 0x80  # Warm start hi
    cart[0x0004] = 0xC3  # 'C' (CBM80 signature)
    cart[0x0005] = 0xC2  # 'B'
    cart[0x0006] = 0xCD  # 'M'
    cart[0x0007] = 0x38  # '8'
    cart[0x0008] = 0x30  # '0'

    code = []
    code_base = 0x8009

    # Initialize - disable interrupts, set up stack
    code.extend([
        SEI_IMPLIED_0x78,
        LDX_IMMEDIATE_0xA2, 0xFF,
        TXS_IMPLIED_0x9A,
    ])

    # Clear screen
    code.extend([
        LDA_IMMEDIATE_0xA9, 0x20,
        LDX_IMMEDIATE_0xA2, 0x00,
    ])
    code.extend([
        STA_ABSOLUTE_X_0x9D, 0x00, 0x04,
        STA_ABSOLUTE_X_0x9D, 0x00, 0x05,
        STA_ABSOLUTE_X_0x9D, 0x00, 0x06,
        STA_ABSOLUTE_X_0x9D, 0x00, 0x07,
        INX_IMPLIED_0xE8,
        BNE_RELATIVE_0xD0, 0xF1,
    ])

    # Initialize fail counter
    code.extend(emit_init_fail_counter())

    # Set border/background to black
    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_BLACK,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,
        STA_ABSOLUTE_0x8D, 0x21, 0xD0,
    ])

    # Display title and type info
    title = "TYPE 5 ERROR CART" if is_error_cart else "TYPE 5 VERIFY"
    code.extend(create_display_code(title, line=0, color=COLOR_WHITE))
    code.extend(create_display_code("TYPE: 5", line=1, color=COLOR_YELLOW))
    code.extend(create_display_code("NAME: OCEAN TYPE 1", line=2, color=COLOR_YELLOW))

    current_line = 4

    # === Bank Test Routine in RAM ===
    # We'll copy a small routine to $C000 (free RAM area) that:
    # 1. Switches to the requested bank (bank number in A)
    # 2. Reads signature byte at $9FF5
    # 3. Switches back to bank 0
    # 4. Returns with signature byte in A
    #
    # Ocean bank selection: Write bank number directly to $DE00 (bits 0-5)
    # RAM routine at $C000:
    #   STA $DE00       ; $8D $00 $DE - switch bank (A = bank number)
    #   LDA $9FF5       ; $AD $F5 $9F - read signature
    #   PHA             ; $48 - save result
    #   LDA #$00        ; $A9 $00 - bank 0
    #   STA $DE00       ; $8D $00 $DE - switch back
    #   PLA             ; $68 - restore result
    #   RTS             ; $60

    ram_routine = [
        0x8D, 0x00, 0xDE,  # STA $DE00 (A already has bank number)
        0xAD, 0xF5, 0x9F,  # LDA $9FF5
        0x48,              # PHA
        0xA9, 0x00,        # LDA #$00
        0x8D, 0x00, 0xDE,  # STA $DE00
        0x68,              # PLA
        0x60,              # RTS
    ]

    # Copy RAM routine to $C000
    for i, byte in enumerate(ram_routine):
        code.extend([
            LDA_IMMEDIATE_0xA9, byte,
            STA_ABSOLUTE_0x8D, (0xC000 + i) & 0xFF, (0xC000 + i) >> 8,
        ])

    # Helper function to emit a test with FAIL-first pattern
    def emit_test(test_name, line, test_code_emitter):
        """Emit test code with FAIL displayed first, updated to PASS on success."""
        nonlocal code

        # Calculate screen positions
        result_screen = 0x0400 + (line * 40) + 35
        result_color = 0xD800 + (line * 40) + 35

        # 1. Display test name with FAIL
        code.extend(create_display_code(test_name, line=line, color=COLOR_LIGHT_GRAY))
        for i, ch in enumerate([0x06, 0x01, 0x09, 0x0C]):  # FAIL
            code.extend([
                LDA_IMMEDIATE_0xA9, ch,
                STA_ABSOLUTE_0x8D, (result_screen + i) & 0xFF, (result_screen + i) >> 8,
                LDA_IMMEDIATE_0xA9, COLOR_FAIL,
                STA_ABSOLUTE_0x8D, (result_color + i) & 0xFF, (result_color + i) >> 8,
            ])

        # 2. Run the test - emitter adds test code and returns branch info
        pass_branch_idx, is_beq = test_code_emitter()

        # 3. If we get here without branching, test failed - increment counter and jump to next
        code.extend(emit_inc_fail_counter())
        code.extend([JMP_ABSOLUTE_0x4C, 0x00, 0x00])  # JMP to next test (placeholder)
        fail_done_jmp = len(code) - 2

        # 4. PASS label - overwrite FAIL with PASS
        pass_addr = len(code)
        # Fix up the branch to point here
        branch_offset = pass_addr - (pass_branch_idx + 1)
        if branch_offset < -128 or branch_offset > 127:
            raise ValueError(f"Branch offset {branch_offset} out of range")
        code[pass_branch_idx] = branch_offset & 0xFF

        for i, ch in enumerate([0x10, 0x01, 0x13, 0x13]):  # PASS
            code.extend([
                LDA_IMMEDIATE_0xA9, ch,
                STA_ABSOLUTE_0x8D, (result_screen + i) & 0xFF, (result_screen + i) >> 8,
                LDA_IMMEDIATE_0xA9, COLOR_PASS,
                STA_ABSOLUTE_0x8D, (result_color + i) & 0xFF, (result_color + i) >> 8,
            ])

        # 5. Next test label - fix up fail jump
        next_addr = len(code)
        code[fail_done_jmp] = (code_base + next_addr) & 0xFF
        code[fail_done_jmp + 1] = ((code_base + next_addr) >> 8) & 0xFF

    # Test each bank
    for bank_num in range(num_banks):
        expected_sig = bank_num  # Each bank has its number at $9FF5

        def bank_test(bn=bank_num, sig=expected_sig):
            # Load bank number and call RAM routine
            code.extend([
                LDA_IMMEDIATE_0xA9, bn,
                JSR_ABSOLUTE_0x20, 0x00, 0xC0,  # JSR $C000
                CMP_IMMEDIATE_0xC9, sig,         # Compare to expected signature
                BEQ_RELATIVE_0xF0, 0x00,         # BEQ to pass (placeholder)
            ])
            return len(code) - 1, True

        emit_test(f"BANK {bank_num}", current_line, bank_test)
        current_line += 1

    current_line += 1  # Skip a line before final status

    # === Final status ===
    # Check fail counter
    code.extend(emit_load_fail_counter())
    code.extend([
        BEQ_RELATIVE_0xF0, 0x03,  # BEQ +3 (skip JMP) - no failures
        JMP_ABSOLUTE_0x4C, 0x00, 0x00,  # JMP to show_fail (placeholder)
    ])
    show_fail_jmp = len(code) - 2

    # All passed - green border (keep black background for text visibility)
    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_GREEN,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # Border green
        # Background stays black for text visibility
    ])
    code.extend(create_display_code("ALL TESTS PASSED", line=current_line, color=COLOR_GREEN))
    code.extend(create_display_code("TYPE 5 SUPPORTED: PASS", line=current_line + 1, color=COLOR_GREEN))
    code.extend([JMP_ABSOLUTE_0x4C, 0x00, 0x00])  # JMP to loop (placeholder)
    loop_jmp = len(code) - 2

    # Show fail - red border
    show_fail_addr = len(code)
    code[show_fail_jmp] = (code_base + show_fail_addr) & 0xFF
    code[show_fail_jmp + 1] = ((code_base + show_fail_addr) >> 8) & 0xFF

    code.extend([
        LDA_IMMEDIATE_0xA9, COLOR_RED,
        STA_ABSOLUTE_0x8D, 0x20, 0xD0,  # Border red
        # Background stays black for text visibility
    ])
    code.extend(create_display_code("VERIFICATION FAILED", line=current_line, color=COLOR_FAIL))
    code.extend(create_display_code("TYPE 5 SUPPORTED: FAIL", line=current_line + 1, color=COLOR_FAIL))

    # Mark tests complete (set bit 7, preserve failure count)
    loop_addr = len(code)
    code[loop_jmp] = (code_base + loop_addr) & 0xFF
    code[loop_jmp + 1] = ((code_base + loop_addr) >> 8) & 0xFF
    code.extend(emit_mark_tests_complete())

    # Infinite loop
    inf_loop_addr = len(code)
    code.extend([JMP_ABSOLUTE_0x4C, (code_base + inf_loop_addr) & 0xFF, ((code_base + inf_loop_addr) >> 8) & 0xFF])

    # Copy code into cartridge
    for i, byte in enumerate(code):
        cart[0x0009 + i] = byte

    # Add signature to bank 0 (bank number as signature byte)
    sig_offset = 0x1FF5
    cart[sig_offset] = 0x00  # Bank 0 signature

    # Create remaining banks with their signatures
    banks = [bytes(cart)]
    for bank_num in range(1, num_banks):
        bank = bytearray(C64.ROML_SIZE)
        bank[sig_offset] = bank_num  # Bank signature = bank number
        banks.append(bytes(bank))

    desc = f"Type 5 verification ({num_banks} banks)" if not is_error_cart else f"Type 5 error cart ({num_banks} banks)"
    return banks, desc


def main():
    fixtures_dir = project_root / "tests" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Create C64-specific fixtures directory structure
    c64_fixtures_dir = fixtures_dir / "c64"
    c64_fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Create cartridge_types directory for all cartridge test fixtures
    cartridge_types_dir = c64_fixtures_dir / "cartridge_types"
    cartridge_types_dir.mkdir(parents=True, exist_ok=True)

    # Create error cartridges for all hardware types
    # These run the same tests as pass carts - used for regression testing
    # Error carts are runtime resources, so they live in the c64 package
    # All error carts are .bin files (raw ROM data)
    # NOTE: Error cartridges are now generated dynamically at runtime,
    # so pre-built files are no longer needed. This code is kept for reference.
    if GENERATE_ERROR_CARTS:
        print("\nCreating error cartridges...")
        error_cart_dir = project_root / "systems" / "c64" / "cartridges" / "error_cartridges"
        error_cart_dir.mkdir(parents=True, exist_ok=True)

        # Type 0 needs separate error carts for each mode
        print("  Type 0 - 8KB mode error cart...")
        roml_err_8k, desc = create_type0_8k_test_cart(is_error_cart=True)
        path = error_cart_dir / "error_cart_type_00_8k.bin"
        write_raw_cartridge(path, roml_err_8k)
        print(f"    {path.name}")

        print("  Type 0 - 16KB mode error cart...")
        roml_err_16k, romh_err_16k, desc = create_type0_16k_test_cart(is_error_cart=True)
        path = error_cart_dir / "error_cart_type_00_16k.bin"
        write_raw_cartridge(path, roml_err_16k, romh_err_16k)
        print(f"    {path.name}")

        print("  Type 0 - Ultimax mode error cart...")
        ultimax_err, _, desc = create_type0_ultimax_test_cart(is_error_cart=True, include_roml=False)
        path = error_cart_dir / "error_cart_type_00_ultimax.bin"
        write_raw_cartridge(path, ultimax_err)
        print(f"    {path.name}")

        print("  Type 0 - Ultimax+ROML mode error cart...")
        ultimax_err_roml, roml_err, desc = create_type0_ultimax_test_cart(is_error_cart=True, include_roml=True)
        path = error_cart_dir / "error_cart_type_00_ultimax_with_roml.bin"
        # For .bin, write ROML first then ROMH (ROML at $8000, ROMH at $E000)
        with open(path, 'wb') as f:
            f.write(roml_err)
            f.write(ultimax_err_roml)
        print(f"    {path.name}")

        # Type 1: Action Replay error cart
        print("  Type 1 - Action Replay error cart...")
        banks_err, desc = create_type1_test_cart(is_error_cart=True)
        path = error_cart_dir / "error_cart_type_01_action_replay.bin"
        with open(path, 'wb') as f:
            for bank in banks_err:
                f.write(bank)
        print(f"    {path.name}")

        # Type 4: Simons' BASIC error cart
        print("  Type 4 - Simons' BASIC error cart...")
        roml_err_v4, romh_err_v4, desc = create_type4_test_cart(is_error_cart=True)
        path = error_cart_dir / "error_cart_type_04_simons_basic.bin"
        with open(path, 'wb') as f:
            f.write(roml_err_v4)
            f.write(romh_err_v4)
        print(f"    {path.name}")

        # Type 5: Ocean Type 1 error cart
        print("  Type 5 - Ocean Type 1 error cart...")
        banks_err_v5, desc = create_type5_test_cart(is_error_cart=True, num_banks=8)
        path = error_cart_dir / "error_cart_type_05_ocean_type_1.bin"
        with open(path, 'wb') as f:
            for bank in banks_err_v5:
                f.write(bank)
        print(f"    {path.name}")

        # Generate generic error carts for all types (for regression testing)
        # Error carts are raw .bin files (runtime resources, not test fixtures)
        # Note: At runtime, unsupported types also get dynamic error carts with
        # test results - see CartridgeTestResults in c64/cartridges/__init__.py
        for hw_type, type_name in sorted(C64.CRT_HARDWARE_TYPES.items()):
            error_rom = create_error_cartridge(hw_type, type_name)
            safe_name = type_name.lower().replace(" ", "_").replace(",", "").replace("/", "_")
            path = error_cart_dir / f"error_cart_type_{hw_type:02d}_{safe_name}.bin"
            write_raw_cartridge(path, error_rom)
            print(f"  Type {hw_type:2d}: {path.name}")

        print(f"\n  Created error cartridges in {error_cart_dir}")
    else:
        print("\nSkipping error cartridge generation (GENERATE_ERROR_CARTS=False)")
        print("  Error cartridges are generated dynamically at runtime.")

    # Create test CRT files for each mapper type in tests/fixtures/c64/cartridge_types/
    # All cartridge test files go here - both supported and unsupported types
    # (cartridge_types_dir was already created above)
    print("\nCreating test cartridges for all hardware types...")

    # For supported types (0, 1), create proper test carts with self-tests
    # For unsupported types, create simple info display carts

    # Type 0 - 8KB mode: EXROM=0, GAME=1
    print("  Type 0 - 8KB mode (EXROM=0, GAME=1)...")
    roml_8k, desc_8k = create_type0_8k_test_cart(is_error_cart=False)
    path_8k_crt = cartridge_types_dir / "test_cart_type_00_8k.crt"
    write_crt_cartridge(path_8k_crt, roml_8k, romh=None, name="TYPE 0 8K TEST", exrom=0, game=1)
    path_8k_bin = cartridge_types_dir / "test_cart_type_00_8k.bin"
    write_raw_cartridge(path_8k_bin, roml_8k)
    print(f"    {path_8k_crt.name} + .bin ({desc_8k})")

    # Type 0 - 16KB mode: EXROM=0, GAME=0
    print("  Type 0 - 16KB mode (EXROM=0, GAME=0)...")
    roml_16k, romh_16k, desc_16k = create_type0_16k_test_cart(is_error_cart=False)
    path_16k_crt = cartridge_types_dir / "test_cart_type_00_16k.crt"
    write_crt_cartridge(path_16k_crt, roml_16k, romh_16k, name="TYPE 0 16K TEST", exrom=0, game=0)
    path_16k_bin = cartridge_types_dir / "test_cart_type_00_16k.bin"
    write_raw_cartridge(path_16k_bin, roml_16k, romh_16k)
    print(f"    {path_16k_crt.name} + .bin ({desc_16k})")

    # Type 0 - 16KB mode with single CHIP packet (like Q*bert and many real carts)
    # Same ROM data but stored as one 16KB chunk at $8000 instead of two 8KB CHIPs
    print("  Type 0 - 16KB single CHIP format...")
    path_16k_single_crt = cartridge_types_dir / "test_cart_type_00_16k_single_chip.crt"
    write_crt_cartridge(
        path_16k_single_crt, roml_16k, romh_16k,
        name="TYPE 0 16K SINGLECHIP", exrom=0, game=0, single_chip=True
    )
    print(f"    {path_16k_single_crt.name} (CRT format variant, same ROM as 16k)")

    # Type 0 - Ultimax mode: EXROM=1, GAME=0 (ROMH only)
    print("  Type 0 - Ultimax mode (EXROM=1, GAME=0)...")
    ultimax_rom, _, desc_ultimax = create_type0_ultimax_test_cart(is_error_cart=False, include_roml=False)
    path_ultimax_crt = cartridge_types_dir / "test_cart_type_00_ultimax.crt"
    write_ultimax_crt_cartridge(path_ultimax_crt, ultimax_rom, name="TYPE 0 ULTIMAX TEST")
    path_ultimax_bin = cartridge_types_dir / "test_cart_type_00_ultimax.bin"
    write_raw_cartridge(path_ultimax_bin, ultimax_rom)
    print(f"    {path_ultimax_crt.name} + .bin ({desc_ultimax})")

    # Type 0 - Ultimax mode with optional ROML: EXROM=1, GAME=0 (ROMH + ROML)
    print("  Type 0 - Ultimax+ROML mode (EXROM=1, GAME=0, with ROML)...")
    ultimax_rom_roml, roml_data, desc_ultimax_roml = create_type0_ultimax_test_cart(is_error_cart=False, include_roml=True)
    path_ultimax_roml_crt = cartridge_types_dir / "test_cart_type_00_ultimax_with_roml.crt"
    write_ultimax_crt_cartridge(path_ultimax_roml_crt, ultimax_rom_roml, roml=roml_data, name="TYPE 0 ULTIMAX+ROML")
    path_ultimax_roml_bin = cartridge_types_dir / "test_cart_type_00_ultimax_with_roml.bin"
    # For .bin, write ROML first then ROMH (ROML at $8000, ROMH at $E000)
    with open(path_ultimax_roml_bin, 'wb') as f:
        f.write(roml_data)
        f.write(ultimax_rom_roml)
    print(f"    {path_ultimax_roml_crt.name} + .bin ({desc_ultimax_roml})")

    # Type 1: Action Replay test cart (CRT only, no .bin for types > 0)
    print("  Type 1 - Action Replay...")
    banks_v1, desc_v1 = create_type1_test_cart(is_error_cart=False)
    path_v1_crt = cartridge_types_dir / "test_cart_type_01_action_replay.crt"
    write_action_replay_crt(path_v1_crt, banks_v1, name="TYPE 1 TEST")
    print(f"    {path_v1_crt.name} ({desc_v1})")

    # Type 4: Simons' BASIC test cart
    print("  Type 4 - Simons' BASIC...")
    roml_v4, romh_v4, desc_v4 = create_type4_test_cart(is_error_cart=False)
    path_v4_crt = cartridge_types_dir / "test_cart_type_04_simons_basic.crt"
    write_simons_basic_crt(path_v4_crt, roml_v4, romh_v4, name="TYPE 4 TEST")
    print(f"    {path_v4_crt.name} ({desc_v4})")

    # Type 5: Ocean Type 1 test cart
    print("  Type 5 - Ocean Type 1...")
    banks_v5, desc_v5 = create_type5_test_cart(is_error_cart=False, num_banks=8)
    path_v5_crt = cartridge_types_dir / "test_cart_type_05_ocean_type_1.crt"
    write_ocean_type1_crt(path_v5_crt, banks_v5, name="TYPE 5 TEST")
    print(f"    {path_v5_crt.name} ({desc_v5})")

    # Unsupported types (2-85) - create simple info display carts
    for hw_type, type_name in sorted(C64.CRT_HARDWARE_TYPES.items()):
        if hw_type in CARTRIDGE_TYPES:
            continue  # Already handled above with proper test carts
        # Create a test ROM that displays the mapper type
        mapper_rom = create_mapper_test_cartridge(hw_type, type_name)
        safe_name = type_name.lower().replace(" ", "_").replace(",", "").replace("/", "_").replace("(", "").replace(")", "").replace(".", "")
        path = cartridge_types_dir / f"test_cart_type_{hw_type:02d}_{safe_name}.crt"
        write_crt_cartridge(path, mapper_rom, name=f"TYPE {hw_type} TEST", hardware_type=hw_type)
        print(f"  Type {hw_type:2d}: {path.name}")

    print(f"\n  Created test cartridges in {cartridge_types_dir}")

    print("\nDone! Test supported mapper carts (should show all PASS):")
    print(f"  poetry run c64 --cartridge {path_8k_crt}")
    print(f"  poetry run c64 --cartridge {path_16k_crt}")
    print(f"  poetry run c64 --cartridge {path_ultimax_crt}")
    print(f"  poetry run c64 --cartridge {path_v1_crt}")
    print(f"  poetry run c64 --cartridge {path_v4_crt}")
    print(f"  poetry run c64 --cartridge {path_v5_crt}")
    print(f"\nTest unsupported type (should show error cart with NO TESTS):")
    print(f"  poetry run c64 --cartridge {cartridge_types_dir}/test_cart_type_02_kcs_power_cartridge.crt")


if __name__ == '__main__':
    main()
