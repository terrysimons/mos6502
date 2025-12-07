"""Test ROM builder for generating 6502 test program code.

This module provides utilities for building test cartridge ROMs that:
- Display text on the C64 screen
- Perform memory verification tests
- Show PASS/FAIL results for each test
- Track failure counts

The TestROMBuilder class is used by cartridge classes to implement
their create_test_cartridge() methods.
"""

from __future__ import annotations

from .base import ROML_START, ROML_SIZE

# Import color constants from c64.colors
from c64.colors import (
    COLOR_BLACK,
    COLOR_WHITE,
    COLOR_RED,
    COLOR_CYAN,
    COLOR_PURPLE,
    COLOR_GREEN,
    COLOR_BLUE,
    COLOR_YELLOW,
    COLOR_ORANGE,
    COLOR_BROWN,
    COLOR_LIGHT_RED,
    COLOR_DARK_GRAY,
    COLOR_MEDIUM_GRAY,
    COLOR_LIGHT_GREEN,
    COLOR_LIGHT_BLUE,
    COLOR_LIGHT_GRAY,
)

# Import 6502 instruction opcodes
from mos6502.instructions import (
    # Load
    LDA_IMMEDIATE_0xA9,
    LDA_ZEROPAGE_0xA5,
    LDA_ABSOLUTE_0xAD,
    LDX_IMMEDIATE_0xA2,
    # Store
    STA_ZEROPAGE_0x85,
    STA_ABSOLUTE_0x8D,
    STA_ABSOLUTE_X_0x9D,
    # Arithmetic
    INC_ZEROPAGE_0xE6,
    INX_IMPLIED_0xE8,
    # Compare
    CMP_IMMEDIATE_0xC9,
    # Branch
    BNE_RELATIVE_0xD0,
    BEQ_RELATIVE_0xF0,
    # Jump/Subroutines
    JMP_ABSOLUTE_0x4C,
    JSR_ABSOLUTE_0x20,
    RTS_IMPLIED_0x60,
    # Stack
    TXS_IMPLIED_0x9A,
    PHA_IMPLIED_0x48,
    PLA_IMPLIED_0x68,
    # Flags
    SEI_IMPLIED_0x78,
    # Logic
    ORA_IMMEDIATE_0x09,
)


__all__ = [
    "TestROMBuilder",
    "text_to_screen_codes",
    "RAM_ROUTINE_ADDR",
]

# Semantic color aliases for test display
COLOR_PASS = COLOR_GREEN
COLOR_FAIL = COLOR_LIGHT_RED  # Light red so it's visible on red background
COLOR_TITLE = COLOR_WHITE
COLOR_INFO = COLOR_YELLOW
COLOR_TEST_NAME = COLOR_LIGHT_GRAY

# Zero-page location for fail counter
# Bits 0-6: failure count (0-127)
# Bit 7: tests complete flag
# Values: 0x00-0x7F = running, 0x80 = done/pass, 0x81-0xFF = done/fail
FAIL_COUNTER_ZP = 0x02

# Zero-page locations for peripheral test cartridges
# Test cartridges store hardware register values here for test framework verification
# These are arbitrary locations we chose - not real C64 hardware addresses
PERIPHERAL_TEST_ZP_X = 0x03       # X-axis value (POTX for mouse/paddle, LPX for lightpen)
PERIPHERAL_TEST_ZP_Y = 0x04       # Y-axis value (POTY for mouse/paddle, LPY for lightpen)
PERIPHERAL_TEST_ZP_BUTTONS = 0x05  # Button state (CIA joystick port bits)

# RAM address for bank-switch routine
# $C000 is free RAM on C64 (between BASIC and I/O area)
RAM_ROUTINE_ADDR = 0xC000


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


class TestROMBuilder:
    """Builder for test cartridge ROM code.

    Generates 6502 machine code that tests cartridge hardware and displays
    PASS/FAIL for each test. Used by cartridge classes to implement
    their create_test_cartridge() methods.

    Example usage:
        builder = TestROMBuilder(base_address=0x8000)
        builder.emit_screen_init()
        builder.emit_set_border_and_background(COLOR_BLUE)
        builder.emit_display_text("TEST TITLE", line=0, color=COLOR_WHITE)

        # Test a memory location
        test_id = builder.start_test("CHECK $8000")
        builder.emit_check_byte(0x8000, 0xC3, f"{test_id}_fail")
        builder.emit_pass_result(test_id)
        builder.emit_fail_result(test_id)

        builder.emit_final_status(hardware_type=0, type_name="NORMAL")
        rom_bytes = builder.build_rom()
    """

    # CBM80 cartridge header
    CBM80_HEADER = bytes([
        0x09, 0x80,  # Cold start -> $8009
        0x09, 0x80,  # Warm start -> $8009
        0xC3,        # 'C'
        0xC2,        # 'B'
        0xCD,        # 'M'
        0x38,        # '8'
        0x30,        # '0'
    ])

    def __init__(self, base_address: int = ROML_START):
        """Initialize the ROM builder.

        Args:
            base_address: Base address for ROM (0x8000 normal, 0xE000 ultimax)
        """
        self.base_address = base_address
        self.code = []
        self.code_offset = 0x0009  # Code starts after CBM80 header
        self.current_line = 0
        self.test_count = 0
        self.branches_to_fix = []  # (code_index, target_label)
        self.jumps_to_fix = []     # (code_index, target_label)
        self.labels = {}           # label_name -> address

    def _addr(self, code_index: int) -> int:
        """Convert code index to absolute address."""
        return self.base_address + self.code_offset + code_index

    def _current_addr(self) -> int:
        """Get current code address."""
        return self._addr(len(self.code))

    def label(self, name: str) -> None:
        """Define a label at current position."""
        self.labels[name] = self._current_addr()

    def emit_screen_init(self) -> None:
        """Emit initialization code: SEI, set stack, clear screen, init fail counter."""
        # Disable interrupts, set up stack
        self.code.extend([
            SEI_IMPLIED_0x78,
            LDX_IMMEDIATE_0xA2, 0xFF,
            TXS_IMPLIED_0x9A,
        ])

        # Clear screen with spaces
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
        self.code.extend([
            LDA_IMMEDIATE_0xA9, 0x00,
            STA_ZEROPAGE_0x85, FAIL_COUNTER_ZP,
        ])

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

    def emit_display_text(
        self, text: str, line: int, color: int = COLOR_WHITE, centered: bool = True
    ) -> None:
        """Display text on screen.

        Args:
            text: Text to display (max 40 chars)
            line: Screen line (0-24)
            color: Color value (0-15)
            centered: If True, center the text on the line
        """
        screen_codes = text_to_screen_codes(text)
        if centered:
            start_pos = (40 - len(text)) // 2
        else:
            start_pos = 0
        screen_addr = 0x0400 + (line * 40) + start_pos
        color_addr = 0xD800 + (line * 40) + start_pos

        # Write each character and its color
        for i, sc in enumerate(screen_codes):
            self.code.extend([
                LDA_IMMEDIATE_0xA9, sc,
                STA_ABSOLUTE_0x8D, (screen_addr + i) & 0xFF, (screen_addr + i) >> 8,
            ])
            self.code.extend([
                LDA_IMMEDIATE_0xA9, color,
                STA_ABSOLUTE_0x8D, (color_addr + i) & 0xFF, (color_addr + i) >> 8,
            ])

    def start_test(self, test_name: str) -> str:
        """Start a test - displays test name, returns test ID for pass/fail.

        Args:
            test_name: Description of the test

        Returns:
            Test ID string for use with emit_pass_result/emit_fail_result
        """
        self.test_count += 1
        test_id = f"test_{self.test_count}"

        # Display test name (leave room for PASS/FAIL at end)
        display_name = test_name[:30]
        screen_codes = text_to_screen_codes(display_name)
        screen_addr = 0x0400 + (self.current_line * 40)
        color_addr = 0xD800 + (self.current_line * 40)

        for i, sc in enumerate(screen_codes):
            self.code.extend([
                LDA_IMMEDIATE_0xA9, sc,
                STA_ABSOLUTE_0x8D, (screen_addr + i) & 0xFF, (screen_addr + i) >> 8,
            ])
            self.code.extend([
                LDA_IMMEDIATE_0xA9, COLOR_LIGHT_GRAY,
                STA_ABSOLUTE_0x8D, (color_addr + i) & 0xFF, (color_addr + i) >> 8,
            ])

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

    def emit_check_byte_not_equal(self, addr: int, unexpected: int, fail_label: str) -> None:
        """Emit code to check a byte at addr does NOT equal unexpected value.

        Branches to fail_label if the values ARE equal.
        """
        self.code.extend([
            LDA_ABSOLUTE_0xAD, addr & 0xFF, (addr >> 8) & 0xFF,
            CMP_IMMEDIATE_0xC9, unexpected,
            BEQ_RELATIVE_0xF0,  # Branch if equal (that's a failure)
        ])
        self.branches_to_fix.append((len(self.code), fail_label))
        self.code.append(0x00)  # Placeholder

    def emit_write_byte(self, addr: int, value: int) -> None:
        """Emit code to write a byte."""
        self.code.extend([
            LDA_IMMEDIATE_0xA9, value,
            STA_ABSOLUTE_0x8D, addr & 0xFF, (addr >> 8) & 0xFF,
        ])

    def emit_install_bank_switch_routine(
        self,
        bank_select_addr: int,
        signature_addr: int,
        ram_addr: int = RAM_ROUTINE_ADDR,
    ) -> None:
        """Emit code to copy a bank-switch routine to RAM.

        The RAM routine will:
        1. Switch to the bank number passed in A register
        2. Read signature byte from signature_addr
        3. Switch back to bank 0
        4. Return with the signature byte in A

        This is needed because bank-switching cartridges swap out the ROM
        while executing from it. By running the switch from RAM, we avoid
        executing from a bank that gets swapped out.

        Args:
            bank_select_addr: Address to write bank number (e.g., $DE00 for Ocean)
            signature_addr: Address to read signature from (e.g., $9FF5)
            ram_addr: RAM address to install routine (default $C000)
        """
        # The RAM routine:
        #   STA bank_select_addr   ; Switch to bank (A = bank number)
        #   LDA signature_addr     ; Read signature
        #   PHA                    ; Save signature
        #   LDA #$00               ; Bank 0
        #   STA bank_select_addr   ; Switch back
        #   PLA                    ; Restore signature
        #   RTS
        ram_routine = [
            STA_ABSOLUTE_0x8D, bank_select_addr & 0xFF, (bank_select_addr >> 8) & 0xFF,
            LDA_ABSOLUTE_0xAD, signature_addr & 0xFF, (signature_addr >> 8) & 0xFF,
            PHA_IMPLIED_0x48,
            LDA_IMMEDIATE_0xA9, 0x00,
            STA_ABSOLUTE_0x8D, bank_select_addr & 0xFF, (bank_select_addr >> 8) & 0xFF,
            PLA_IMPLIED_0x68,
            RTS_IMPLIED_0x60,
        ]

        # Copy the routine to RAM byte by byte
        for i, byte in enumerate(ram_routine):
            self.code.extend([
                LDA_IMMEDIATE_0xA9, byte,
                STA_ABSOLUTE_0x8D, (ram_addr + i) & 0xFF, (ram_addr + i) >> 8,
            ])

        # Store the RAM routine address for later use
        self._ram_routine_addr = ram_addr

    def emit_call_bank_switch(self, bank_num: int) -> None:
        """Emit code to switch to a bank and return signature in A.

        Must call emit_install_bank_switch_routine first!

        Args:
            bank_num: Bank number to switch to
        """
        if not hasattr(self, '_ram_routine_addr'):
            raise RuntimeError("Must call emit_install_bank_switch_routine first")

        self.code.extend([
            LDA_IMMEDIATE_0xA9, bank_num,
            JSR_ABSOLUTE_0x20,
            self._ram_routine_addr & 0xFF,
            (self._ram_routine_addr >> 8) & 0xFF,
        ])

    def emit_check_a_equals(self, expected: int, fail_label: str) -> None:
        """Emit code to check if A register equals expected value.

        Branches to fail_label if A != expected.

        Args:
            expected: Expected value in A
            fail_label: Label to branch to on failure
        """
        self.code.extend([
            CMP_IMMEDIATE_0xC9, expected,
            BNE_RELATIVE_0xD0,
        ])
        self.branches_to_fix.append((len(self.code), fail_label))
        self.code.append(0x00)  # Placeholder

    def emit_bytes(self, bytes_list: list[int]) -> None:
        """Emit raw bytes directly into the code stream.

        Args:
            bytes_list: List of byte values (0-255) to emit
        """
        self.code.extend(bytes_list)

    def emit_pass_result(self, test_id: str) -> None:
        """Emit PASS result for current test and jump to done label."""
        # Display "PASS" in green at position 35 on current line
        pass_pos = 35
        screen_addr = 0x0400 + (self.current_line * 40) + pass_pos
        color_addr = 0xD800 + (self.current_line * 40) + pass_pos

        # Write "PASS" - P A S S in screen codes
        for i, ch in enumerate([0x10, 0x01, 0x13, 0x13]):
            self.code.extend([
                LDA_IMMEDIATE_0xA9, ch,
                STA_ABSOLUTE_0x8D, (screen_addr + i) & 0xFF, (screen_addr + i) >> 8,
                LDA_IMMEDIATE_0xA9, COLOR_PASS,
                STA_ABSOLUTE_0x8D, (color_addr + i) & 0xFF, (color_addr + i) >> 8,
            ])

        # Jump to done
        self.code.append(JMP_ABSOLUTE_0x4C)
        self.jumps_to_fix.append((len(self.code), f"{test_id}_done"))
        self.code.extend([0x00, 0x00])

    def emit_fail_result(self, test_id: str) -> None:
        """Emit FAIL result for current test."""
        self.label(f"{test_id}_fail")

        # Increment fail counter
        self.code.extend([INC_ZEROPAGE_0xE6, FAIL_COUNTER_ZP])

        # Display "FAIL" in light red at position 35 on current line
        fail_pos = 35
        screen_addr = 0x0400 + (self.current_line * 40) + fail_pos
        color_addr = 0xD800 + (self.current_line * 40) + fail_pos

        # Write "FAIL" - F A I L in screen codes
        for i, ch in enumerate([0x06, 0x01, 0x09, 0x0C]):
            self.code.extend([
                LDA_IMMEDIATE_0xA9, ch,
                STA_ABSOLUTE_0x8D, (screen_addr + i) & 0xFF, (screen_addr + i) >> 8,
                LDA_IMMEDIATE_0xA9, COLOR_FAIL,
                STA_ABSOLUTE_0x8D, (color_addr + i) & 0xFF, (color_addr + i) >> 8,
            ])

        self.label(f"{test_id}_done")
        self.current_line += 1

    def emit_final_status(self, hardware_type: int, type_name: str) -> None:
        """Emit code to check fail counter and set final border color.

        Sets bit 7 of fail counter ($02) to indicate tests are complete:
        - 0x80 = tests done, 0 failures (success)
        - 0x81-0xFF = tests done, 1-127 failures
        """
        self.current_line += 1  # Skip a line

        # Check fail counter
        self.code.extend([LDA_ZEROPAGE_0xA5, FAIL_COUNTER_ZP])
        self.code.extend([
            BEQ_RELATIVE_0xF0, 0x03,  # BEQ +3 (skip the JMP if zero/pass)
            JMP_ABSOLUTE_0x4C,
        ])
        self.jumps_to_fix.append((len(self.code), "show_fail"))
        self.code.extend([0x00, 0x00])

        # All passed - green border
        self.emit_set_border(COLOR_GREEN)
        self.emit_display_text("ALL TESTS PASSED", line=self.current_line, color=COLOR_GREEN)
        pass_msg = f"TYPE {hardware_type} SUPPORTED: PASS"
        self.emit_display_text(pass_msg, line=self.current_line + 1, color=COLOR_GREEN)
        self.code.append(JMP_ABSOLUTE_0x4C)
        self.jumps_to_fix.append((len(self.code), "loop"))
        self.code.extend([0x00, 0x00])

        # Some failures - red border
        self.label("show_fail")
        self.emit_set_border(COLOR_RED)
        self.emit_display_text("VERIFICATION FAILED", line=self.current_line, color=COLOR_FAIL)
        fail_msg = f"TYPE {hardware_type} SUPPORTED: FAIL"
        self.emit_display_text(fail_msg, line=self.current_line + 1, color=COLOR_FAIL)

        # Mark tests complete (set bit 7, preserve failure count)
        self.label("loop")
        self.code.extend([
            LDA_ZEROPAGE_0xA5, FAIL_COUNTER_ZP,  # Load fail counter
            ORA_IMMEDIATE_0x09, 0x80,             # Set bit 7 (tests complete)
            STA_ZEROPAGE_0x85, FAIL_COUNTER_ZP,   # Store back
        ])

        # Infinite loop
        loop_addr = self._current_addr()
        self.code.extend([
            JMP_ABSOLUTE_0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF,
        ])

    def emit_infinite_loop(self) -> None:
        """Emit an infinite loop at current position."""
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

    def build_rom(self, size: int = ROML_SIZE) -> bytes:
        """Build final ROM bytes.

        Args:
            size: ROM size in bytes (default 8KB)

        Returns:
            ROM bytes with CBM80 header and code
        """
        self.fixup_branches()

        rom = bytearray(size)

        # CBM80 header
        rom[0:len(self.CBM80_HEADER)] = self.CBM80_HEADER

        # Copy code
        for i, byte in enumerate(self.code):
            if self.code_offset + i < size:
                rom[self.code_offset + i] = byte

        return bytes(rom)

    def add_signature(self, rom: bytearray, offset: int, signature: str) -> None:
        """Add a signature string at a specific offset in the ROM.

        Args:
            rom: ROM bytearray to modify
            offset: Offset in ROM to place signature
            signature: ASCII string to write
        """
        for i, ch in enumerate(signature.encode('ascii')):
            if offset + i < len(rom):
                rom[offset + i] = ch
