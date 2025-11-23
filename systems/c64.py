#!/usr/bin/env python3
"""Commodore 64 Emulator using the mos6502 CPU package."""

import logging
import sys
from pathlib import Path
from typing import Optional

from mos6502 import CPU, CPUVariant, errors
from mos6502.core import INFINITE_CYCLES
from mos6502.memory import Byte, Word

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("c64")
COLORS = [
    (0x00, 0x00, 0x00),   # 0  Black
    (0xFF, 0xFF, 0xFF),   # 1  White
    (0x68, 0x37, 0x2B),   # 2  Red
    (0x70, 0xA4, 0xB2),   # 3  Cyan
    (0x6F, 0x3D, 0x86),   # 4  Purple
    (0x58, 0x8D, 0x43),   # 5  Green
    (0x35, 0x28, 0x79),   # 6  Blue
    (0xB8, 0xC7, 0x6F),   # 7  Yellow
    (0x6F, 0x4F, 0x25),   # 8  Orange
    (0x43, 0x39, 0x00),   # 9  Brown
    (0x9A, 0x67, 0x59),   # 10 Light red
    (0x44, 0x44, 0x44),   # 11 Dark gray
    (0x6C, 0x6C, 0x6C),   # 12 Medium gray
    (0x9A, 0xD2, 0x84),   # 13 Light green
    (0x6C, 0x5E, 0xB5),   # 14 Light blue
    (0x95, 0x95, 0x95),   # 15 Light gray
]

class C64:
    """Commodore 64 Emulator.

    Memory Map:
        $0000-$0001: I/O Ports (6510 specific - stubbed)
        $0002-$9FFF: RAM (40KB usable)
        $A000-$BFFF: BASIC ROM (8KB)
        $C000-$CFFF: RAM (4KB)
        $D000-$DFFF: I/O and Color RAM (4KB - stubbed)
        $E000-$FFFF: KERNAL ROM (8KB)
    """

    # Memory regions
    BASIC_ROM_START = 0xA000
    BASIC_ROM_END = 0xBFFF
    BASIC_ROM_SIZE = 0x2000  # 8KB

    KERNAL_ROM_START = 0xE000
    KERNAL_ROM_END = 0xFFFF
    KERNAL_ROM_SIZE = 0x2000  # 8KB

    CHAR_ROM_START = 0xD000
    CHAR_ROM_END = 0xDFFF
    CHAR_ROM_SIZE = 0x1000  # 4KB

    # I/O regions within $D000-$DFFF
    VIC_START = 0xD000
    VIC_END = 0xD3FF
    SID_START = 0xD400
    SID_END = 0xD7FF
    COLOR_RAM_START = 0xD800
    COLOR_RAM_END = 0xDBFF
    CIA1_START = 0xDC00
    CIA1_END = 0xDCFF
    CIA2_START = 0xDD00
    CIA2_END = 0xDDFF

    # C64 BASIC programs typically start here
    BASIC_PROGRAM_START = 0x0801

    # Reset vector location
    RESET_VECTOR_ADDR = 0xFFFC

    class CIA1:
        def __init__(self, cpu) -> None:
            # 16 registers, mirrored through $DC00–$DC0F
            self.regs = [0x00] * 16

            # Reference to CPU for IRQ signaling
            self.cpu = cpu

            # Keyboard matrix: 8 rows x 8 columns
            # keyboard_matrix[row] = byte where each bit is a column
            # 0 = key pressed (active low), 1 = key released
            self.keyboard_matrix = [0xFF] * 8

            # Joystick state (active low: 0 = pressed, 1 = released)
            # Port A bits 0-4 (when input): Joystick 2
            # Port B bits 0-4 (when input): Joystick 1
            # Bit 0: Up, Bit 1: Down, Bit 2: Left, Bit 3: Right, Bit 4: Fire
            self.joystick_1 = 0xFF  # All released (bits high)
            self.joystick_2 = 0xFF  # All released (bits high)

            # Port values
            self.port_a = 0xFF  # Columns (input)
            self.port_b = 0xFF  # Rows (output)

            # Data Direction Registers
            # 0 = input, 1 = output
            self.ddr_a = 0xFF   # Port A all outputs (row selection)
            self.ddr_b = 0x00   # Port B all inputs (column sensing)

            # Timer A state
            self.timer_a_counter = 0xFFFF  # 16-bit counter
            self.timer_a_latch = 0xFFFF    # 16-bit latch (reload value)
            self.timer_a_running = False

            # Timer B state
            self.timer_b_counter = 0xFFFF
            self.timer_b_latch = 0xFFFF
            self.timer_b_running = False

            # Interrupt state
            self.icr_data = 0x00      # Interrupt data (which interrupts occurred)
            self.icr_mask = 0x00      # Interrupt mask (which interrupts are enabled)

            # Track last CPU cycle count for timer updates
            self.last_cycle_count = 0

        def read(self, addr) -> int:
            reg = addr & 0x0F

            # Port A ($DC00) — keyboard matrix row selection (write) / joystick 2 (read)
            if reg == 0x00:
                # Start with all input row bits HIGH (pulled up externally)
                port_a_ext = 0xFF

                # For input row bits, check if any keys in that row are pressed
                # If a key is pressed in an input row, that row bit goes LOW
                for row in range(8):
                    row_is_input = not bool(self.ddr_a & (1 << row))
                    if row_is_input:
                        # Check if any key in this row is pressed
                        if self.keyboard_matrix[row] != 0xFF:  # Some key pressed in this row
                            port_a_ext &= ~(1 << row)  # Pull this row bit LOW
                            log.info(f"*** PORT A INPUT ROW: row={row} has key pressed, pulling Port A bit {row} LOW, matrix[{row}]=${self.keyboard_matrix[row]:02X} ***")

                # Reading Port A respects DDR:
                # - Output bits (ddr_a=1): return port_a value (software-controlled)
                # - Input bits (ddr_a=0): return keyboard/joystick state
                # For input bits, combine keyboard row detection with joystick 2
                # Joystick 2 only uses bits 0-4, bits 5-7 are keyboard-only
                joy2_with_float = (self.joystick_2 & 0x1F) | 0xE0  # Joystick on bits 0-4, bits 5-7 high
                ext_combined = port_a_ext & joy2_with_float  # Combine keyboard rows and joystick
                result = (self.port_a & self.ddr_a) | (ext_combined & ~self.ddr_a)
                return result

            # Port B ($DC01) — keyboard matrix column sensing (read) / joystick 1 (read)
            # This is where the keyboard magic happens!
            if reg == 0x01:
                # Start with keyboard matrix scan
                keyboard_ext = 0xFF

                # IMPORTANT: The C64 keyboard matrix is electrically bidirectional
                # Port A bits can be outputs (actively drive row selection) OR inputs (pulled high externally)
                #
                # DDRA bits: 1 = OUTPUT (software controlled), 0 = INPUT (pulled HIGH externally by pull-ups)
                #
                # When DDRA bit = 1 (OUTPUT):
                #   - port_a bit = 0: Row driven LOW (actively selects this row)
                #   - port_a bit = 1: Row driven HIGH (doesn't select this row)
                #
                # When DDRA bit = 0 (INPUT):
                #   - Row is pulled HIGH externally
                #   - Pressed keys can pull the row LOW through the keyboard matrix
                #   - The row line "floats" and keys can affect it
                #
                # This means ALL rows (both output and input) can have their keys detected!

                # For each row, check if it should participate in THIS Port B scan
                for row in range(8):
                    row_is_output = bool(self.ddr_a & (1 << row))
                    row_bit_low = not bool(self.port_a & (1 << row))

                    # CRITICAL FIX for input row detection:
                    # When Port A bit is LOW for an INPUT row, the KERNAL is trying to "select"
                    # that row even though it can't actually drive it. We should ONLY scan that
                    # specific input row, not all input rows!
                    #
                    # Row participates in Port B scanning if its Port A bit is LOW, regardless
                    # of whether it's an output or input. The key insight: the KERNAL writes
                    # specific bit patterns to Port A to select rows, and we should respect
                    # that selection even for input rows.
                    row_selected = row_bit_low  # Participate if Port A bit is LOW

                    if row_selected:
                        # For each column in this row
                        for col in range(8):
                            # Check if key at [row][col] is pressed
                            # keyboard_matrix[row] is a byte: 0 bit = pressed, 1 bit = released
                            if not (self.keyboard_matrix[row] & (1 << col)):  # Key is pressed (bit=0)
                                # Pressed key pulls that column line low
                                keyboard_ext &= ~(1 << col)

                                # Get key name for this matrix position
                                key_name = self._get_key_name(row, col)

                                if row_is_output:
                                    log.info(f"*** MATRIX: row={row}, col={col} ({key_name}), matrix[{row}]=${self.keyboard_matrix[row]:02X}, keyboard_ext now=${keyboard_ext:02X} ***")
                                else:
                                    log.info(f"*** MATRIX (INPUT ROW): row={row}, col={col} ({key_name}), keyboard_ext now=${keyboard_ext:02X} ***")

                # Combine keyboard and joystick 1 inputs (both active low, so AND them)
                # Joystick 1 only affects bits 0-4 (Up, Down, Left, Right, Fire)
                # Bits 5-7 are keyboard-only
                ext = keyboard_ext & (self.joystick_1 | 0xE0)  # Only apply joystick to bits 0-4

                # Mix CIA output vs input:
                # - Output bits (ddr_b=1): use port_b value AND'd with ext (allows keyboard/joystick to pull low)
                # - Input bits (ddr_b=0): use ext (keyboard/joystick) value
                result = (self.port_b & self.ddr_b & ext) | (ext & ~self.ddr_b)
                if result != 0xFF:  # Only log when a key might be detected
                    # Show which row(s) are being actively scanned (output bits driven low)
                    rows_scanned = []
                    for r in range(8):
                        r_is_output = bool(self.ddr_a & (1 << r))
                        r_driven_low = not bool(self.port_a & (1 << r))
                        if r_is_output and r_driven_low:
                            rows_scanned.append(r)
                    rows_str = ",".join(str(r) for r in rows_scanned) if rows_scanned else "none"

                    # Show which column bits are low (key detected)
                    cols_detected = []
                    for c in range(8):
                        if not (result & (1 << c)):
                            cols_detected.append(c)
                    cols_str = ",".join(str(c) for c in cols_detected) if cols_detected else "none"

                    log.info(f"*** CIA1 Port B READ: result=${result:02X}, rows_scanned=[{rows_str}], cols_detected=[{cols_str}], port_a=${self.port_a:02X}, ddr_a=${self.ddr_a:02X}, port_b=${self.port_b:02X}, ddr_b=${self.ddr_b:02X}, keyboard_ext=${keyboard_ext:02X}, joystick_1=${self.joystick_1:02X} ***")
                return result & 0xFF

            # Port A DDR ($DC02)
            if reg == 0x02:
                return self.ddr_a

            # Port B DDR ($DC03)
            if reg == 0x03:
                return self.ddr_b

            # Timer A Low Byte ($DC04)
            if reg == 0x04:
                return self.timer_a_counter & 0xFF

            # Timer A High Byte ($DC05)
            if reg == 0x05:
                return (self.timer_a_counter >> 8) & 0xFF

            # Timer B Low Byte ($DC06)
            if reg == 0x06:
                return self.timer_b_counter & 0xFF

            # Timer B High Byte ($DC07)
            if reg == 0x07:
                return (self.timer_b_counter >> 8) & 0xFF

            # Interrupt Control Register (ICR) ($DC0D)
            if reg == 0x0D:
                # Reading ICR clears it and returns current interrupt state
                result = self.icr_data
                # Set bit 7 if any enabled interrupt has occurred
                if result & self.icr_mask:
                    result |= 0x80
                # Log ICR reads
                log.info(f"*** CIA1 ICR READ: data=${self.icr_data:02X}, result=${result:02X}, clearing ICR but NOT cpu.irq_pending ***")
                # Clear interrupt data after read
                self.icr_data = 0x00
                # NOTE: Do NOT clear cpu.irq_pending here! The CPU's IRQ handling mechanism
                # should manage irq_pending. The CIA ICR read only acknowledges the CIA's interrupt.
                # The CPU will clear irq_pending when the IRQ handler is called or when no interrupts remain.
                return result

            # Return stored register contents for other registers
            return self.regs[reg]

        def write(self, addr, value) -> None:
            reg = addr & 0x0F
            self.regs[reg] = value

            # Port A ($DC00) — keyboard row selection (KERNAL writes here)
            if reg == 0x00:
                old_port_a = self.port_a
                self.port_a = value
                if old_port_a != value:
                    log.info(f"*** CIA1 Port A WRITE (row select): ${value:02X} ***")

            # Port B ($DC01) — keyboard column sensing (stored but typically not written)
            if reg == 0x01:
                old_port_b = self.port_b
                self.port_b = value
                if old_port_b != value:
                    log.info(f"*** CIA1 Port B WRITE: ${value:02X} (unusual - Port B is typically input-only for keyboard) ***")

            # Port A DDR ($DC02)
            if reg == 0x02:
                old_ddr_a = self.ddr_a
                self.ddr_a = value
                log.info(f"*** CIA1 Port A DDR: ${old_ddr_a:02X} -> ${value:02X} (0=input, 1=output) ***")
                if value != 0xFF:
                    log.info(f"*** WARNING: Port A DDR != 0xFF, rows {bin(~value & 0xFF)} will not be selectable! ***")

            # Port B DDR ($DC03)
            if reg == 0x03:
                self.ddr_b = value
                log.info(f"*** CIA1 Port B DDR: ${value:02X} (0=input, 1=output) ***")

            # Timer A Low Byte ($DC04)
            if reg == 0x04:
                self.timer_a_latch = (self.timer_a_latch & 0xFF00) | value

            # Timer A High Byte ($DC05)
            if reg == 0x05:
                self.timer_a_latch = (self.timer_a_latch & 0x00FF) | (value << 8)

            # Timer B Low Byte ($DC06)
            if reg == 0x06:
                self.timer_b_latch = (self.timer_b_latch & 0xFF00) | value

            # Timer B High Byte ($DC07)
            if reg == 0x07:
                self.timer_b_latch = (self.timer_b_latch & 0x00FF) | (value << 8)

            # Control Register A ($DC0E)
            if reg == 0x0E:
                # Bit 0: Start/Stop Timer A (1=start, 0=stop)
                self.timer_a_running = bool(value & 0x01)
                # Bit 4: Force load (1=load latch into counter)
                if value & 0x10:
                    self.timer_a_counter = self.timer_a_latch
                log.info(f"*** CIA1 Timer A Control: ${value:02X}, running={self.timer_a_running}, latch=${self.timer_a_latch:04X} ***")

            # Control Register B ($DC0F)
            if reg == 0x0F:
                # Bit 0: Start/Stop Timer B (1=start, 0=stop)
                self.timer_b_running = bool(value & 0x01)
                # Bit 4: Force load (1=load latch into counter)
                if value & 0x10:
                    self.timer_b_counter = self.timer_b_latch
                log.info(f"*** CIA1 Timer B Control: ${value:02X}, running={self.timer_b_running}, latch=${self.timer_b_latch:04X} ***")

            # Interrupt Control Register ($DC0D)
            if reg == 0x0D:
                # Bit 7: 1=set bits, 0=clear bits in mask
                if value & 0x80:
                    # Set mask bits
                    self.icr_mask |= (value & 0x1F)
                else:
                    # Clear mask bits
                    self.icr_mask &= ~(value & 0x1F)
                log.info(f"*** CIA1 ICR Mask: ${value:02X}, mask=${self.icr_mask:02X}, Timer A IRQ {'ENABLED' if (self.icr_mask & 0x01) else 'DISABLED'} ***")

        def update(self) -> None:
            """Update CIA timers based on CPU cycles.

            Called periodically to count down timers and generate interrupts.
            """
            # Calculate cycles elapsed since last update
            cycles_elapsed = self.cpu.cycles_executed - self.last_cycle_count
            self.last_cycle_count = self.cpu.cycles_executed

            # Update Timer A
            if self.timer_a_running and cycles_elapsed > 0:
                # Log every 1000 cycles to monitor timer countdown
                if self.cpu.cycles_executed % 10000 < 100:
                    pass  # log.info(f"*** CIA1 Timer A: counter=${self.timer_a_counter:04X}, latch=${self.timer_a_latch:04X}, cycles_elapsed={cycles_elapsed} ***")

                # Count down by elapsed cycles
                if self.timer_a_counter >= cycles_elapsed:
                    self.timer_a_counter -= cycles_elapsed
                else:
                    # Timer underflow
                    underflows = (cycles_elapsed - self.timer_a_counter) // (self.timer_a_latch + 1) + 1
                    self.timer_a_counter = self.timer_a_latch - ((cycles_elapsed - self.timer_a_counter - 1) % (self.timer_a_latch + 1))

                    # Trigger Timer A interrupt (bit 0)
                    self.icr_data |= 0x01
                    # log.info(f"*** CIA1 Timer A UNDERFLOW: Triggering IRQ, counter reloaded to ${self.timer_a_counter:04X}, cycles={self.cpu.cycles_executed} ***")

                    # If Timer A interrupts are enabled, signal CPU IRQ
                    if self.icr_mask & 0x01:
                        self.cpu.irq_pending = True

            # Update Timer B (similar logic)
            if self.timer_b_running and cycles_elapsed > 0:
                if self.timer_b_counter >= cycles_elapsed:
                    self.timer_b_counter -= cycles_elapsed
                else:
                    # Timer underflow
                    underflows = (cycles_elapsed - self.timer_b_counter) // (self.timer_b_latch + 1) + 1
                    self.timer_b_counter = self.timer_b_latch - ((cycles_elapsed - self.timer_b_counter - 1) % (self.timer_b_latch + 1))

                    # Trigger Timer B interrupt (bit 1)
                    self.icr_data |= 0x02

                    # If Timer B interrupts are enabled, signal CPU IRQ
                    if self.icr_mask & 0x02:
                        self.cpu.irq_pending = True
                        log.info(f"*** CIA1 Timer B UNDERFLOW: Triggering IRQ, counter reloaded to ${self.timer_b_counter:04X}, cycles={self.cpu.cycles_executed} ***")

        def _read_keyboard_port(self) -> int:
            """Read keyboard matrix columns based on selected rows.

            The C64 keyboard is an 8x8 matrix:
            - KERNAL writes to Port B ($DC01) to select row(s) - active low
            - KERNAL reads from Port A ($DC00) to get column states - active low
            - 0 = pressed, 1 = released

            The KERNAL typically scans one row at a time by setting one bit low.
            But it can also scan multiple rows simultaneously (all bits low = scan all rows).
            """
            # Port B contains the row selection (active low)
            # Each bit low = scan that row
            selected_rows = ~self.port_b & 0xFF

            # Start with all columns high (no keys)
            result = 0xFF

            # Check each row
            for row in range(8):
                if selected_rows & (1 << row):
                    # This row is selected, AND its columns into result
                    # If any key in this row is pressed (bit=0), it will pull the result low
                    result &= self.keyboard_matrix[row]

            return result

        def _get_key_name(self, row: int, col: int) -> str:
            """Get the PETSCII key name for a matrix position.

            Args:
                row: Row index (0-7)
                col: Column index (0-7)

            Returns:
                Key name string
            """
            # C64 keyboard matrix mapping: (row, col) -> key name
            # Reference: https://www.c64-wiki.com/wiki/Keyboard
            key_map = {
                # Row 0
                (0, 0): "DEL",
                (0, 1): "RETURN",
                (0, 2): "CRSR→",
                (0, 3): "F7",
                (0, 4): "F1",
                (0, 5): "F3",
                (0, 6): "F5",
                (0, 7): "CRSR↓",

                # Row 1
                (1, 0): "3",
                (1, 1): "W",
                (1, 2): "A",
                (1, 3): "4",
                (1, 4): "Z",
                (1, 5): "S",
                (1, 6): "E",
                (1, 7): "LSHIFT",

                # Row 2
                (2, 0): "5",
                (2, 1): "R",
                (2, 2): "D",
                (2, 3): "6",
                (2, 4): "C",
                (2, 5): "F",
                (2, 6): "T",
                (2, 7): "X",

                # Row 3
                (3, 0): "7",
                (3, 1): "Y",
                (3, 2): "G",
                (3, 3): "8",
                (3, 4): "B",
                (3, 5): "H",
                (3, 6): "U",
                (3, 7): "V",

                # Row 4
                (4, 0): "9",
                (4, 1): "I",
                (4, 2): "J",
                (4, 3): "0",
                (4, 4): "M",
                (4, 5): "K",
                (4, 6): "O",
                (4, 7): "N",

                # Row 5
                (5, 0): "+",
                (5, 1): "P",
                (5, 2): "L",
                (5, 3): "-",
                (5, 4): ".",
                (5, 5): ":",
                (5, 6): "@",
                (5, 7): ",",

                # Row 6
                (6, 0): "£",
                (6, 1): "*",
                (6, 2): ";",
                (6, 3): "HOME",
                (6, 4): "RSHIFT",
                (6, 5): "=",
                (6, 6): "↑",
                (6, 7): "/",

                # Row 7
                (7, 0): "1",
                (7, 1): "←",
                (7, 2): "CTRL",
                (7, 3): "2",
                (7, 4): "SPACE",
                (7, 5): "C=",
                (7, 6): "Q",
                (7, 7): "RUN/STOP",
            }

            # Simple key name lookup - just return the key label
            return key_map.get((row, col), f"?({row},{col})?")

        def press_key(self, row: int, col: int) -> None:
            """Press a key at the given matrix position.

            Args:
                row: Row index (0-7)
                col: Column index (0-7)
            """
            if 0 <= row < 8 and 0 <= col < 8:
                # Clear the bit (active low = pressed)
                old_value = self.keyboard_matrix[row]
                self.keyboard_matrix[row] &= ~(1 << col)
                new_value = self.keyboard_matrix[row]
                log.info(f"*** PRESS_KEY: row={row}, col={col}, matrix[{row}]: ${old_value:02X} -> ${new_value:02X} ***")

        def release_key(self, row: int, col: int) -> None:
            """Release a key at the given matrix position.

            Args:
                row: Row index (0-7)
                col: Column index (0-7)
            """
            if 0 <= row < 8 and 0 <= col < 8:
                # Set the bit (active low = released)
                self.keyboard_matrix[row] |= (1 << col)

    class CIA2:
        def __init__(self) -> None:
            self.regs = [0x00] * 16

        def read(self, addr) -> int:
            reg = addr & 0x0F

            if reg == 0x0D:
                # ICR — no interrupts pending
                return 0x00

            return 0xFF  # CIA2 usually floats high where unused

        def write(self, addr, value) -> None:
            reg = addr & 0x0F
            self.regs[reg] = value

    class C64VIC:
        def __init__(self, char_rom, cpu) -> None:
            self.log = logging.getLogger("c64.vic")
            self.regs = [0] * 0x40
            self.char_rom = char_rom
            self.cpu = cpu

            # Set default VIC register values (C64 power-on state)
            # $D018: Memory Control - Screen at $0400, Char ROM at $1000
            # Bits 4-7 = 0001 (screen at 1*$400 = $0400)
            # Bits 1-3 = 010 (char at 2*$800 = $1000)
            self.regs[0x18] = 0x14  # 0001 0100 binary

            # $D020: Border color - Default light blue (14)
            self.regs[0x20] = 0x0E  # Light blue

            # $D021: Background color - Default blue (6)
            self.regs[0x21] = 0x06  # Blue

            # Display dimensions (hardware characteristics)
            # Text area: 320x200 (40x25 characters at 8x8 pixels)
            # Border: 32 pixels on each side (left/right), 35 pixels top/bottom
            # Total visible area: 384x270
            self.text_width = 320
            self.text_height = 200
            self.border_left = 32
            self.border_right = 32
            self.border_top = 35
            self.border_bottom = 35
            self.total_width = self.text_width + self.border_left + self.border_right  # 384
            self.total_height = self.text_height + self.border_top + self.border_bottom  # 270

            # NTSC timing: 263 raster lines, 63 cycles per line
            self.raster_lines = 263
            self.cycles_per_line = 63
            self.cycles_per_frame = self.raster_lines * self.cycles_per_line  # 16,569

            # Current raster line - start at a reasonable position
            self.current_raster = 0

            # Interrupt flags - latched until read/cleared
            # Set bit 0 initially so KERNAL can clear it (boot requirement)
            self.irq_flags = 0x01  # Bit 0=raster, 1=sprite-bg, 2=sprite-sprite, 3=lightpen
            self.irq_enabled = 0x00  # Which interrupts are enabled

            # Track last cycle count to know when to increment raster
            self.last_cycle_count = 0

            # Track initialization state
            self.initialized = False

            self.log.info("VIC-II initialized (NTSC: 263 lines, 63 cycles/line)")

        def update(self) -> None:
            """Update VIC state based on CPU cycles.

            This is called automatically during register reads to keep raster counter current.
            Also checks if a raster IRQ should be triggered.
            """
            # Calculate raster line based on total CPU cycles
            total_lines = self.cpu.cycles_executed // self.cycles_per_line
            new_raster = total_lines % self.raster_lines

            # Check if we should trigger raster IRQ on raster line match
            if new_raster != self.current_raster:
                raster_compare = self.regs[0x12] | ((self.regs[0x11] & 0x80) << 1)
                # Debug: Log every time we change raster line and check for match
                if new_raster == raster_compare:
                    log.info(f"*** VIC RASTER MATCH: line {new_raster} == compare {raster_compare}, irq_enabled=${self.irq_enabled:02X} (bit 0={'set' if (self.irq_enabled & 0x01) else 'clear'}) ***")
                if new_raster == raster_compare and (self.irq_enabled & 0x01):
                    # Set raster IRQ flag (bit 0)
                    self.irq_flags |= 0x01
                    # Signal CPU that IRQ is pending
                    self.cpu.irq_pending = True
                    log.info(f"*** VIC TRIGGERING IRQ: raster line {new_raster}, cpu.irq_pending=True, cycles={self.cpu.cycles_executed} ***")
                    self.log.debug(f"VIC raster IRQ: line {new_raster}, setting cpu.irq_pending=True")

            self.current_raster = new_raster

        def read(self, addr) -> int:
            reg = addr & 0x3F

            # $D012: Raster line register (read current raster position)
            if reg == 0x12:
                self.update()
                return self.current_raster & 0xFF

            # $D019: Interrupt flags (read and acknowledge)
            if reg == 0x19:
                # Return current flags with bit 7 set if any enabled IRQ is active
                flags = self.irq_flags
                # Bit 7 is set if any interrupt occurred (regardless of enable)
                if flags & 0x0F:
                    flags |= 0x80
                return flags

            return self.regs[reg]

        def write(self, addr, val) -> None:
            reg = addr & 0x3F
            self.regs[reg] = val

            # $D012: Raster compare register
            if reg == 0x12:
                raster_compare = val | ((self.regs[0x11] & 0x80) << 1)
                log.info(f"*** VIC RASTER COMPARE: $D012 = ${val:02X}, full compare value = {raster_compare} ***")

            # $D011: Control register (also affects raster compare bit 8)
            if reg == 0x11:
                raster_compare = self.regs[0x12] | ((val & 0x80) << 1)
                log.info(f"*** VIC CONTROL: $D011 = ${val:02X}, raster compare = {raster_compare} ***")

            # $D018: Memory control register (screen/char memory location)
            if reg == 0x18:
                screen_addr = ((val & 0xF0) >> 4) * 0x0400
                char_offset = ((val & 0x0E) >> 1) * 0x0800
                self.log.debug(f"VIC $D018 = ${val:02X}: screen=${screen_addr:04X}, char_offset=${char_offset:04X}")

            # $D019: Interrupt flags - writing 1 to a bit CLEARS it (acknowledge)
            if reg == 0x19:
                # Writing 1 clears the corresponding flag (interrupt latch behavior)
                was_set = self.irq_flags & 0x0F
                self.irq_flags &= ~(val & 0x0F)

                # If all IRQ flags are now clear, clear the CPU's pending IRQ
                if (self.irq_flags & 0x0F) == 0:
                    self.cpu.irq_pending = False
                    self.log.debug("VIC IRQ acknowledged, cpu.irq_pending cleared")

                # Log when KERNAL acknowledges the initial IRQ (completion of VIC init)
                if not self.initialized and was_set and (self.irq_flags & 0x0F) == 0:
                    self.initialized = True
                    self.log.info("VIC-II initialization complete (IRQ acknowledged)")

            # $D01A: Interrupt enable register
            if reg == 0x1A:
                self.irq_enabled = val & 0x0F
                log.info(f"*** VIC IRQ ENABLE: $D01A = ${val:02X}, irq_enabled=${self.irq_enabled:02X}, raster IRQ {'ENABLED' if (self.irq_enabled & 0x01) else 'DISABLED'} ***")

        def render_frame(self, surface, ram, color_ram) -> None:
            """Render complete VIC-II frame including border and character area.

            This method emulates the VIC-II's display generation:
            - Fills the entire frame with border color
            - Renders the 40x25 character text area with proper positioning
            - Handles all VIC register settings (colors, memory locations, etc.)

            Args:
                surface: Pygame surface to render to (should be total_width x total_height)
                ram: Memory accessor for screen RAM
                color_ram: Memory accessor for color RAM
            """
            # Border color from VIC register $D020 (register 0x20)
            border_color = self.regs[0x20] & 0x0F

            # Fill entire surface with border color (VIC draws border first)
            surface.fill(COLORS[border_color])

            # VIC register $D018 (Memory Control Register)
            # Bits 4-7: Screen memory location (Video Matrix Base Address)
            #   Value * 1024 = screen address (within current 16K VIC bank)
            #   Default: 0001 = 1 * 1024 = 0x0400
            # Bits 1-3: Character memory location (Character Dot-Data Base Address)
            #   Value * 2048 = char ROM offset (within current 16K VIC bank)
            #   Default: 010 = 2 * 2048 = 0x1000 (but points to ROM, not RAM)
            mem_control = self.regs[0x18]

            # Screen memory base address
            screen_base = ((mem_control & 0xF0) >> 4) * 0x0400

            # Character ROM bank selection
            char_bank_offset = ((mem_control & 0x0E) >> 1) * 0x0800
            char_bank_offset = char_bank_offset & 0x0FFF  # Mask to 4K

            # Background color from VIC register $D021 (register 0x21)
            bg_color = self.regs[0x21] & 0x0F

            # Render text area within the border
            # VIC positions text area at (border_left, border_top)
            for row in range(25):
                for col in range(40):
                    cell_addr = screen_base + row * 40 + col
                    char_code = ram[cell_addr]
                    color_offset = row * 40 + col
                    color = color_ram[color_offset] & 0x0F

                    # Check for reverse video (character codes 128-255)
                    reverse = char_code >= 128
                    if reverse:
                        char_code = char_code & 0x7F

                    # Get glyph from character ROM
                    glyph_addr = (char_code * 8) + char_bank_offset
                    glyph_addr = glyph_addr & 0x0FFF
                    glyph = self.char_rom[glyph_addr : glyph_addr + 8]

                    # Render character at proper screen position
                    # VIC places text area offset from top-left by border dimensions
                    for y in range(8):
                        line = glyph[y]
                        for x in range(8):
                            pixel = (line >> (7 - x)) & 1
                            # VIC positions pixels: border_offset + character_position
                            pixel_x = self.border_left + col*8 + x
                            pixel_y = self.border_top + row*8 + y

                            if reverse:
                                # Reverse video: swap foreground and background
                                surface.set_at((pixel_x, pixel_y),
                                            COLORS[bg_color] if pixel else COLORS[color])
                            else:
                                # Normal: foreground on background
                                surface.set_at((pixel_x, pixel_y),
                                            COLORS[color] if pixel else COLORS[bg_color])


    class C64Memory:
        def __init__(self, ram, *, basic_rom, kernal_rom, char_rom, cia1, cia2, vic) -> None:
            # Store references to actual RAM storage for direct access (avoids delegation loop)
            self.ram_zeropage = ram.zeropage
            self.ram_stack = ram.stack
            self.ram_heap = ram.heap
            self.basic = basic_rom
            self.kernal = kernal_rom
            self.char = char_rom
            self.cia1 = cia1
            self.cia2 = cia2
            self.vic = vic

            # Color RAM - 1000 bytes ($D800-$DBE7), only low 4 bits used
            self.ram_color = bytearray(1024)

            # CPU I/O port
            self.ddr = 0x00  # $0000
            self.port = 0x37  # $0001 default value

        def _read_ram_direct(self, addr) -> int:
            """Read directly from RAM storage without delegation."""
            if 0 <= addr < 256:
                return self.ram_zeropage[addr].value
            elif 256 <= addr < 512:
                return self.ram_stack[addr - 256].value
            elif addr <= 65535:
                return self.ram_heap[addr - 512].value
            return 0

        def _write_ram_direct(self, addr, value) -> None:
            """Write directly to RAM storage without delegation."""
            from mos6502.memory import Byte, int2ba
            if 0 <= addr < 256:
                self.ram_zeropage[addr] = Byte(value=int2ba(value, length=8, endian="little"), endianness="little")
            elif 256 <= addr < 512:
                self.ram_stack[addr - 256] = Byte(value=int2ba(value, length=8, endian="little"), endianness="little")
            elif addr <= 65535:
                self.ram_heap[addr - 512] = Byte(value=int2ba(value, length=8, endian="little"), endianness="little")

        def _read_io_area(self, addr: int) -> int:
            """Read from I/O area ($D000-$DFFF)."""
            # VIC registers
            if C64.VIC_START <= addr <= C64.VIC_END:
                return self.vic.read(addr)
            # SID registers
            if C64.SID_START <= addr <= C64.SID_END:
                return 0xFF  # SID stub
            # Color RAM
            if C64.COLOR_RAM_START <= addr <= C64.COLOR_RAM_END:
                return self.ram_color[addr - C64.COLOR_RAM_START] | 0xF0
            # CIA1
            if C64.CIA1_START <= addr <= C64.CIA1_END:
                return self.cia1.read(addr)
            # CIA2
            if C64.CIA2_START <= addr <= C64.CIA2_END:
                return self.cia2.read(addr)
            return 0xFF

        def read(self, addr) -> int:
            # CPU internal port
            if addr == 0x0000: return self.ddr
            if addr == 0x0001:
                # Bits with DDR=0 read as 1
                return (self.port | (~self.ddr)) & 0xFF

            # $0002-$9FFF is ALWAYS RAM (never banked on C64)
            # This includes zero page, stack, KERNAL/BASIC working storage, and screen RAM
            if 0x0002 <= addr <= 0x9FFF:
                return self._read_ram_direct(addr)

            # Memory banking logic (only applies to $A000-$FFFF)
            io_enabled = self.port & 0b00000100
            basic_enabled = self.port & 0b00000001
            kernal_enabled = self.port & 0b00000010

            # BASIC ROM ($A000-$BFFF)
            if C64.BASIC_ROM_START <= addr <= C64.BASIC_ROM_END and basic_enabled:
                return self.basic[addr - C64.BASIC_ROM_START]

            # KERNAL ROM ($E000-$FFFF)
            if C64.KERNAL_ROM_START <= addr <= C64.KERNAL_ROM_END and kernal_enabled:
                return self.kernal[addr - C64.KERNAL_ROM_START]

            # I/O or CHAR ROM ($D000-$DFFF)
            if C64.CHAR_ROM_START <= addr <= C64.CHAR_ROM_END:
                if io_enabled:
                    return self._read_io_area(addr)
                else:
                    return self.char[addr - C64.CHAR_ROM_START]

            # RAM fallback (for $A000-$FFFF when banking is off)
            return self._read_ram_direct(addr)

        def _write_io_area(self, addr: int, value: int) -> None:
            """Write to I/O area ($D000-$DFFF)."""
            # VIC registers
            if 0xD000 <= addr <= 0xD3FF:
                self.vic.write(addr, value)
                return
            # SID registers (stub)
            if 0xD400 <= addr <= 0xD7FF:
                return  # Ignore writes to SID
            # Color RAM
            if 0xD800 <= addr <= 0xDBFF:
                self.ram_color[addr - 0xD800] = value & 0x0F  # Only 4 bits
                return
            # CIA1
            if 0xDC00 <= addr <= 0xDCFF:
                self.cia1.write(addr, value)
                return
            # CIA2
            if 0xDD00 <= addr <= 0xDDFF:
                self.cia2.write(addr, value)
                return

        def write(self, addr, value) -> None:
            """Write to C64 memory with banking logic."""
            # CPU internal port
            if addr == 0x0000:
                self.ddr = value & 0xFF
                return
            if addr == 0x0001:
                self.port = value & 0xFF
                return

            # $0002-$9FFF is ALWAYS RAM (never banked on C64)
            # This includes zero page, stack, KERNAL/BASIC working storage, and screen RAM
            if 0x0002 <= addr <= 0x9FFF:
                # Log writes to jiffy clock ($A0-$A2)
                if 0xA0 <= addr <= 0xA2:
                    log.info(f"*** JIFFY CLOCK WRITE: addr=${addr:04X}, value=${value:02X} ***")
                self._write_ram_direct(addr, value & 0xFF)
                return

            # Memory banking logic (only applies to $A000-$FFFF)
            io_enabled = self.port & 0b00000100

            # I/O area ($D000-$DFFF)
            if C64.CHAR_ROM_START <= addr <= C64.CHAR_ROM_END and io_enabled:
                self._write_io_area(addr, value)
                return

            # Writes to $A000-$FFFF always go to underlying RAM
            # (Even if ROM/I/O is visible for reads, writes always go to RAM)
            self._write_ram_direct(addr, value & 0xFF)


    def __init__(self, rom_dir: Path = Path("./roms"), display_mode: str = "terminal", scale: int = 2, enable_irq: bool = True) -> None:
        """Initialize the C64 emulator.

        Arguments:
            rom_dir: Directory containing ROM files (basic, kernal, char)
            display_mode: Display mode (terminal, pygame, headless)
            scale: Pygame window scaling factor
            enable_irq: Enable IRQ injection (default: True)
        """
        self.rom_dir = Path(rom_dir)
        self.display_mode = display_mode
        self.scale = scale
        self.enable_irq = enable_irq

        # Initialize CPU (6510 is essentially a 6502 with I/O ports)
        # We'll use NMOS 6502 as the base
        self.cpu = CPU(cpu_variant=CPUVariant.NMOS_6502)

        log.info(f"Initialized CPU: {self.cpu.variant_name}")

        # Storage for ROMs
        self.basic_rom: Optional[bytes] = None
        self.kernal_rom: Optional[bytes] = None
        self.char_rom: Optional[bytes] = None
        self.vic: Optional[C64.C64VIC] = None
        self.cia1: Optional[C64.CIA1] = None
        self.cia2: Optional[C64.CIA2] = None

        # Pygame display attributes
        self.pygame_screen = None
        self.pygame_surface = None
        self.pygame_available = False

        # Debug logging control
        self.basic_logging_enabled = False
        self.last_pc_region = None

        # self.memory = C64.C64Memory(self.cpu.ram, self.basic_rom, self.kernal_rom, self.char_rom)
        # self.cpu.memory = self.memory

    def load_rom(self, filename: str, expected_size: int, description: str) -> bytes:
        """Load a ROM file from the rom directory.

        Arguments:
            filename: Name of the ROM file
            expected_size: Expected size in bytes
            description: Human-readable description for logging

        Returns:
            ROM data as bytes

        Raises:
            FileNotFoundError: If ROM file doesn't exist
            ValueError: If ROM file size is incorrect
        """
        rom_path = self.rom_dir / filename

        if not rom_path.exists():
            raise FileNotFoundError(
                f"{description} ROM not found: {rom_path}\n"
                f"Expected file: {filename} in directory: {self.rom_dir}"
            )

        rom_data = rom_path.read_bytes()

        if len(rom_data) != expected_size:
            raise ValueError(
                f"{description} ROM has incorrect size: {len(rom_data)} bytes "
                f"(expected {expected_size} bytes)"
            )

        log.info(f"Loaded {description} ROM: {rom_path} ({len(rom_data)} bytes)")
        return rom_data

    def load_roms(self) -> None:
        """Load all C64 ROM files into memory."""
        # Try common ROM filenames
        basic_names = ["basic", "basic.rom", "basic.901226-01.bin"]
        kernal_names = ["kernal", "kernal.rom", "kernal.901227-03.bin"]
        char_names = ["char", "char.rom", "characters.901225-01.bin", "chargen"]

        # Load BASIC ROM
        for name in basic_names:
            try:
                self.basic_rom = self.load_rom(name, self.BASIC_ROM_SIZE, "BASIC")
                break
            except FileNotFoundError:
                continue
        else:
            raise FileNotFoundError(
                f"BASIC ROM not found. Tried: {', '.join(basic_names)} in {self.rom_dir}"
            )

        # Load KERNAL ROM
        for name in kernal_names:
            try:
                self.kernal_rom = self.load_rom(name, self.KERNAL_ROM_SIZE, "KERNAL")
                break
            except FileNotFoundError:
                continue
        else:
            raise FileNotFoundError(
                f"KERNAL ROM not found. Tried: {', '.join(kernal_names)} in {self.rom_dir}"
            )

        # Load CHAR ROM (optional for now)
        for name in char_names:
            try:
                self.char_rom = self.load_rom(name, self.CHAR_ROM_SIZE, "CHAR")
                break
            except FileNotFoundError:
                continue

        if self.char_rom is None:
            log.warning(f"CHAR ROM not found (optional). Tried: {', '.join(char_names)}")

        # Write ROMs to CPU memory
        self._write_rom_to_memory(self.BASIC_ROM_START, self.basic_rom)
        self._write_rom_to_memory(self.KERNAL_ROM_START, self.kernal_rom)

        if self.char_rom:
            self._write_rom_to_memory(self.CHAR_ROM_START, self.char_rom)


        # Now set up the CIA1 and CIA2 and VIC
        self.cia1 = C64.CIA1(cpu=self.cpu)
        self.cia2 = C64.CIA2()
        self.vic = C64.C64VIC(char_rom=self.char_rom, cpu=self.cpu)

        # Initialize memory
        self.memory = C64.C64Memory(
            self.cpu.ram,
            basic_rom=self.basic_rom,
            kernal_rom=self.kernal_rom,
            char_rom=self.char_rom,
            cia1=self.cia1,
            cia2=self.cia2,
            vic=self.vic,
        )
        # Hook up the memory handler so CPU RAM accesses go through C64Memory
        self.cpu.ram.memory_handler = self.memory

        # Set up periodic update callback for both VIC and CIA1
        # VIC checks cycle count and triggers raster IRQs
        # CIA1 counts down timers and triggers timer IRQs
        def update_peripherals():
            self.vic.update()
            self.cia1.update()

        self.cpu.periodic_callback = update_peripherals
        self.cpu.periodic_callback_interval = 63  # Update every raster line (63 cycles/line)

        log.info("All ROMs loaded into memory")

        # Note: PC is already set from reset vector by cpu.reset() in main()
        # The reset() method handles the complete reset sequence including
        # fetching the vector from $FFFC/$FFFD and setting PC accordingly
        log.info(f"PC initialized to ${self.cpu.PC:04X} (from reset vector at ${self.RESET_VECTOR_ADDR:04X})")

    def init_pygame_display(self) -> bool:
        """Initialize pygame display.

        Returns:
            True if pygame was successfully initialized, False otherwise
        """
        try:
            import pygame
            self.pygame_available = True
        except ImportError:
            log.error("Pygame not installed. Install with: pip install pygame-ce")
            return False

        try:
            pygame.init()

            # Get display dimensions from VIC (hardware characteristics)
            total_width = self.vic.total_width
            total_height = self.vic.total_height

            # Create window with scaled dimensions
            width = total_width * self.scale
            height = total_height * self.scale
            self.pygame_screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption("C64 Emulator")

            # Create the rendering surface (384x270 with border)
            self.pygame_surface = pygame.Surface((total_width, total_height))

            log.info(f"Pygame display initialized: {width}x{height} (scale={self.scale})")
            return True

        except Exception as e:
            log.error(f"Failed to initialize pygame: {e}")
            self.pygame_available = False
            return False

    def _write_rom_to_memory(self, start_addr: int, rom_data: bytes) -> None:
        """Write ROM data to CPU memory.

        Arguments:
            start_addr: Starting address in CPU memory
            rom_data: ROM data to write
        """
        for offset, byte_value in enumerate(rom_data):
            self.cpu.ram[start_addr + offset] = byte_value

        log.debug(f"Wrote ROM to ${start_addr:04X}-${start_addr + len(rom_data) - 1:04X}")

    def load_program(self, program_path: Path, load_address: Optional[int] = None) -> int:
        """Load a program into memory.

        Arguments:
            program_path: Path to the program file
            load_address: Address to load program at (default: $0801 for BASIC programs)
                         If None and file has a 2-byte header, use header address

        Returns:
            The actual load address used
        """
        program_path = Path(program_path)

        if not program_path.exists():
            raise FileNotFoundError(f"Program not found: {program_path}")

        program_data = program_path.read_bytes()

        # Check if program has a load address header (common for .prg files)
        if load_address is None and len(program_data) >= 2:
            # First two bytes might be load address (little-endian)
            header_addr = program_data[0] | (program_data[1] << 8)

            # If it looks like a reasonable address, use it
            if 0x0000 <= header_addr <= 0xFFFF:
                load_address = header_addr
                program_data = program_data[2:]  # Skip header
                log.info(f"Using load address from file header: ${load_address:04X}")

        # Default to BASIC program start
        if load_address is None:
            load_address = self.BASIC_PROGRAM_START

        # Write program to memory
        for offset, byte_value in enumerate(program_data):
            self.cpu.ram[load_address + offset] = byte_value

        log.info(
            f"Loaded program: {program_path.name} "
            f"at ${load_address:04X}-${load_address + len(program_data) - 1:04X} "
            f"({len(program_data)} bytes)"
        )

        return load_address

    def reset(self) -> None:
        """Reset the C64 (CPU reset).

        The CPU reset() method now handles the complete 6502 reset sequence:
        - Sets S = 0xFD
        - Sets P = 0x34 (I flag set, interrupts disabled)
        - Fetches reset vector from $FFFC/$FFFD
        - Sets PC to vector value
        - Consumes 7 cycles
        """
        log.info("Resetting C64...")

        # CPU reset handles the complete hardware reset sequence
        self.cpu.reset()

        log.info(f"Reset complete: PC=${self.cpu.PC:04X}, S=${self.cpu.S & 0xFF:02X}")

    def get_pc_region(self) -> str:
        """Determine which memory region PC is currently in.

        Takes memory banking into account (via $0001 port).

        Returns:
            String describing the region: "RAM", "BASIC", "KERNAL", "I/O", "CHAR", or "???"
        """
        pc = self.cpu.PC
        port = self.memory.port

        if pc < self.BASIC_ROM_START:
            return "RAM"
        elif self.BASIC_ROM_START <= pc <= self.BASIC_ROM_END:
            # BASIC ROM only visible if bit 0 of port is set
            return "BASIC" if (port & 0x01) else "RAM"
        elif self.CHAR_ROM_START <= pc <= self.CHAR_ROM_END:
            # I/O vs CHAR vs RAM depends on bits in port
            if port & 0x04:
                return "I/O"
            elif (port & 0x03) == 0x01:
                return "CHAR"
            else:
                return "RAM"
        elif self.KERNAL_ROM_START <= pc <= self.KERNAL_ROM_END:
            # KERNAL ROM only visible if bit 1 of port is set
            return "KERNAL" if (port & 0x02) else "RAM"
        else:
            return "???"

    def _check_pc_region(self) -> None:
        """Monitor PC and enable detailed logging when entering BASIC or KERNAL ROM."""
        region = self.get_pc_region()

        # Track important PC locations
        pc = self.cpu.PC

        # Log when we reach BASIC input loop at $A7AE
        if pc == 0xA7AE and not hasattr(self, '_logged_a7ae'):
            self._logged_a7ae = True
            log.info(f"*** REACHED BASIC INPUT LOOP at $A7AE ***")

        # Log when stuck at KERNAL idle loop ($E5CF-$E5D2)
        if 0xE5CF <= pc <= 0xE5D2:
            if not hasattr(self, '_e5cf_count'):
                self._e5cf_count = 0
            self._e5cf_count += 1
            if self._e5cf_count % 10000 == 0:
                log.info(f"*** Still in KERNAL idle loop at ${pc:04X} (count={self._e5cf_count}) ***")

        # Enable logging when entering KERNAL for the first time (for debugging)
        # TEMPORARILY DISABLED
        # if region == "KERNAL" and self.last_pc_region != "KERNAL":
        #     logging.getLogger("mos6502").setLevel(logging.DEBUG)
        #     logging.getLogger("mos6502.cpu").setLevel(logging.DEBUG)
        #     logging.getLogger("mos6502.cpu.flags").setLevel(logging.DEBUG)
        #     logging.getLogger("mos6502.memory").setLevel(logging.DEBUG)
        #     logging.getLogger("mos6502.memory.RAM").setLevel(logging.DEBUG)
        #     logging.getLogger("mos6502.memory.Byte").setLevel(logging.DEBUG)
        #     logging.getLogger("mos6502.memory.Word").setLevel(logging.DEBUG)
        #     log.info(f"*** ENTERING KERNAL ROM at ${self.cpu.PC:04X} - Enabling detailed CPU logging ***")

        # Enable logging when entering BASIC for the first time
        # TEMPORARILY DISABLED
        # if region == "BASIC" and not self.basic_logging_enabled:
        #     self.basic_logging_enabled = True
        #     logging.getLogger("mos6502").setLevel(logging.DEBUG)
        #     logging.getLogger("mos6502.cpu").setLevel(logging.DEBUG)
        #     logging.getLogger("mos6502.cpu.flags").setLevel(logging.DEBUG)
        #     logging.getLogger("mos6502.memory").setLevel(logging.DEBUG)
        #     logging.getLogger("mos6502.memory.RAM").setLevel(logging.DEBUG)
        #     logging.getLogger("mos6502.memory.Byte").setLevel(logging.DEBUG)
        #     logging.getLogger("mos6502.memory.Word").setLevel(logging.DEBUG)
        #     log.info(f"*** ENTERING BASIC ROM at ${self.cpu.PC:04X} - Enabling detailed CPU logging ***")

        self.last_pc_region = region



    def run(self, max_cycles: int = INFINITE_CYCLES) -> None:
        """Run the C64 emulator.

        Arguments:
            max_cycles: Maximum number of CPU cycles to execute
                       (default: INFINITE_CYCLES for continuous execution)
        """
        log.info(f"Starting execution at PC=${self.cpu.PC:04X}")
        log.info("Press Ctrl+C to stop")

        try:
            # Execute with cycle counter display
            import threading
            import time
            import sys as _sys

            # Check if we're in a TTY (terminal) for interactive display
            is_tty = _sys.stdout.isatty()

            # For pygame mode, run CPU in background thread and pygame in main thread
            # For other modes, run display in background and CPU in main thread
            if self.display_mode == "pygame" and self.pygame_available:
                # Pygame mode: CPU in background, rendering in main thread
                cpu_done = threading.Event()
                cpu_error = None

                def cpu_thread() -> None:
                    nonlocal cpu_error
                    try:
                        # IRQs are now handled automatically by the CPU based on irq_pending flag
                        # No need for separate execute_with_irqs method
                        self.cpu.execute(cycles=max_cycles)
                    except Exception as e:
                        cpu_error = e
                    finally:
                        cpu_done.set()

                # Start CPU thread
                cpu_thread_obj = threading.Thread(target=cpu_thread, daemon=True)
                cpu_thread_obj.start()

                # Main thread handles pygame rendering
                try:
                    while not cpu_done.is_set():
                        self._render_pygame()
                        time.sleep(0.1)  # Update 10 times per second
                finally:
                    cpu_done.set()
                    cpu_thread_obj.join(timeout=0.5)

                    # Cleanup pygame
                    if self.pygame_available:
                        try:
                            import pygame
                            pygame.quit()
                        except Exception:
                            pass

                # Re-raise CPU thread exception if any
                if cpu_error:
                    raise cpu_error

            else:
                # Terminal or none mode: display in background, CPU in main thread
                stop_display = threading.Event()

                def display_cycles() -> None:
                    """Display cycle count, CPU state, and C64 screen."""
                    while not stop_display.is_set():
                        # Check PC region for all modes (enables debug logging when entering BASIC)
                        self._check_pc_region()
                        if self.display_mode == "terminal" and is_tty:
                            self._render_terminal()
                        # "headless" mode: just checks PC region
                        time.sleep(0.1)  # Update 10 times per second

                # Start the display thread for all modes (including headless for PC region checking)
                display_thread = threading.Thread(target=display_cycles, daemon=True)
                display_thread.start()

                try:
                    # IRQs are now handled automatically by the CPU based on irq_pending flag
                    # No need for separate execute_with_irqs method
                    self.cpu.execute(cycles=max_cycles)
                finally:
                    # Stop the display thread
                    stop_display.set()
                    display_thread.join(timeout=0.5)

        except errors.CPUCycleExhaustionError as e:
            log.info(f"CPU execution completed: {e}")
        except errors.CPUBreakError as e:
            log.info(f"Program terminated (BRK at PC=${self.cpu.PC:04X})")
        except KeyboardInterrupt:
            log.info("\nExecution interrupted by user")
            log.info(f"PC=${self.cpu.PC:04X}, Cycles={self.cpu.cycles_executed}")
        except (errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError, RuntimeError) as e:
            log.exception(f"Execution error at PC=${self.cpu.PC:04X}")
            # Show context around error
            try:
                pc_val = int(self.cpu.PC)
                self.show_disassembly(max(0, pc_val - 10), num_instructions=20)
                self.dump_memory(max(0, pc_val - 16), min(0xFFFF, pc_val + 16))
            except (IndexError, KeyError, ValueError):
                log.exception("Could not display context")
            raise
        finally:
            # Always show screen buffer on termination
            self.show_screen()

    def dump_memory(self, start: int, end: int, bytes_per_line: int = 16) -> None:
        """Dump memory contents for debugging.

        Arguments:
            start: Starting address
            end: Ending address
            bytes_per_line: Number of bytes to display per line
        """
        print(f"\nMemory dump ${start:04X}-${end:04X}:")
        print("      ", end="")
        for i in range(bytes_per_line):
            print(f" {i:02X}", end="")
        print()

        for addr in range(start, end + 1, bytes_per_line):
            print(f"{addr:04X}: ", end="")
            for offset in range(bytes_per_line):
                if addr + offset <= end:
                    byte_val = self.cpu.ram[addr + offset]
                    print(f" {byte_val:02X}", end="")
                else:
                    print("   ", end="")
            print()

    def dump_registers(self) -> None:
        """Dump CPU register state."""
        print(f"\nCPU Registers:")
        print(f"  PC: ${self.cpu.PC:04X}")
        print(f"  A:  ${self.cpu.A:02X}  ({self.cpu.A})")
        print(f"  X:  ${self.cpu.X:02X}  ({self.cpu.X})")
        print(f"  Y:  ${self.cpu.Y:02X}  ({self.cpu.Y})")
        print(f"  S:  ${self.cpu.S:04X}")
        print(f"  Flags: C={self.cpu.C} Z={self.cpu.Z} I={self.cpu.I} "
              f"D={self.cpu.D} B={self.cpu.B} V={self.cpu.V} N={self.cpu.N}")
        print(f"  Cycles executed: {self.cpu.cycles_executed}")

    def disassemble_at(self, address: int, num_instructions: int = 10) -> list[str]:
        """Disassemble instructions starting at address.

        Arguments:
            address: Starting address
            num_instructions: Number of instructions to disassemble

        Returns:
            List of disassembly strings
        """
        from mos6502 import instructions

        lines = []
        current_addr = address

        for _ in range(num_instructions):
            if current_addr > 0xFFFF:
                break

            opcode = self.cpu.ram[current_addr]

            # First try InstructionSet.map (has full metadata)
            if opcode in instructions.InstructionSet.map:
                inst_info = instructions.InstructionSet.map[opcode]
                # Convert bytes/cycles to int (they might be strings in the map)
                try:
                    num_bytes = int(inst_info.get("bytes", 1))
                except (ValueError, TypeError):
                    num_bytes = 1

                # Extract mnemonic from assembler string (e.g., "LDX #{oper}" -> "LDX")
                assembler = inst_info.get("assembler", "???")
                mnemonic = assembler.split()[0] if assembler != "???" else "???"
                mode = inst_info.get("addressing", "")

            # If not in map, try OPCODE_LOOKUP (just has opcode objects)
            elif opcode in instructions.OPCODE_LOOKUP:
                opcode_obj = instructions.OPCODE_LOOKUP[opcode]
                # Extract mnemonic from function name (e.g., "sei_implied_0x78" -> "SEI")
                func_name = opcode_obj.function
                mnemonic = func_name.split("_")[0].upper()

                # Guess number of bytes from function name
                if "implied" in func_name or "accumulator" in func_name:
                    num_bytes = 1
                elif "relative" in func_name or "immediate" in func_name or "zeropage" in func_name:
                    num_bytes = 2
                else:
                    num_bytes = 3

                mode = "implied"

            else:
                # Unknown/illegal opcode
                hex_str = f"{opcode:02X}"
                line = f"${current_addr:04X}: {hex_str}        ???  ; ILLEGAL/UNKNOWN ${opcode:02X}"
                lines.append(line)
                current_addr += 1
                continue

            # Build hex dump
            hex_bytes = [f"{self.cpu.ram[current_addr + i]:02X}"
                        for i in range(min(num_bytes, 3))]
            hex_str = " ".join(hex_bytes).ljust(8)

            # Build operand display
            if num_bytes == 1:
                operand_str = ""
            elif num_bytes == 2:
                operand = self.cpu.ram[current_addr + 1]
                operand_str = f" ${operand:02X}"
            elif num_bytes == 3:
                lo = self.cpu.ram[current_addr + 1]
                hi = self.cpu.ram[current_addr + 2]
                operand = (hi << 8) | lo
                operand_str = f" ${operand:04X}"
            else:
                operand_str = ""

            # Mark illegal opcodes
            if mnemonic == "???":
                line = f"${current_addr:04X}: {hex_str}  {mnemonic}  ; ILLEGAL ${opcode:02X}"
            else:
                line = f"${current_addr:04X}: {hex_str}  {mnemonic}{operand_str}  ; {mode}"
            lines.append(line)
            current_addr += num_bytes

        return lines

    def show_disassembly(self, address: int, num_instructions: int = 10) -> None:
        """Display disassembly at address."""
        print(f"\nDisassembly at ${address:04X}:")
        print("-" * 60)
        for line in self.disassemble_at(address, num_instructions):
            print(line)

    def petscii_to_ascii(self, petscii_code: int) -> str:
        """Convert PETSCII code to displayable ASCII character.

        Arguments:
            petscii_code: PETSCII character code (0-255)

        Returns:
            ASCII character or representation
        """
        # Basic PETSCII to ASCII conversion (simplified)
        # Uppercase letters (PETSCII 65-90 = ASCII 65-90)
        if 65 <= petscii_code <= 90:
            return chr(petscii_code)
        # Lowercase letters (PETSCII 97-122 = ASCII 97-122)
        if 97 <= petscii_code <= 122:
            return chr(petscii_code)
        # Digits (PETSCII 48-57 = ASCII 48-57)
        if 48 <= petscii_code <= 57:
            return chr(petscii_code)
        # Space
        if petscii_code == 32:
            return " "
        # Common punctuation
        punctuation = {
            33: "!", 34: '"', 35: "#", 36: "$", 37: "%", 38: "&", 39: "'",
            40: "(", 41: ")", 42: "*", 43: "+", 44: ",", 45: "-", 46: ".", 47: "/",
            58: ":", 59: ";", 60: "<", 61: "=", 62: ">", 63: "?", 64: "@",
            91: "[", 93: "]", 95: "_"
        }
        if petscii_code in punctuation:
            return punctuation[petscii_code]
        # Screen codes 1-26 map to letters A-Z (reverse video in C64)
        if 1 <= petscii_code <= 26:
            return chr(64 + petscii_code)  # Convert to uppercase letter
        # Default: show as '.' for unprintable
        return "."

    def show_screen(self) -> None:
        """Display the C64 screen (40x25 characters from screen RAM at $0400)."""
        screen_start = 0x0400
        screen_end = 0x07E7
        cols = 40
        rows = 25

        print("\n" + "=" * 42)
        print(" C64 SCREEN")
        print("=" * 42)

        for row in range(rows):
            line = ""
            for col in range(cols):
                addr = screen_start + (row * cols) + col
                if addr <= screen_end:
                    petscii = int(self.cpu.ram[addr])
                    line += self.petscii_to_ascii(petscii)
                else:
                    line += " "
            # Only print non-empty lines
            if line.strip():
                print(line.rstrip())
            else:
                print()

        print("=" * 42)

    def _render_terminal(self) -> None:
        """Render C64 screen to terminal."""
        import sys as _sys

        screen_start = 0x0400
        cols = 40
        rows = 25

        # Clear screen and move cursor to top
        _sys.stdout.write("\033[2J\033[H")

        # Render C64 screen (40x25 characters)
        _sys.stdout.write("=" * 42 + "\n")
        _sys.stdout.write(" C64 SCREEN\n")
        _sys.stdout.write("=" * 42 + "\n")

        for row in range(rows):
            line = ""
            for col in range(cols):
                addr = screen_start + (row * cols) + col
                petscii = int(self.cpu.ram[addr])
                line += self.petscii_to_ascii(petscii)
            _sys.stdout.write(line + "\n")

        _sys.stdout.write("=" * 42 + "\n")

        # Get flag values using shared formatter
        from mos6502.flags import format_flags
        flags = format_flags(self.cpu._flags.value)

        # Determine what's mapped at PC
        pc = self.cpu.PC
        region = self.get_pc_region()

        # Disassemble current instruction
        try:
            inst_str = self.disassemble_instruction(pc)
            inst_display = inst_str.strip()
        except (KeyError, ValueError, IndexError):
            # Fallback: just show opcode bytes if disassembly fails
            try:
                b0 = self.cpu.ram[pc]
                b1 = self.cpu.ram[pc+1]
                b2 = self.cpu.ram[pc+2]
                inst_display = f"{b0:02X} {b1:02X} {b2:02X}  ???"
            except IndexError:
                inst_display = "???"

        # Status line at bottom
        status = (f"Cycles: {self.cpu.cycles_executed:,} | "
                f"PC=${self.cpu.PC:04X}[{region}] {inst_display:20s} | "
                f"A=${self.cpu.A:02X} X=${self.cpu.X:02X} "
                f"Y=${self.cpu.Y:02X} S=${self.cpu.S & 0xFF:02X} P={flags}")
        _sys.stdout.write(status + "\n")
        _sys.stdout.flush()

    def _handle_pygame_keyboard(self, event, pygame) -> None:
        """Handle pygame keyboard events and update CIA1 keyboard matrix.

        Args:
            event: Pygame event
            pygame: Pygame module
        """
        # C64 keyboard matrix mapping: (row, col)
        # Reference: https://www.c64-wiki.com/wiki/Keyboard
        key_map = {
            # Row 0
            pygame.K_BACKSPACE: (0, 0),  # DEL/INST
            pygame.K_RETURN: (0, 1),     # RETURN
            pygame.K_KP_ENTER: (0, 1),   # RETURN (numeric keypad)
            pygame.K_RIGHT: (0, 2),      # CRSR →
            pygame.K_F7: (0, 3),         # F7
            pygame.K_F1: (0, 4),         # F1
            pygame.K_F3: (0, 5),         # F3
            pygame.K_F5: (0, 6),         # F5
            pygame.K_DOWN: (0, 7),       # CRSR ↓

            # Row 1
            pygame.K_3: (1, 0),
            pygame.K_w: (1, 1),
            pygame.K_a: (1, 2),
            pygame.K_4: (1, 3),
            pygame.K_z: (1, 4),
            pygame.K_s: (1, 5),
            pygame.K_e: (1, 6),
            pygame.K_LSHIFT: (1, 7),     # Left SHIFT

            # Row 2
            pygame.K_5: (2, 0),
            pygame.K_r: (2, 1),
            pygame.K_d: (2, 2),
            pygame.K_6: (2, 3),
            pygame.K_c: (2, 4),
            pygame.K_f: (2, 5),
            pygame.K_t: (2, 6),
            pygame.K_x: (2, 7),

            # Row 3
            pygame.K_7: (3, 0),
            pygame.K_y: (3, 1),
            pygame.K_g: (3, 2),
            pygame.K_8: (3, 3),
            pygame.K_b: (3, 4),
            pygame.K_h: (3, 5),
            pygame.K_u: (3, 6),
            pygame.K_v: (3, 7),

            # Row 4
            pygame.K_9: (4, 0),
            pygame.K_i: (4, 1),
            pygame.K_j: (4, 2),
            pygame.K_0: (4, 3),
            pygame.K_m: (4, 4),
            pygame.K_k: (4, 5),
            pygame.K_o: (4, 6),
            pygame.K_n: (4, 7),

            # Row 5
            pygame.K_PLUS: (5, 0),       # +
            pygame.K_p: (5, 1),
            pygame.K_l: (5, 2),
            pygame.K_MINUS: (5, 3),      # -
            pygame.K_PERIOD: (5, 4),     # .
            pygame.K_COLON: (5, 5),      # :
            pygame.K_AT: (5, 6),         # @
            pygame.K_COMMA: (5, 7),      # ,

            # Row 6
            # pygame.K_POUND: (6, 0),    # £ (not on US keyboard)
            pygame.K_ASTERISK: (6, 1),   # *
            pygame.K_SEMICOLON: (6, 2),  # ;
            pygame.K_HOME: (6, 3),       # HOME/CLR
            # pygame.K_CLR: (6, 4),      # CLR (combined with HOME)
            pygame.K_EQUALS: (6, 5),     # =
            pygame.K_UP: (6, 6),         # ↑ (up arrow, mapped to up key)
            pygame.K_SLASH: (6, 7),      # /

            # Row 7
            pygame.K_1: (7, 0),
            pygame.K_LEFT: (7, 1),       # ← (CRSR left, using arrow key)
            pygame.K_LCTRL: (7, 2),      # CTRL
            pygame.K_2: (7, 3),
            pygame.K_SPACE: (7, 4),      # SPACE
            # pygame.K_COMMODORE: (7, 5), # C= (no pygame equivalent)
            pygame.K_q: (7, 6),
            pygame.K_ESCAPE: (7, 7),     # RUN/STOP (mapped to ESC)
        }

        if event.type == pygame.KEYDOWN:
            # Log all key presses with key code and name
            key_name = pygame.key.name(event.key) if hasattr(pygame.key, 'name') else str(event.key)

            # Try to get ASCII representation
            try:
                ascii_char = chr(event.key) if 32 <= event.key < 127 else f"<{event.key}>"
                ascii_code = event.key
            except (ValueError, OverflowError):
                ascii_char = f"<non-printable>"
                ascii_code = event.key

            if event.key in key_map:
                row, col = key_map[event.key]
                self.cia1.press_key(row, col)
                petscii_key = self.cia1._get_key_name(row, col)
                log.info(f"*** KEYDOWN: pygame='{key_name}' (code={event.key}), ASCII='{ascii_char}' (0x{ascii_code:02X}), matrix position=({row},{col}), PETSCII={petscii_key} ***")
            else:
                log.info(f"*** UNMAPPED KEYDOWN: pygame='{key_name}' (code={event.key}), ASCII='{ascii_char}' ***")
        elif event.type == pygame.KEYUP:
            if event.key in key_map:
                row, col = key_map[event.key]
                self.cia1.release_key(row, col)
                log.info(f"*** KEY RELEASED: pygame key {event.key}, row={row}, col={col} ***")

    def _render_pygame(self) -> None:
        """Render C64 screen to pygame window."""
        if not self.pygame_available or self.pygame_screen is None:
            return

        try:
            import pygame

            # Check if we've entered BASIC ROM (for conditional logging)
            self._check_pc_region()

            # Handle pygame events (window close, keyboard, etc.)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    import sys
                    sys.exit(0)
                elif event.type == pygame.KEYDOWN:
                    log.info(f"*** PYGAME KEYDOWN EVENT: key={event.key} ***")
                    self._handle_pygame_keyboard(event, pygame)
                elif event.type == pygame.KEYUP:
                    self._handle_pygame_keyboard(event, pygame)

            # Create memory wrappers for VIC
            class RAMWrapper:
                def __init__(self, cpu_ram):
                    self.cpu_ram = cpu_ram

                def __getitem__(self, index):
                    return int(self.cpu_ram[index])

            class ColorRAMWrapper:
                def __init__(self, color_ram):
                    self.color_ram = color_ram

                def __getitem__(self, index):
                    return self.color_ram[index] & 0x0F

            ram_wrapper = RAMWrapper(self.cpu.ram)
            color_wrapper = ColorRAMWrapper(self.memory.ram_color)

            # Let VIC render the complete frame (border + text)
            # VIC handles all positioning and color logic internally
            self.vic.render_frame(self.pygame_surface, ram_wrapper, color_wrapper)

            # Scale and blit to screen
            scaled_surface = pygame.transform.scale(
                self.pygame_surface,
                (self.vic.total_width * self.scale, self.vic.total_height * self.scale)
            )
            self.pygame_screen.blit(scaled_surface, (0, 0))
            pygame.display.flip()

        except Exception as e:
            log.error(f"Error rendering pygame display: {e}")

    def disassemble_instruction(self, address: int) -> str:
        """Disassemble a single instruction at the given address.

        Arguments:
            address: Address of instruction to disassemble

        Returns:
            Formatted disassembly string for the instruction

        """
        from mos6502 import instructions

        opcode = self.cpu.ram[address]

        # First try InstructionSet.map (has full metadata)
        if opcode in instructions.InstructionSet.map:
            inst_info = instructions.InstructionSet.map[opcode]
            # Convert bytes/cycles to int (they might be strings in the map)
            try:
                num_bytes = int(inst_info.get("bytes", 1))
            except (ValueError, TypeError):
                num_bytes = 1

            # Extract mnemonic from assembler string (e.g., "LDX #{oper}" -> "LDX")
            assembler = inst_info.get("assembler", "???")
            mnemonic = assembler.split()[0] if assembler != "???" else "???"
            mode = inst_info.get("addressing", "")

        # If not in map, try OPCODE_LOOKUP (just has opcode objects)
        elif opcode in instructions.OPCODE_LOOKUP:
            opcode_obj = instructions.OPCODE_LOOKUP[opcode]
            # Extract mnemonic from function name (e.g., "sei_implied_0x78" -> "SEI")
            func_name = opcode_obj.function
            mnemonic = func_name.split("_")[0].upper()

            # Guess number of bytes from function name
            if "implied" in func_name or "accumulator" in func_name:
                num_bytes = 1
            elif "relative" in func_name or "immediate" in func_name or "zeropage" in func_name:
                num_bytes = 2
            else:
                num_bytes = 3

            mode = "implied"

        else:
            # Unknown/illegal opcode - return formatted string
            return f"{opcode:02X}              ???  ; ILLEGAL ${opcode:02X}"

        # Build hex dump
        hex_bytes = [f"{self.cpu.ram[address + i]:02X}"
                    for i in range(min(num_bytes, 3))]
        hex_str = " ".join(hex_bytes).ljust(8)

        # Build operand display
        if num_bytes == 1:
            operand_str = ""
        elif num_bytes == 2:
            operand = self.cpu.ram[address + 1]
            operand_str = f" ${operand:02X}"
        elif num_bytes == 3:
            lo = self.cpu.ram[address + 1]
            hi = self.cpu.ram[address + 2]
            operand = (hi << 8) | lo
            operand_str = f" ${operand:04X}"
        else:
            operand_str = ""

        # Return formatted string without the address prefix
        if mnemonic == "???":
            return f"{hex_str}  {mnemonic}  ; ILLEGAL ${opcode:02X}"
        else:
            return f"{hex_str}  {mnemonic}{operand_str}  ; {mode}"


def main() -> int | None:
    """Run the C64 emulator CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="Commodore 64 Emulator")
    parser.add_argument(
        "--rom-dir",
        type=Path,
        default=Path("./roms"),
        help="Directory containing ROM files (default: ./roms)",
    )
    parser.add_argument(
        "--program",
        type=Path,
        help="Program file to load and run (.prg, .bin, etc.)",
    )
    parser.add_argument(
        "--load-address",
        type=lambda x: int(x, 0),
        help="Override load address (hex or decimal, e.g., 0x0801 or 2049)",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=INFINITE_CYCLES,
        help="Maximum CPU cycles to execute (default: infinite)",
    )
    parser.add_argument(
        "--dump-mem",
        nargs=2,
        metavar=("START", "END"),
        type=lambda x: int(x, 0),
        help="Dump memory region after execution (hex or decimal addresses)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--no-roms",
        action="store_true",
        help="Run without C64 ROMs (for testing standalone programs)",
    )
    parser.add_argument(
        "--disassemble",
        type=lambda x: int(x, 0),
        metavar="ADDRESS",
        help="Disassemble at address and exit (hex or decimal)",
    )
    parser.add_argument(
        "--num-instructions",
        type=int,
        default=20,
        help="Number of instructions to disassemble (default: 20)",
    )
    parser.add_argument(
        "--show-screen",
        action="store_true",
        help="Display screen RAM after execution (40x25 character display)",
    )
    parser.add_argument(
        "--display",
        type=str,
        choices=["terminal", "pygame", "headless"],
        default="terminal",
        help="Display mode: terminal (default), pygame (graphical), or headless (no display)",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=2,
        help="Pygame window scaling factor (default: 2 = 640x400)",
    )
    parser.add_argument(
        "--no-irq",
        action="store_true",
        help="Disable IRQ injection (for debugging; system will hang waiting for IRQs)",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Initialize C64
        c64 = C64(rom_dir=args.rom_dir, display_mode=args.display, scale=args.scale, enable_irq=not args.no_irq)

        # Start with minimal logging - will auto-enable when BASIC ROM is entered
        # This avoids flooding the console during KERNAL boot
        logging.getLogger("mos6502").setLevel(logging.CRITICAL)
        logging.getLogger("mos6502.cpu.flags").setLevel(logging.CRITICAL)
        log.info("CPU logging will enable when BASIC ROM is entered")

        # Load ROMs first (if using C64 ROMs)
        # This creates the VIC which is needed for pygame initialization
        if not args.no_roms:
            c64.load_roms()

        # Reset CPU AFTER ROMs are loaded so reset vector can be read correctly
        # This implements the complete 6502 reset sequence:
        # - Clears RAM to 0xFF
        # - Sets S = 0xFD
        # - Sets P = 0x34 (I=1, interrupts disabled)
        # - Reads reset vector from $FFFC/$FFFD
        # - Sets PC to vector value
        # - Consumes 7 cycles
        c64.cpu.reset()

        # Initialize pygame AFTER VIC is created
        if args.display == "pygame":
            if not c64.init_pygame_display():
                log.warning("Pygame initialization failed, falling back to terminal mode")
                c64.display_mode = "terminal"

        # In no-roms mode, log that we're running headless
        if args.no_roms:
            log.info(f"Running in headless mode (no ROMs)")

        # Load program AFTER reset (so it doesn't get cleared)
        if args.program:
            actual_load_addr = c64.load_program(args.program, load_address=args.load_address)
            # In no-roms mode, set PC to the program's load address
            if args.no_roms:
                c64.cpu.PC = actual_load_addr
                log.info(f"PC set to ${c64.cpu.PC:04X}")
        elif args.no_roms:
            log.error("--no-roms requires --program to be specified")
            return 1

        # If disassemble mode, show disassembly and exit
        if args.disassemble is not None:
            c64.show_disassembly(args.disassemble, num_instructions=args.num_instructions)
            if args.dump_mem:
                c64.dump_memory(args.dump_mem[0], args.dump_mem[1])
            return 0

        # Dump initial state if verbose
        if args.verbose:
            c64.dump_registers()
            if args.dump_mem:
                c64.dump_memory(args.dump_mem[0], args.dump_mem[1])

        # Run
        c64.run(max_cycles=args.max_cycles)

        # Dump final state
        c64.dump_registers()

        if args.dump_mem:
            c64.dump_memory(args.dump_mem[0], args.dump_mem[1])

        logging.getLogger("mos6502").setLevel(logging.INFO)

        # Show screen if requested
        if args.show_screen:
            c64.show_screen()

        return 0

    except Exception as e:
        if args.verbose:
            log.exception("Error")
        else:
            log.error(f"Error: {e}")  # noqa: TRY400
        return 1


if __name__ == "__main__":
    sys.exit(main())
