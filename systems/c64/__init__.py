#!/usr/bin/env python3
"""Commodore 64 Emulator using the mos6502 CPU package."""

import logging
import sys
from pathlib import Path
from typing import NamedTuple, Optional

from mos6502 import CPU, CPUVariant, errors
from mos6502.core import INFINITE_CYCLES
from mos6502.memory import Byte, Word

from c64.cartridges import (
    Cartridge,
    CartridgeTestResults,
    StaticROMCartridge,
    ErrorCartridge,
    CARTRIDGE_TYPES,
    create_cartridge,
    create_error_cartridge_rom,
    ROML_START,
    ROML_END,
    ROML_SIZE,
    ROMH_START,
    ROMH_END,
    IO1_START,
    IO1_END,
    IO2_START,
    IO2_END,
)

logging.basicConfig(level=logging.CRITICAL)
log = logging.getLogger("c64")

# Debug flags - set to True to enable verbose logging
DEBUG_CIA = False      # CIA register reads/writes
DEBUG_VIC = False      # VIC register operations
DEBUG_JIFFY = False    # Jiffy clock updates
DEBUG_KEYBOARD = False # Keyboard events
DEBUG_SCREEN = False   # Screen memory writes
DEBUG_CURSOR = False   # Cursor position variables
DEBUG_KERNAL = False   # Enable CPU logging when entering KERNAL ROM
DEBUG_BASIC = False    # Enable CPU logging when entering BASIC ROM

# Video system timing constants


class VideoTiming(NamedTuple):
    """Video system timing parameters for VIC-II chip variants.

    VIC-II Chip Variants:
        6569 (PAL)       - Europe, Australia (312 lines, 63 cycles/line, ~50Hz)
        6567R8 (NTSC)    - North America 1984+ (263 lines, 65 cycles/line, ~60Hz)
        6567R56A (NTSC)  - North America 1982-1984 (262 lines, 64 cycles/line, ~60Hz)

    Access standard timing configurations via class attributes:
        VideoTiming.VIC_6569     - PAL chip
        VideoTiming.VIC_6567R8   - New NTSC chip (default for NTSC)
        VideoTiming.VIC_6567R56A - Old NTSC chip
        VideoTiming.PAL          - Alias for VIC_6569
        VideoTiming.NTSC         - Alias for VIC_6567R8
    """
    chip_name: str          # VIC-II chip identifier (6569, 6567R8, 6567R56A)
    cpu_freq: int           # CPU frequency in Hz
    refresh_hz: float       # Screen refresh rate in Hz
    cycles_per_frame: int   # CPU cycles per video frame
    cycles_per_line: int    # CPU cycles per raster line
    raster_lines: int       # Total raster lines per frame
    render_interval: float  # Seconds between frame renders (1/refresh_hz)


# VIC-II 6569 (PAL) - Europe, Australia
# More compatible with demos/games, slightly slower CPU
VideoTiming.VIC_6569 = VideoTiming(
    chip_name="6569",
    cpu_freq=985248,           # ~0.985 MHz
    refresh_hz=50.125,         # ~50 Hz
    cycles_per_frame=19656,    # 312 lines × 63 cycles
    cycles_per_line=63,
    raster_lines=312,
    render_interval=1.0 / 50.125,
)

# VIC-II 6567R8 (NTSC) - North America, Japan (1984 onwards)
# "New" NTSC chip, most common in later C64s
VideoTiming.VIC_6567R8 = VideoTiming(
    chip_name="6567R8",
    cpu_freq=1022727,          # ~1.023 MHz
    refresh_hz=59.826,         # ~60 Hz
    cycles_per_frame=17095,    # 263 lines × 65 cycles
    cycles_per_line=65,
    raster_lines=263,
    render_interval=1.0 / 59.826,
)

# VIC-II 6567R56A (NTSC) - North America (1982-1984)
# "Old" NTSC chip, found in early C64s
VideoTiming.VIC_6567R56A = VideoTiming(
    chip_name="6567R56A",
    cpu_freq=1022727,          # ~1.023 MHz
    refresh_hz=59.826,         # ~60 Hz (slightly different in reality)
    cycles_per_frame=16768,    # 262 lines × 64 cycles
    cycles_per_line=64,
    raster_lines=262,
    render_interval=1.0 / 59.826,
)

# Backwards compatibility aliases
VideoTiming.PAL = VideoTiming.VIC_6569
VideoTiming.NTSC = VideoTiming.VIC_6567R8  # Default to new NTSC chip

# Module-level constants for backwards compatibility
PAL = VideoTiming.PAL
NTSC = VideoTiming.NTSC
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

# ANSI true color (24-bit) escape sequences for exact C64 color matching
# Using 24-bit mode: \033[38;2;R;G;Bm for foreground, \033[48;2;R;G;Bm for background


def c64_to_ansi_fg(c64_color: int) -> str:
    """Convert C64 color to ANSI 24-bit true color foreground escape sequence."""
    r, g, b = COLORS[c64_color & 0x0F]
    return f"\033[38;2;{r};{g};{b}m"


def c64_to_ansi_bg(c64_color: int) -> str:
    """Convert C64 color to ANSI 24-bit true color background escape sequence."""
    r, g, b = COLORS[c64_color & 0x0F]
    return f"\033[48;2;{r};{g};{b}m"


ANSI_RESET = "\033[0m"


class ScreenDirtyTracker:
    """Track which screen cells have changed since last render.

    Optimizes rendering by only updating cells that have been modified.
    Tracks both screen RAM ($0400-$07E7) and color RAM ($D800-$DBE7).
    Also tracks VIC register changes that affect global rendering.
    """

    SCREEN_RAM_START = 0x0400
    SCREEN_RAM_END = 0x07E7
    COLOR_RAM_START = 0xD800
    COLOR_RAM_END = 0xDBE7
    VIC_START = 0xD000
    VIC_END = 0xD02E

    SCREEN_COLS = 40
    SCREEN_ROWS = 25
    SCREEN_SIZE = SCREEN_COLS * SCREEN_ROWS  # 1000 cells

    def __init__(self):
        # Track dirty cells as a set of (row, col) tuples for fast lookup
        self._dirty_cells = set()
        # Track if any VIC registers changed (requires full redraw)
        self._vic_dirty = False
        # Track if color RAM changed
        self._color_dirty_cells = set()
        # Force full redraw on first frame
        self._force_full_redraw = True
        # Previous screen state for comparison (optional optimization)
        self._prev_screen = None
        self._prev_color = None

    def mark_screen_dirty(self, addr: int) -> None:
        """Mark a screen RAM address as dirty."""
        if self.SCREEN_RAM_START <= addr <= self.SCREEN_RAM_END:
            offset = addr - self.SCREEN_RAM_START
            row = offset // self.SCREEN_COLS
            col = offset % self.SCREEN_COLS
            self._dirty_cells.add((row, col))

    def mark_color_dirty(self, addr: int) -> None:
        """Mark a color RAM address as dirty."""
        if self.COLOR_RAM_START <= addr <= self.COLOR_RAM_END:
            offset = addr - self.COLOR_RAM_START
            if offset < self.SCREEN_SIZE:
                row = offset // self.SCREEN_COLS
                col = offset % self.SCREEN_COLS
                self._color_dirty_cells.add((row, col))

    def mark_vic_dirty(self) -> None:
        """Mark VIC registers as changed (forces full redraw)."""
        self._vic_dirty = True

    def mark_address_dirty(self, addr: int) -> None:
        """Mark any address as dirty (routes to appropriate tracker)."""
        if self.SCREEN_RAM_START <= addr <= self.SCREEN_RAM_END:
            self.mark_screen_dirty(addr)
        elif self.COLOR_RAM_START <= addr <= self.COLOR_RAM_END:
            self.mark_color_dirty(addr)
        elif self.VIC_START <= addr <= self.VIC_END:
            self.mark_vic_dirty()

    def needs_full_redraw(self) -> bool:
        """Check if a full screen redraw is needed."""
        return self._force_full_redraw or self._vic_dirty

    def get_dirty_cells(self) -> set:
        """Get all dirty cells (screen + color changes combined)."""
        return self._dirty_cells | self._color_dirty_cells

    def get_dirty_rows(self) -> set:
        """Get set of row numbers that have any dirty cells."""
        dirty = self.get_dirty_cells()
        return {row for row, col in dirty}

    def has_changes(self) -> bool:
        """Check if any changes need to be rendered."""
        return (self._force_full_redraw or
                self._vic_dirty or
                len(self._dirty_cells) > 0 or
                len(self._color_dirty_cells) > 0)

    def clear(self) -> None:
        """Clear all dirty flags after rendering."""
        self._dirty_cells.clear()
        self._color_dirty_cells.clear()
        self._vic_dirty = False
        self._force_full_redraw = False

    def force_redraw(self) -> None:
        """Force a full redraw on next render."""
        self._force_full_redraw = True


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

    # BASIC memory pointers (zero page)
    # These must be updated when loading a BASIC program for RUN to work
    TXTTAB = 0x2B   # Start of BASIC program text (2 bytes, little-endian)
    VARTAB = 0x2D   # Start of BASIC variables / end of program (2 bytes)
    ARYTAB = 0x2F   # Start of BASIC arrays (2 bytes)
    STREND = 0x31   # End of BASIC arrays / bottom of strings (2 bytes)

    # KERNAL keyboard buffer (for injecting typed commands)
    KEYBOARD_BUFFER = 0x0277      # 10-byte keyboard buffer
    KEYBOARD_BUFFER_SIZE = 0x00C6 # Number of characters in buffer

    # Reset vector location
    RESET_VECTOR_ADDR = 0xFFFC

    # Cartridge memory regions
    ROML_START = 0x8000  # Low ROM (8KB) - active when EXROM=0
    ROML_END = 0x9FFF
    ROML_SIZE = 0x2000   # 8KB

    ROMH_START = 0xA000  # High ROM (8KB) - overlaps BASIC ROM area
    ROMH_END = 0xBFFF
    ROMH_SIZE = 0x2000   # 8KB

    # Cartridge auto-start signature location
    CART_SIGNATURE_ADDR = 0x8004  # "CBM80" signature for auto-start

    # CRT hardware type names (from VICE specification)
    # Type 0 is the only one we currently support
    # Source: http://rr.c64.org/wiki/CRT_ID
    CRT_HARDWARE_TYPES = {
        0: "Normal cartridge",
        1: "Action Replay",
        2: "KCS Power Cartridge",
        3: "Final Cartridge III",
        4: "Simons Basic",
        5: "Ocean type 1",
        6: "Expert Cartridge",
        7: "Fun Play, Power Play",
        8: "Super Games",
        9: "Atomic Power",
        10: "Epyx Fastload",
        11: "Westermann Learning",
        12: "Rex Utility",
        13: "Final Cartridge I",
        14: "Magic Formel",
        15: "C64 Game System, System 3",
        16: "WarpSpeed",
        17: "Dinamic",
        18: "Zaxxon, Super Zaxxon (SEGA)",
        19: "Magic Desk, Domark, HES Australia",
        20: "Super Snapshot V5",
        21: "Comal-80",
        22: "Structured Basic",
        23: "Ross",
        24: "Dela EP64",
        25: "Dela EP7x8",
        26: "Dela EP256",
        27: "Rex EP256",
        28: "Mikro Assembler",
        29: "Final Cartridge Plus",
        30: "Action Replay 4",
        31: "StarDOS",
        32: "EasyFlash",
        33: "EasyFlash X-Bank",
        34: "Capture",
        35: "Action Replay 3",
        36: "Retro Replay, Nordic Replay",
        37: "MMC64",
        38: "MMC Replay",
        39: "IDE64",
        40: "Super Snapshot V4",
        41: "IEEE488",
        42: "Game Killer",
        43: "Prophet 64",
        44: "Exos",
        45: "Freeze Frame",
        46: "Freeze Machine",
        47: "Snapshot64",
        48: "Super Explode V5",
        49: "Magic Voice",
        50: "Action Replay 2",
        51: "MACH 5",
        52: "Diashow Maker",
        53: "Pagefox",
        54: "Kingsoft Business Basic",
        55: "Silver Rock 128",
        56: "Formel 64",
        57: "RGCD",
        58: "RR-Net MK3",
        59: "Easy Calc Result",
        60: "GMod2",
        61: "MAX BASIC",
        62: "GMod3",
        63: "ZIPP-CODE 48",
        64: "Blackbox V8",
        65: "Blackbox V3",
        66: "Blackbox V4",
        67: "REX RAM Floppy",
        68: "BIS Plus",
        69: "SD Box",
        70: "MultiMAX",
        71: "Blackbox V9",
        72: "LT Kernal",
        73: "CMD RAMlink",
        74: "Drean (H.E.R.O. bootleg)",
        75: "IEEE Flash 64",
        76: "Turtle Graphics II",
        77: "Freeze Frame MK2",
        78: "Partner 64",
        79: "Hyper-BASIC MK2",
        80: "Universal Cartridge 1",
        81: "Universal Cartridge 1.5",
        82: "Universal Cartridge 2",
        83: "BMP Data Turbo 2000",
        84: "Profi-DOS",
        85: "Magic Desk 16",
    }

    @classmethod
    def args(cls, parser) -> None:
        """Add C64-specific command-line arguments to an argument parser.

        Args:
            parser: An argparse.ArgumentParser instance
        """
        # Core emulator options
        core_group = parser.add_argument_group("Core Options")
        core_group.add_argument(
            "--rom-dir",
            type=Path,
            default=Path("./roms"),
            help="Directory containing ROM files (default: ./roms)",
        )
        core_group.add_argument(
            "--display",
            type=str,
            choices=["terminal", "pygame", "headless", "repl"],
            default="pygame",
            help="Display mode: pygame (default, graphical window), terminal (ASCII art), headless (no display), or repl (interactive terminal with keyboard input). Automatically falls back to terminal if pygame unavailable.",
        )
        core_group.add_argument(
            "--scale",
            type=int,
            default=2,
            help="Pygame window scaling factor (default: 2 = 640x400)",
        )
        core_group.add_argument(
            "--video-chip",
            type=str.upper,
            choices=["6569", "6567R8", "6567R56A", "PAL", "NTSC"],
            default="6569",
            help="VIC-II chip variant: 6569 (PAL, default), 6567R8 (NTSC 1984+), "
                 "6567R56A (old NTSC 1982-1984). PAL/NTSC are aliases for 6569/6567R8.",
        )
        core_group.add_argument(
            "--no-irq",
            action="store_true",
            help="Disable IRQ injection (for debugging; system will hang waiting for IRQs)",
        )
        core_group.add_argument(
            "--throttle",
            action="store_true",
            default=True,
            help="Throttle emulation to real-time speed (default: enabled)",
        )
        core_group.add_argument(
            "--no-throttle",
            action="store_false",
            dest="throttle",
            help="Disable throttling - run at maximum speed (for benchmarks)",
        )

        # Program loading options
        program_group = parser.add_argument_group("Program Loading")
        program_group.add_argument(
            "--program",
            type=Path,
            help="Program file to load and run (.prg, .bin, etc.)",
        )
        program_group.add_argument(
            "--load-address",
            type=lambda x: int(x, 0),
            help="Override load address (hex or decimal, e.g., 0x0801 or 2049)",
        )
        program_group.add_argument(
            "--no-roms",
            action="store_true",
            help="Run without C64 ROMs (for testing standalone programs)",
        )
        program_group.add_argument(
            "--run",
            action="store_true",
            help="Auto-run program after loading (injects RUN command after boot)",
        )

        # Cartridge options
        cart_group = parser.add_argument_group("Cartridge Options")
        cart_group.add_argument(
            "--cartridge",
            type=Path,
            help="Cartridge file to load (.crt format or raw binary)",
        )
        cart_group.add_argument(
            "--cartridge-type",
            type=str.lower,
            choices=["auto", "8k", "16k", "ultimax"],
            default="auto",
            help="Cartridge type: auto (detect from file), 8k, 16k, or ultimax (default: auto)",
        )

        # Execution control options
        exec_group = parser.add_argument_group("Execution Control")
        exec_group.add_argument(
            "--max-cycles",
            type=int,
            default=INFINITE_CYCLES,
            help="Maximum CPU cycles to execute (default: infinite)",
        )
        exec_group.add_argument(
            "--stop-on-basic",
            action="store_true",
            help="Stop execution when BASIC prompt is ready (useful for benchmarking boot time)",
        )

        # Output options
        output_group = parser.add_argument_group("Output Options")
        output_group.add_argument(
            "--dump-mem",
            nargs=2,
            metavar=("START", "END"),
            type=lambda x: int(x, 0),
            help="Dump memory region after execution (hex or decimal addresses)",
        )
        output_group.add_argument(
            "--show-screen",
            action="store_true",
            help="Display screen RAM after execution (40x25 character display)",
        )
        output_group.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Enable verbose logging",
        )

        # Disassembly options
        disasm_group = parser.add_argument_group("Disassembly")
        disasm_group.add_argument(
            "--disassemble",
            type=lambda x: int(x, 0),
            metavar="ADDRESS",
            help="Disassemble at address and exit (hex or decimal)",
        )
        disasm_group.add_argument(
            "--num-instructions",
            type=int,
            default=20,
            help="Number of instructions to disassemble (default: 20)",
        )

        # Debug flag arguments
        debug_group = parser.add_argument_group("Debug Flags")
        debug_group.add_argument(
            "--debug-cia",
            action="store_true",
            help="Enable CIA register read/write logging",
        )
        debug_group.add_argument(
            "--debug-vic",
            action="store_true",
            help="Enable VIC register operation logging",
        )
        debug_group.add_argument(
            "--debug-jiffy",
            action="store_true",
            help="Enable jiffy clock update logging",
        )
        debug_group.add_argument(
            "--debug-keyboard",
            action="store_true",
            help="Enable keyboard event logging",
        )
        debug_group.add_argument(
            "--debug-screen",
            action="store_true",
            help="Enable screen memory write logging",
        )
        debug_group.add_argument(
            "--debug-cursor",
            action="store_true",
            help="Enable cursor position variable logging",
        )
        debug_group.add_argument(
            "--debug-kernal",
            action="store_true",
            help="Enable CPU logging when entering KERNAL ROM",
        )
        debug_group.add_argument(
            "--debug-basic",
            action="store_true",
            help="Enable CPU logging when entering BASIC ROM",
        )
        debug_group.add_argument(
            "--verbose-cycles",
            action="store_true",
            help="Enable per-cycle CPU logging (f/r/w/o markers) - very slow, for debugging only",
        )

    @classmethod
    def from_args(cls, args) -> "C64":
        """Create a C64 instance from parsed command-line arguments.

        Args:
            args: Parsed argparse namespace with C64 arguments

        Returns:
            Configured C64 instance
        """
        return cls(
            rom_dir=args.rom_dir,
            display_mode=args.display,
            scale=args.scale,
            enable_irq=not getattr(args, 'no_irq', False),
            video_chip=args.video_chip,
            verbose_cycles=getattr(args, 'verbose_cycles', False),
        )

    class CIA1:
        """CIA1 (Complex Interface Adapter) at $DC00-$DCFF.

        Handles:
        - Keyboard matrix scanning (Port A/B)
        - Joystick ports
        - Timer A and Timer B with multiple clock sources
        - Time-of-Day (TOD) clock
        - Serial shift register
        - IRQ generation
        """

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
            self.port_a = 0xFF  # Rows (written by KERNAL to select which rows to scan)
            self.port_b = 0xFF  # Columns (read by KERNAL to get key states)

            # Data Direction Registers
            # 0 = input, 1 = output
            self.ddr_a = 0xFF   # Port A all outputs (row selection)
            self.ddr_b = 0x00   # Port B all inputs (column sensing)

            # Timer A state
            self.timer_a_counter = 0xFFFF  # 16-bit counter
            self.timer_a_latch = 0xFFFF    # 16-bit latch (reload value)
            self.timer_a_running = False
            self.timer_a_oneshot = False   # One-shot mode (bit 3 of CRA)
            self.timer_a_pb6_mode = 0      # PB6 output mode (bits 1-2 of CRA)
            self.timer_a_cnt_mode = False  # Count CNT transitions (bit 5 of CRA)
            self.timer_a_underflowed = False  # Track underflow for Timer B chaining

            # Timer B state
            self.timer_b_counter = 0xFFFF
            self.timer_b_latch = 0xFFFF
            self.timer_b_running = False
            self.timer_b_oneshot = False   # One-shot mode (bit 3 of CRB)
            self.timer_b_pb7_mode = 0      # PB7 output mode (bits 1-2 of CRB)
            self.timer_b_input_mode = 0    # Input mode (bits 5-6 of CRB):
                                           # 0 = count CPU cycles
                                           # 1 = count CNT transitions
                                           # 2 = count Timer A underflows
                                           # 3 = count Timer A underflows when CNT high

            # Interrupt state
            self.icr_data = 0x00      # Interrupt data (which interrupts occurred)
            self.icr_mask = 0x00      # Interrupt mask (which interrupts are enabled)

            # Time-of-Day (TOD) clock
            # TOD counts in BCD format: 1/10 sec, seconds, minutes, hours
            self.tod_10ths = 0x00     # $DC08: 1/10 seconds (0-9 BCD)
            self.tod_sec = 0x00       # $DC09: seconds (0-59 BCD)
            self.tod_min = 0x00       # $DC0A: minutes (0-59 BCD)
            self.tod_hr = 0x00        # $DC0B: hours (1-12 BCD + AM/PM in bit 7)

            # TOD alarm
            self.alarm_10ths = 0x00   # Alarm 1/10 seconds
            self.alarm_sec = 0x00     # Alarm seconds
            self.alarm_min = 0x00     # Alarm minutes
            self.alarm_hr = 0x00      # Alarm hours

            # TOD control
            self.tod_running = True   # TOD clock running
            self.tod_latched = False  # TOD output latched (reading hours latches)
            self.tod_latch = [0, 0, 0, 0]  # Latched TOD values
            self.tod_write_alarm = False  # Write to alarm (bit 7 of CRB)
            self.tod_50hz = False     # 50Hz input (bit 7 of CRA)

            # TOD timing (updated via CPU cycles)
            self.tod_cycles = 0       # Cycles since last TOD tick
            self.tod_cycles_per_tick = 98525  # ~10Hz at 985248 Hz (PAL)

            # Serial shift register
            self.sdr = 0x00           # $DC0C: Serial Data Register
            self.sdr_bits_remaining = 0  # Bits left to shift
            self.sdr_output_mode = False  # True = output, False = input

            # CNT pin state (directly accessible by external hardware)
            self.cnt_pin = True       # CNT pin level (active high)
            self.cnt_last = True      # Last CNT pin state for edge detection

            # FLAG pin (directly accessible by external hardware)
            self.flag_pin = True      # FLAG pin level (directly accessible, directly clears)

            # Track last CPU cycle count for timer updates
            self.last_cycle_count = 0

        def read(self, addr) -> int:
            reg = addr & 0x0F

            # Port A ($DC00) — keyboard matrix row selection
            # WRITE: KERNAL writes row selection bits (active low)
            # READ: Returns row bits, with input rows pulled low if keys pressed
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

            # Port B ($DC01) — keyboard matrix column sensing
            # READ: KERNAL reads column bits to detect which keys are pressed in selected rows
            # Each column bit is pulled low (0) if any key in that column is pressed in a selected row
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

                                if DEBUG_KEYBOARD:
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

                    if DEBUG_CIA:
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

            # TOD 1/10 Seconds ($DC08)
            if reg == 0x08:
                if self.tod_latched:
                    result = self.tod_latch[0]
                    # Reading 10ths unlatches TOD
                    self.tod_latched = False
                else:
                    result = self.tod_10ths
                return result

            # TOD Seconds ($DC09)
            if reg == 0x09:
                if self.tod_latched:
                    return self.tod_latch[1]
                return self.tod_sec

            # TOD Minutes ($DC0A)
            if reg == 0x0A:
                if self.tod_latched:
                    return self.tod_latch[2]
                return self.tod_min

            # TOD Hours ($DC0B)
            if reg == 0x0B:
                # Reading hours latches all TOD registers
                if not self.tod_latched:
                    self.tod_latched = True
                    self.tod_latch = [self.tod_10ths, self.tod_sec, self.tod_min, self.tod_hr]
                return self.tod_latch[3]

            # Serial Data Register ($DC0C)
            if reg == 0x0C:
                return self.sdr

            # Interrupt Control Register (ICR) ($DC0D)
            if reg == 0x0D:
                # Reading ICR clears it and returns current interrupt state
                result = self.icr_data
                # Set bit 7 if any enabled interrupt has occurred
                if result & self.icr_mask:
                    result |= 0x80
                # Log ICR reads
                if DEBUG_CIA:
                    log.info(f"*** CIA1 ICR READ: data=${self.icr_data:02X}, result=${result:02X}, clearing ICR but NOT cpu.irq_pending ***")
                # Clear interrupt data after read
                self.icr_data = 0x00
                # NOTE: Do NOT clear cpu.irq_pending here! The CPU's IRQ handling mechanism
                # should manage irq_pending. The CIA ICR read only acknowledges the CIA's interrupt.
                # The CPU will clear irq_pending when the IRQ handler is called or when no interrupts remain.
                return result

            # Control Register A ($DC0E)
            if reg == 0x0E:
                result = 0x00
                if self.timer_a_running:
                    result |= 0x01
                result |= (self.timer_a_pb6_mode & 0x03) << 1
                if self.timer_a_oneshot:
                    result |= 0x08
                if self.timer_a_cnt_mode:
                    result |= 0x20
                if self.sdr_output_mode:
                    result |= 0x40
                if self.tod_50hz:
                    result |= 0x80
                return result

            # Control Register B ($DC0F)
            if reg == 0x0F:
                result = 0x00
                if self.timer_b_running:
                    result |= 0x01
                result |= (self.timer_b_pb7_mode & 0x03) << 1
                if self.timer_b_oneshot:
                    result |= 0x08
                result |= (self.timer_b_input_mode & 0x03) << 5
                if self.tod_write_alarm:
                    result |= 0x80
                return result

            # Return stored register contents for other registers
            return self.regs[reg]

        def write(self, addr, value) -> None:
            reg = addr & 0x0F
            self.regs[reg] = value

            # Port A ($DC00) — keyboard row selection
            # KERNAL writes here to select which row(s) to scan (active low)
            if reg == 0x00:
                old_port_a = self.port_a
                self.port_a = value
                if old_port_a != value and DEBUG_CIA:
                    log.info(f"*** CIA1 Port A WRITE (row select): ${value:02X} ***")

            # Port B ($DC01) — keyboard column sensing
            # Typically read-only for keyboard, but can be written (value used in output mixing)
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

            # TOD 1/10 Seconds ($DC08)
            if reg == 0x08:
                if self.tod_write_alarm:
                    self.alarm_10ths = value & 0x0F
                else:
                    self.tod_10ths = value & 0x0F
                    # Writing 10ths starts TOD clock
                    self.tod_running = True

            # TOD Seconds ($DC09)
            if reg == 0x09:
                if self.tod_write_alarm:
                    self.alarm_sec = value & 0x7F
                else:
                    self.tod_sec = value & 0x7F

            # TOD Minutes ($DC0A)
            if reg == 0x0A:
                if self.tod_write_alarm:
                    self.alarm_min = value & 0x7F
                else:
                    self.tod_min = value & 0x7F

            # TOD Hours ($DC0B)
            if reg == 0x0B:
                if self.tod_write_alarm:
                    self.alarm_hr = value
                else:
                    self.tod_hr = value
                    # Writing hours stops TOD clock until 10ths is written
                    self.tod_running = False

            # Serial Data Register ($DC0C)
            if reg == 0x0C:
                self.sdr = value
                # If in output mode, start shifting
                if self.sdr_output_mode:
                    self.sdr_bits_remaining = 8

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

            # Control Register A ($DC0E)
            if reg == 0x0E:
                # Bit 0: Start/Stop Timer A (1=start, 0=stop)
                self.timer_a_running = bool(value & 0x01)
                # Bits 1-2: PB6 output mode
                self.timer_a_pb6_mode = (value >> 1) & 0x03
                # Bit 3: One-shot mode (1=one-shot, 0=continuous)
                self.timer_a_oneshot = bool(value & 0x08)
                # Bit 4: Force load (1=load latch into counter)
                if value & 0x10:
                    self.timer_a_counter = self.timer_a_latch
                # Bit 5: Timer A input mode (0=count cycles, 1=count CNT transitions)
                self.timer_a_cnt_mode = bool(value & 0x20)
                # Bit 6: Serial port direction (0=input, 1=output)
                self.sdr_output_mode = bool(value & 0x40)
                # Bit 7: TOD frequency (0=60Hz, 1=50Hz)
                self.tod_50hz = bool(value & 0x80)
                # Update TOD tick rate based on frequency
                if self.tod_50hz:
                    self.tod_cycles_per_tick = 98525  # PAL: 985248 Hz / 10
                else:
                    self.tod_cycles_per_tick = 102273  # NTSC: 1022730 Hz / 10
                log.info(f"*** CIA1 Timer A Control: ${value:02X}, running={self.timer_a_running}, oneshot={self.timer_a_oneshot}, latch=${self.timer_a_latch:04X} ***")

            # Control Register B ($DC0F)
            if reg == 0x0F:
                # Bit 0: Start/Stop Timer B (1=start, 0=stop)
                self.timer_b_running = bool(value & 0x01)
                # Bits 1-2: PB7 output mode
                self.timer_b_pb7_mode = (value >> 1) & 0x03
                # Bit 3: One-shot mode (1=one-shot, 0=continuous)
                self.timer_b_oneshot = bool(value & 0x08)
                # Bit 4: Force load (1=load latch into counter)
                if value & 0x10:
                    self.timer_b_counter = self.timer_b_latch
                # Bits 5-6: Timer B input mode
                # 0 = count CPU cycles
                # 1 = count CNT transitions
                # 2 = count Timer A underflows
                # 3 = count Timer A underflows when CNT high
                self.timer_b_input_mode = (value >> 5) & 0x03
                # Bit 7: TOD alarm write (0=write TOD, 1=write alarm)
                self.tod_write_alarm = bool(value & 0x80)
                log.info(f"*** CIA1 Timer B Control: ${value:02X}, running={self.timer_b_running}, oneshot={self.timer_b_oneshot}, input_mode={self.timer_b_input_mode}, latch=${self.timer_b_latch:04X} ***")

        def update(self) -> None:
            """Update CIA timers and TOD based on CPU cycles.

            Called periodically to count down timers and generate interrupts.
            """
            # Calculate cycles elapsed since last update
            cycles_elapsed = self.cpu.cycles_executed - self.last_cycle_count
            self.last_cycle_count = self.cpu.cycles_executed

            # Reset Timer A underflow flag for this update cycle
            self.timer_a_underflowed = False
            timer_a_underflow_count = 0

            # Update Timer A (only counts CPU cycles if not in CNT mode)
            if self.timer_a_running and cycles_elapsed > 0 and not self.timer_a_cnt_mode:
                # Count down by elapsed cycles
                if self.timer_a_counter >= cycles_elapsed:
                    self.timer_a_counter -= cycles_elapsed
                else:
                    # Timer underflow
                    timer_a_underflow_count = (cycles_elapsed - self.timer_a_counter) // (self.timer_a_latch + 1) + 1
                    self.timer_a_underflowed = True

                    # In one-shot mode, stop timer after underflow
                    if self.timer_a_oneshot:
                        self.timer_a_counter = 0
                        self.timer_a_running = False
                    else:
                        self.timer_a_counter = self.timer_a_latch - ((cycles_elapsed - self.timer_a_counter - 1) % (self.timer_a_latch + 1))

                    # Trigger Timer A interrupt (bit 0)
                    self.icr_data |= 0x01

                    # If Timer A interrupts are enabled, signal CPU IRQ
                    if self.icr_mask & 0x01:
                        self.cpu.irq_pending = True

            # Update Timer B
            if self.timer_b_running:
                decrement = 0

                # Determine clock source for Timer B
                if self.timer_b_input_mode == 0:
                    # Mode 0: Count CPU cycles
                    decrement = cycles_elapsed
                elif self.timer_b_input_mode == 1:
                    # Mode 1: Count CNT transitions (not implemented for now)
                    pass
                elif self.timer_b_input_mode == 2:
                    # Mode 2: Count Timer A underflows
                    decrement = timer_a_underflow_count
                elif self.timer_b_input_mode == 3:
                    # Mode 3: Count Timer A underflows when CNT high
                    if self.cnt_pin:
                        decrement = timer_a_underflow_count

                if decrement > 0:
                    if self.timer_b_counter >= decrement:
                        self.timer_b_counter -= decrement
                    else:
                        # Timer underflow
                        # In one-shot mode, stop timer after underflow
                        if self.timer_b_oneshot:
                            self.timer_b_counter = 0
                            self.timer_b_running = False
                        else:
                            if self.timer_b_input_mode == 0:
                                # CPU cycle mode - handle multiple underflows
                                self.timer_b_counter = self.timer_b_latch - ((decrement - self.timer_b_counter - 1) % (self.timer_b_latch + 1))
                            else:
                                # Timer A underflow mode - simpler reload
                                self.timer_b_counter = self.timer_b_latch

                        # Trigger Timer B interrupt (bit 1)
                        self.icr_data |= 0x02

                        # If Timer B interrupts are enabled, signal CPU IRQ
                        if self.icr_mask & 0x02:
                            self.cpu.irq_pending = True

            # Update TOD clock
            if self.tod_running:
                self.tod_cycles += cycles_elapsed
                while self.tod_cycles >= self.tod_cycles_per_tick:
                    self.tod_cycles -= self.tod_cycles_per_tick
                    self._tick_tod()

        def _tick_tod(self) -> None:
            """Advance TOD clock by 1/10 second."""
            # Increment 1/10 seconds (BCD)
            self.tod_10ths = (self.tod_10ths + 1) & 0x0F
            if self.tod_10ths > 9:
                self.tod_10ths = 0

                # Increment seconds (BCD)
                sec_lo = (self.tod_sec & 0x0F) + 1
                sec_hi = (self.tod_sec >> 4) & 0x07
                if sec_lo > 9:
                    sec_lo = 0
                    sec_hi += 1
                if sec_hi > 5:
                    sec_hi = 0

                    # Increment minutes (BCD)
                    min_lo = (self.tod_min & 0x0F) + 1
                    min_hi = (self.tod_min >> 4) & 0x07
                    if min_lo > 9:
                        min_lo = 0
                        min_hi += 1
                    if min_hi > 5:
                        min_hi = 0

                        # Increment hours (BCD with AM/PM)
                        hr_lo = (self.tod_hr & 0x0F) + 1
                        hr_hi = (self.tod_hr >> 4) & 0x01
                        pm = bool(self.tod_hr & 0x80)

                        if hr_lo > 9:
                            hr_lo = 0
                            hr_hi += 1

                        # Handle 12-hour rollover
                        hr_val = hr_hi * 10 + hr_lo
                        if hr_val == 12:
                            pm = not pm
                        elif hr_val == 13:
                            hr_lo = 1
                            hr_hi = 0

                        self.tod_hr = (0x80 if pm else 0x00) | (hr_hi << 4) | hr_lo

                    self.tod_min = (min_hi << 4) | min_lo
                self.tod_sec = (sec_hi << 4) | sec_lo

            # Check for alarm match
            if (self.tod_10ths == self.alarm_10ths and
                self.tod_sec == self.alarm_sec and
                self.tod_min == self.alarm_min and
                self.tod_hr == self.alarm_hr):
                # Trigger TOD alarm interrupt (bit 2)
                self.icr_data |= 0x04
                if self.icr_mask & 0x04:
                    self.cpu.irq_pending = True

        def _read_keyboard_port(self) -> int:
            """Read keyboard matrix columns based on selected rows.

            The C64 keyboard is an 8x8 matrix:
            - KERNAL writes to Port A ($DC00) to select row(s) - active low
            - KERNAL reads from Port B ($DC01) to get column states - active low
            - 0 = pressed, 1 = released

            The KERNAL typically scans one row at a time by setting one bit low.
            But it can also scan multiple rows simultaneously (all bits low = scan all rows).
            """
            # Port A contains the row selection (active low)
            # Each bit low = scan that row
            selected_rows = ~self.port_a & 0xFF

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
                if DEBUG_KEYBOARD:
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
        """CIA2 (Complex Interface Adapter) at $DD00-$DDFF.

        Handles:
        - VIC bank selection (Port A bits 0-1)
        - Serial bus (Port A bits 2-7)
        - User port (Port B)
        - Timer A and Timer B with multiple clock sources
        - Time-of-Day (TOD) clock
        - Serial shift register
        - NMI generation (directly to CPU)
        """

        def __init__(self, cpu) -> None:
            # 16 registers, mirrored through $DD00–$DD0F
            self.regs = [0x00] * 16

            # Reference to CPU for NMI signaling
            self.cpu = cpu

            # Port A: VIC bank selection + serial bus
            # Bits 0-1: VIC bank (active low, inverted)
            #   %00 = Bank 3 ($C000-$FFFF)
            #   %01 = Bank 2 ($8000-$BFFF)
            #   %10 = Bank 1 ($4000-$7FFF)
            #   %11 = Bank 0 ($0000-$3FFF) - default
            # Bits 2-7: Serial bus control
            self.port_a = 0x03  # Default: VIC bank 0 (bits 0-1 = %11, inverted = %00)
            self.ddr_a = 0x3F   # Default: lower 6 bits output

            # Port B: User port
            self.port_b = 0xFF
            self.ddr_b = 0x00   # Default: all inputs

            # Timer A state
            self.timer_a_counter = 0xFFFF
            self.timer_a_latch = 0xFFFF
            self.timer_a_running = False
            self.timer_a_oneshot = False
            self.timer_a_pb6_mode = 0
            self.timer_a_cnt_mode = False
            self.timer_a_underflowed = False

            # Timer B state
            self.timer_b_counter = 0xFFFF
            self.timer_b_latch = 0xFFFF
            self.timer_b_running = False
            self.timer_b_oneshot = False
            self.timer_b_pb7_mode = 0
            self.timer_b_input_mode = 0

            # Interrupt state
            self.icr_data = 0x00
            self.icr_mask = 0x00

            # Time-of-Day (TOD) clock
            self.tod_10ths = 0x00
            self.tod_sec = 0x00
            self.tod_min = 0x00
            self.tod_hr = 0x00

            # TOD alarm
            self.alarm_10ths = 0x00
            self.alarm_sec = 0x00
            self.alarm_min = 0x00
            self.alarm_hr = 0x00

            # TOD control
            self.tod_running = True
            self.tod_latched = False
            self.tod_latch = [0, 0, 0, 0]
            self.tod_write_alarm = False
            self.tod_50hz = False
            self.tod_cycles = 0
            self.tod_cycles_per_tick = 98525

            # Serial shift register
            self.sdr = 0x00
            self.sdr_bits_remaining = 0
            self.sdr_output_mode = False

            # CNT and FLAG pins
            self.cnt_pin = True
            self.cnt_last = True
            self.flag_pin = True

            # Track last CPU cycle count for timer updates
            self.last_cycle_count = 0

        def get_vic_bank(self) -> int:
            """Get the current VIC bank address (0x0000, 0x4000, 0x8000, or 0xC000).

            The VIC bank is determined by bits 0-1 of Port A, inverted.
            """
            bank_bits = (~self.port_a) & 0x03
            return bank_bits * 0x4000

        def read(self, addr) -> int:
            reg = addr & 0x0F

            # Port A ($DD00)
            if reg == 0x00:
                # Read Port A with serial bus state
                # For now, return port_a value with input bits floating high
                result = (self.port_a & self.ddr_a) | (~self.ddr_a & 0xFF)
                return result

            # Port B ($DD01) - User port
            if reg == 0x01:
                result = (self.port_b & self.ddr_b) | (~self.ddr_b & 0xFF)
                return result

            # Port A DDR ($DD02)
            if reg == 0x02:
                return self.ddr_a

            # Port B DDR ($DD03)
            if reg == 0x03:
                return self.ddr_b

            # Timer A Low Byte ($DD04)
            if reg == 0x04:
                return self.timer_a_counter & 0xFF

            # Timer A High Byte ($DD05)
            if reg == 0x05:
                return (self.timer_a_counter >> 8) & 0xFF

            # Timer B Low Byte ($DD06)
            if reg == 0x06:
                return self.timer_b_counter & 0xFF

            # Timer B High Byte ($DD07)
            if reg == 0x07:
                return (self.timer_b_counter >> 8) & 0xFF

            # TOD 1/10 Seconds ($DD08)
            if reg == 0x08:
                if self.tod_latched:
                    result = self.tod_latch[0]
                    self.tod_latched = False
                else:
                    result = self.tod_10ths
                return result

            # TOD Seconds ($DD09)
            if reg == 0x09:
                if self.tod_latched:
                    return self.tod_latch[1]
                return self.tod_sec

            # TOD Minutes ($DD0A)
            if reg == 0x0A:
                if self.tod_latched:
                    return self.tod_latch[2]
                return self.tod_min

            # TOD Hours ($DD0B)
            if reg == 0x0B:
                if not self.tod_latched:
                    self.tod_latched = True
                    self.tod_latch = [self.tod_10ths, self.tod_sec, self.tod_min, self.tod_hr]
                return self.tod_latch[3]

            # Serial Data Register ($DD0C)
            if reg == 0x0C:
                return self.sdr

            # Interrupt Control Register (ICR) ($DD0D)
            if reg == 0x0D:
                result = self.icr_data
                if result & self.icr_mask:
                    result |= 0x80
                self.icr_data = 0x00
                return result

            # Control Register A ($DD0E)
            if reg == 0x0E:
                result = 0x00
                if self.timer_a_running:
                    result |= 0x01
                result |= (self.timer_a_pb6_mode & 0x03) << 1
                if self.timer_a_oneshot:
                    result |= 0x08
                if self.timer_a_cnt_mode:
                    result |= 0x20
                if self.sdr_output_mode:
                    result |= 0x40
                if self.tod_50hz:
                    result |= 0x80
                return result

            # Control Register B ($DD0F)
            if reg == 0x0F:
                result = 0x00
                if self.timer_b_running:
                    result |= 0x01
                result |= (self.timer_b_pb7_mode & 0x03) << 1
                if self.timer_b_oneshot:
                    result |= 0x08
                result |= (self.timer_b_input_mode & 0x03) << 5
                if self.tod_write_alarm:
                    result |= 0x80
                return result

            return self.regs[reg]

        def write(self, addr, value) -> None:
            reg = addr & 0x0F
            self.regs[reg] = value

            # Port A ($DD00) - VIC bank + serial bus
            if reg == 0x00:
                old_port_a = self.port_a
                self.port_a = value
                if old_port_a != value:
                    new_bank = self.get_vic_bank()
                    log.info(f"*** CIA2 Port A WRITE: ${value:02X}, VIC bank=${new_bank:04X} ***")

            # Port B ($DD01) - User port
            if reg == 0x01:
                self.port_b = value

            # Port A DDR ($DD02)
            if reg == 0x02:
                self.ddr_a = value

            # Port B DDR ($DD03)
            if reg == 0x03:
                self.ddr_b = value

            # Timer A Low Byte ($DD04)
            if reg == 0x04:
                self.timer_a_latch = (self.timer_a_latch & 0xFF00) | value

            # Timer A High Byte ($DD05)
            if reg == 0x05:
                self.timer_a_latch = (self.timer_a_latch & 0x00FF) | (value << 8)

            # Timer B Low Byte ($DD06)
            if reg == 0x06:
                self.timer_b_latch = (self.timer_b_latch & 0xFF00) | value

            # Timer B High Byte ($DD07)
            if reg == 0x07:
                self.timer_b_latch = (self.timer_b_latch & 0x00FF) | (value << 8)

            # TOD 1/10 Seconds ($DD08)
            if reg == 0x08:
                if self.tod_write_alarm:
                    self.alarm_10ths = value & 0x0F
                else:
                    self.tod_10ths = value & 0x0F
                    self.tod_running = True

            # TOD Seconds ($DD09)
            if reg == 0x09:
                if self.tod_write_alarm:
                    self.alarm_sec = value & 0x7F
                else:
                    self.tod_sec = value & 0x7F

            # TOD Minutes ($DD0A)
            if reg == 0x0A:
                if self.tod_write_alarm:
                    self.alarm_min = value & 0x7F
                else:
                    self.tod_min = value & 0x7F

            # TOD Hours ($DD0B)
            if reg == 0x0B:
                if self.tod_write_alarm:
                    self.alarm_hr = value
                else:
                    self.tod_hr = value
                    self.tod_running = False

            # Serial Data Register ($DD0C)
            if reg == 0x0C:
                self.sdr = value
                if self.sdr_output_mode:
                    self.sdr_bits_remaining = 8

            # Interrupt Control Register ($DD0D)
            if reg == 0x0D:
                if value & 0x80:
                    self.icr_mask |= (value & 0x1F)
                else:
                    self.icr_mask &= ~(value & 0x1F)

            # Control Register A ($DD0E)
            if reg == 0x0E:
                self.timer_a_running = bool(value & 0x01)
                self.timer_a_pb6_mode = (value >> 1) & 0x03
                self.timer_a_oneshot = bool(value & 0x08)
                if value & 0x10:
                    self.timer_a_counter = self.timer_a_latch
                self.timer_a_cnt_mode = bool(value & 0x20)
                self.sdr_output_mode = bool(value & 0x40)
                self.tod_50hz = bool(value & 0x80)
                if self.tod_50hz:
                    self.tod_cycles_per_tick = 98525
                else:
                    self.tod_cycles_per_tick = 102273

            # Control Register B ($DD0F)
            if reg == 0x0F:
                self.timer_b_running = bool(value & 0x01)
                self.timer_b_pb7_mode = (value >> 1) & 0x03
                self.timer_b_oneshot = bool(value & 0x08)
                if value & 0x10:
                    self.timer_b_counter = self.timer_b_latch
                self.timer_b_input_mode = (value >> 5) & 0x03
                self.tod_write_alarm = bool(value & 0x80)

        def update(self) -> None:
            """Update CIA2 timers and TOD based on CPU cycles."""
            cycles_elapsed = self.cpu.cycles_executed - self.last_cycle_count
            self.last_cycle_count = self.cpu.cycles_executed

            self.timer_a_underflowed = False
            timer_a_underflow_count = 0

            # Update Timer A
            if self.timer_a_running and cycles_elapsed > 0 and not self.timer_a_cnt_mode:
                if self.timer_a_counter >= cycles_elapsed:
                    self.timer_a_counter -= cycles_elapsed
                else:
                    timer_a_underflow_count = (cycles_elapsed - self.timer_a_counter) // (self.timer_a_latch + 1) + 1
                    self.timer_a_underflowed = True

                    if self.timer_a_oneshot:
                        self.timer_a_counter = 0
                        self.timer_a_running = False
                    else:
                        self.timer_a_counter = self.timer_a_latch - ((cycles_elapsed - self.timer_a_counter - 1) % (self.timer_a_latch + 1))

                    self.icr_data |= 0x01
                    if self.icr_mask & 0x01:
                        # CIA2 generates NMI, not IRQ
                        self.cpu.nmi_pending = True

            # Update Timer B
            if self.timer_b_running:
                decrement = 0
                if self.timer_b_input_mode == 0:
                    decrement = cycles_elapsed
                elif self.timer_b_input_mode == 2:
                    decrement = timer_a_underflow_count
                elif self.timer_b_input_mode == 3:
                    if self.cnt_pin:
                        decrement = timer_a_underflow_count

                if decrement > 0:
                    if self.timer_b_counter >= decrement:
                        self.timer_b_counter -= decrement
                    else:
                        if self.timer_b_oneshot:
                            self.timer_b_counter = 0
                            self.timer_b_running = False
                        else:
                            if self.timer_b_input_mode == 0:
                                self.timer_b_counter = self.timer_b_latch - ((decrement - self.timer_b_counter - 1) % (self.timer_b_latch + 1))
                            else:
                                self.timer_b_counter = self.timer_b_latch

                        self.icr_data |= 0x02
                        if self.icr_mask & 0x02:
                            self.cpu.nmi_pending = True

            # Update TOD clock
            if self.tod_running:
                self.tod_cycles += cycles_elapsed
                while self.tod_cycles >= self.tod_cycles_per_tick:
                    self.tod_cycles -= self.tod_cycles_per_tick
                    self._tick_tod()

        def _tick_tod(self) -> None:
            """Advance TOD clock by 1/10 second."""
            self.tod_10ths = (self.tod_10ths + 1) & 0x0F
            if self.tod_10ths > 9:
                self.tod_10ths = 0

                sec_lo = (self.tod_sec & 0x0F) + 1
                sec_hi = (self.tod_sec >> 4) & 0x07
                if sec_lo > 9:
                    sec_lo = 0
                    sec_hi += 1
                if sec_hi > 5:
                    sec_hi = 0

                    min_lo = (self.tod_min & 0x0F) + 1
                    min_hi = (self.tod_min >> 4) & 0x07
                    if min_lo > 9:
                        min_lo = 0
                        min_hi += 1
                    if min_hi > 5:
                        min_hi = 0

                        hr_lo = (self.tod_hr & 0x0F) + 1
                        hr_hi = (self.tod_hr >> 4) & 0x01
                        pm = bool(self.tod_hr & 0x80)

                        if hr_lo > 9:
                            hr_lo = 0
                            hr_hi += 1

                        hr_val = hr_hi * 10 + hr_lo
                        if hr_val == 12:
                            pm = not pm
                        elif hr_val == 13:
                            hr_lo = 1
                            hr_hi = 0

                        self.tod_hr = (0x80 if pm else 0x00) | (hr_hi << 4) | hr_lo

                    self.tod_min = (min_hi << 4) | min_lo
                self.tod_sec = (sec_hi << 4) | sec_lo

            # Check for alarm match
            if (self.tod_10ths == self.alarm_10ths and
                self.tod_sec == self.alarm_sec and
                self.tod_min == self.alarm_min and
                self.tod_hr == self.alarm_hr):
                self.icr_data |= 0x04
                if self.icr_mask & 0x04:
                    self.cpu.nmi_pending = True

    class C64VIC:
        """
        VIC-II video chip emulation.

        Supports:
        - 40×25 character text mode (standard and multicolor)
        - Bitmap modes (320x200 hires, 160x200 multicolor)
        - Extended background color mode
        - 8 hardware sprites with collision detection
        - Border and background colors
        - $D018 screen/character memory selection
        - $D011/$D016 fine scroll
        - Raster IRQ, sprite-sprite collision IRQ, sprite-background collision IRQ
        - Light pen registers
        """

        def __init__(self, char_rom, cpu, cia2=None, video_timing: VideoTiming = None) -> None:
            self.log = logging.getLogger("c64.vic")
            self.regs = [0] * 0x40
            self.char_rom = char_rom
            self.cpu = cpu
            self.cia2 = cia2  # For VIC bank selection
            self.video_timing = video_timing if video_timing is not None else PAL

            # --- Power-on register defaults (C64 reset state-ish) -----------------
            # Sprite X positions ($D000-$D00F): all 0
            for i in range(16):
                self.regs[i] = 0x00

            # Sprite X MSB ($D010): all 0
            self.regs[0x10] = 0x00

            # $D011: Control register 1 (vertical scroll, display enable, 25-row mode)
            #  %00011011 = $1B
            self.regs[0x11] = 0x1B

            # $D012: raster low byte
            self.regs[0x12] = 0x00

            # Light pen registers ($D013-$D014)
            self.regs[0x13] = 0x00  # Light pen X
            self.regs[0x14] = 0x00  # Light pen Y

            # $D015: sprite enable (all off)
            self.regs[0x15] = 0x00

            # $D016: Control register 2 (horizontal scroll, 40-column mode)
            #  %00001000 = $08
            self.regs[0x16] = 0x08

            # $D017: sprite Y-expand (all off)
            self.regs[0x17] = 0x00

            # $D018: Memory control – start with screen at $0400, chars at $1000
            # Bits 4-7 = 0001 → 1 * $0400 = $0400 (screen RAM)
            # Bits 1-3 = 010  → 2 * $0800 = $1000 (character ROM offset)
            self.regs[0x18] = 0x14
            log.info(
                f"*** VIC INIT: Set $D018 = ${self.regs[0x18]:02X} "
                f"(screen=$0400, char=$1000) ***"
            )

            # $D019: IRQ flags – set bit 0 so KERNAL has something to clear
            self.irq_flags = 0x01

            # $D01A: IRQ enable mask
            self.irq_enabled = 0x00

            # $D01B: Sprite-to-background priority (0=sprite in front)
            self.regs[0x1B] = 0x00

            # $D01C: Sprite multicolor mode
            self.regs[0x1C] = 0x00

            # $D01D: Sprite X-expand
            self.regs[0x1D] = 0x00

            # $D01E: Sprite-sprite collision (read clears)
            self.sprite_sprite_collision = 0x00

            # $D01F: Sprite-background collision (read clears)
            self.sprite_bg_collision = 0x00

            # Colours
            # $D020: border colour – light blue (14)
            self.regs[0x20] = 0x0E
            # $D021: background colour 0 – blue (6)
            self.regs[0x21] = 0x06
            # $D022: background colour 1
            self.regs[0x22] = 0x00
            # $D023: background colour 2
            self.regs[0x23] = 0x00
            # $D024: background colour 3
            self.regs[0x24] = 0x00
            # $D025: sprite multicolor 0
            self.regs[0x25] = 0x00
            # $D026: sprite multicolor 1
            self.regs[0x26] = 0x00
            # $D027-$D02E: sprite colors
            for i in range(8):
                self.regs[0x27 + i] = 0x00

            # --- Geometry / timing -----------------------------------------------
            # Text area: 40×25 chars → 320×200 pixels
            self.text_width = 320
            self.text_height = 200

            # Choose a total frame large enough for borders; keep your 384×270
            self.total_width = 384
            self.total_height = 270

            # Center the text area within the total frame
            # This gives symmetric borders on all sides
            self.border_left = (self.total_width - self.text_width) // 2    # 32 pixels
            self.border_right = self.total_width - self.border_left - self.text_width  # 32 pixels
            self.border_top = (self.total_height - self.text_height) // 2   # 35 pixels
            self.border_bottom = self.total_height - self.border_top - self.text_height  # 35 pixels

            # Video timing from VIC-II chip variant
            # 6569 (PAL):     312 raster lines, 63 cycles/line, 19656 cycles/frame
            # 6567R8 (NTSC):  263 raster lines, 65 cycles/line, 17095 cycles/frame
            # 6567R56A (old): 262 raster lines, 64 cycles/line, 16768 cycles/frame
            self.raster_lines = self.video_timing.raster_lines
            self.cycles_per_line = self.video_timing.cycles_per_line
            self.cycles_per_frame = self.video_timing.cycles_per_frame

            # Current raster line
            self.current_raster = 0

            # Track last CPU cycle count to derive raster position
            self.last_cycle_count = 0

            # Track when the KERNAL has acknowledged the initial IRQ
            self.initialized = False

            # Light pen state
            self.light_pen_triggered = False

            # Frame-ready flag for render synchronization
            # VIC sets this when a frame completes (raster wraps to 0)
            # Pygame checks it, grabs a snapshot, and clears it
            # No blocking - VIC runs at full speed, pygame renders what it catches
            # Using multiprocessing.Event for proper cross-process visibility
            import multiprocessing
            self.frame_complete = multiprocessing.Event()

            # RAM snapshots taken at VBlank for consistent rendering
            # Only the 16KB VIC bank is snapshotted (not full 64KB) for performance
            self.ram_snapshot = None
            self.ram_snapshot_bank = 0  # Base address of snapshotted bank
            self.color_snapshot = None
            self.c64_memory = None  # Set later via set_memory()

            self.log.info(
                "VIC-II %s initialized (%d lines, %d cycles/line, %d cycles/frame)",
                self.video_timing.chip_name,
                self.raster_lines,
                self.cycles_per_line,
                self.cycles_per_frame,
            )

        def set_cia2(self, cia2) -> None:
            """Set reference to CIA2 for VIC bank selection."""
            self.cia2 = cia2

        def set_memory(self, c64_memory) -> None:
            """Set reference to C64Memory for VBlank snapshots."""
            self.c64_memory = c64_memory

        def get_vic_bank(self) -> int:
            """Get the current VIC bank address from CIA2."""
            if self.cia2:
                return self.cia2.get_vic_bank()
            return 0x0000  # Default to bank 0

        # --------------------------------------------------------------------- IRQ /
        def update(self) -> None:
            """
            Update raster position based on CPU cycles and generate raster IRQ
            when the raster counter matches the compare register.
            """
            # Derive raster from total CPU cycles; we don't try to be sub-cycle accurate.
            total_lines = self.cpu.cycles_executed // self.cycles_per_line
            new_raster = total_lines % self.raster_lines

            if new_raster != self.current_raster:
                # Detect frame completion (VBlank) when raster wraps back to 0
                # This happens when new_raster < current_raster (wrapped around)
                if new_raster < self.current_raster:
                    # Take RAM snapshot NOW while we're at VBlank
                    # This ensures consistent frame data before CPU continues
                    # Use snapshot_vic_bank() to bypass memory handler and avoid infinite recursion
                    # Only snapshot the 16KB VIC bank that's currently visible
                    if self.c64_memory:
                        vic_bank = self.get_vic_bank()
                        self.ram_snapshot = self.c64_memory.snapshot_vic_bank(vic_bank)
                        self.ram_snapshot_bank = vic_bank  # Remember bank offset for rendering
                        self.color_snapshot = bytes(self.c64_memory.ram_color)
                    # Warn if frame_complete is still set (render thread falling behind)
                    if self.frame_complete.is_set():
                        log.warning(
                            "VIC: frame_complete still set at VBlank - render thread falling behind"
                        )
                    # Signal frame complete - pygame will use the snapshot
                    self.frame_complete.set()
                # 9-bit raster compare value: low byte in $D012, bit 8 in $D011 bit 7
                compare = self.regs[0x12] | ((self.regs[0x11] & 0x80) << 1)

                if new_raster == compare:
                    # Always set the raster IRQ flag when raster matches compare value
                    # This flag is set regardless of whether IRQ is enabled
                    # (The enable bit only controls whether an actual interrupt fires)
                    # This is critical for PAL/NTSC detection which reads $D019
                    self.irq_flags |= 0x01

                    log.info(
                        "*** VIC RASTER MATCH: line %d == compare %d, irq_enabled=$%02X "
                        "(bit0=%s), irq_flags now=$%02X ***",
                        new_raster,
                        compare,
                        self.irq_enabled,
                        "set" if (self.irq_enabled & 0x01) else "clear",
                        self.irq_flags,
                    )

                    if self.irq_enabled & 0x01:
                        # Tell CPU an IRQ is pending
                        self.cpu.irq_pending = True
                        log.info(
                            "*** VIC TRIGGERING IRQ: raster line %d, "
                            "cpu.irq_pending=True, cycles=%d ***",
                            new_raster,
                            self.cpu.cycles_executed,
                        )
                        self.log.debug(
                            "VIC raster IRQ: line %d, setting cpu.irq_pending=True",
                            new_raster,
                        )

            self.current_raster = new_raster

        # ---------------------------------------------------------------- Register I/O /
        def read(self, addr) -> int:
            reg = addr & 0x3F

            # $D011: Control register 1 (bit 7 is raster bit 8)
            if reg == 0x11:
                # Bit 7 is raster line bit 8
                result = self.regs[0x11] & 0x7F
                if self.current_raster > 255:
                    result |= 0x80
                return result

            # $D012: raster counter (low 8 bits)
            if reg == 0x12:
                self.update()
                return self.current_raster & 0xFF

            # $D018: handy debug decode
            if reg == 0x18:
                val = self.regs[reg]
                screen_addr = ((val & 0xF0) >> 4) * 0x0400
                char_offset = ((val & 0x0E) >> 1) * 0x0800
                log.info(
                    "*** VIC $D018 READ: value=$%02X, screen=$%04X, char_offset=$%04X ***",
                    val,
                    screen_addr,
                    char_offset,
                )

            # $D019: IRQ flags
            if reg == 0x19:
                flags = self.irq_flags & 0x0F
                if flags:
                    flags |= 0x80  # bit 7 set if any IRQ occurred
                return flags

            # $D01E: Sprite-sprite collision (cleared on read)
            if reg == 0x1E:
                result = self.sprite_sprite_collision
                self.sprite_sprite_collision = 0x00
                return result

            # $D01F: Sprite-background collision (cleared on read)
            if reg == 0x1F:
                result = self.sprite_bg_collision
                self.sprite_bg_collision = 0x00
                return result

            return self.regs[reg]

        def write(self, addr, val) -> None:
            reg = addr & 0x3F
            self.regs[reg] = val & 0xFF

            # $D012: raster compare low byte
            if reg == 0x12:
                compare = val | ((self.regs[0x11] & 0x80) << 1)
                log.info(
                    "*** VIC RASTER COMPARE: $D012 = $%02X, full compare value = %d ***",
                    val,
                    compare,
                )

            # $D011: control register (contains raster compare bit 8 as bit 7)
            if reg == 0x11:
                compare = self.regs[0x12] | ((val & 0x80) << 1)
                log.info(
                    "*** VIC CONTROL: $D011 = $%02X, raster compare = %d ***",
                    val,
                    compare,
                )

            # $D018: memory control (screen + char memory)
            if reg == 0x18:
                screen_addr = ((val & 0xF0) >> 4) * 0x0400
                char_offset = ((val & 0x0E) >> 1) * 0x0800
                log.info(
                    "*** VIC $D018 WRITE: value=$%02X, screen=$%04X, char_offset=$%04X ***",
                    val,
                    screen_addr,
                    char_offset,
                )

            # $D019: IRQ flags — write 1 to clear corresponding bits
            if reg == 0x19:
                was_set = self.irq_flags & 0x0F
                self.irq_flags &= ~(val & 0x0F)

                if (self.irq_flags & 0x0F) == 0:
                    # All IRQ sources cleared, let CPU drop its pending flag
                    self.cpu.irq_pending = False
                    self.log.debug("VIC IRQ acknowledged, cpu.irq_pending cleared")

                # Detect completion of KERNAL's initial IRQ sequence
                if not self.initialized and was_set and (self.irq_flags & 0x0F) == 0:
                    self.initialized = True
                    self.log.info("VIC-II initialization complete (IRQ acknowledged)")

            # $D01A: IRQ enable mask
            if reg == 0x1A:
                self.irq_enabled = val & 0x0F
                log.info(
                    "*** VIC IRQ ENABLE: $D01A = $%02X, irq_enabled=$%02X, "
                    "raster IRQ %s ***",
                    val,
                    self.irq_enabled,
                    "ENABLED" if (self.irq_enabled & 0x01) else "DISABLED",
                )

        # ---------------------------------------------------------------- Rendering /
        def render_frame(self, surface, ram, color_ram) -> None:
            """
            Render a full frame into the given pygame surface.

            Supports:
            - Standard character mode (40x25)
            - Multicolor character mode
            - Extended background color mode
            - Standard bitmap mode (320x200)
            - Multicolor bitmap mode (160x200)
            - 8 hardware sprites with priority and collision
            """
            # Border colour
            border_color = self.regs[0x20] & 0x0F
            surface.fill(COLORS[border_color])

            # Get VIC bank from CIA2
            vic_bank = self.get_vic_bank()

            # Decode $D018: video matrix base + character/bitmap offset
            mem_control = self.regs[0x18]

            # Bits 4-7: screen base in 1 KB blocks (within VIC bank)
            screen_base = vic_bank + ((mem_control & 0xF0) >> 4) * 0x0400

            # Bits 1-3: char/bitmap base in 2 KB blocks (within VIC bank)
            char_bank_offset = ((mem_control & 0x0E) >> 1) * 0x0800

            # Mode flags from $D011 and $D016
            ecm = bool(self.regs[0x11] & 0x40)  # Extended Color Mode
            bmm = bool(self.regs[0x11] & 0x20)  # Bitmap Mode
            den = bool(self.regs[0x11] & 0x10)  # Display Enable
            mcm = bool(self.regs[0x16] & 0x10)  # Multicolor Mode

            # Background colours
            bg_colors = [
                self.regs[0x21] & 0x0F,
                self.regs[0x22] & 0x0F,
                self.regs[0x23] & 0x0F,
                self.regs[0x24] & 0x0F,
            ]

            # Fine scroll values
            hscroll = self.regs[0x16] & 0x07
            vscroll = self.regs[0x11] & 0x07

            x_origin = self.border_left - hscroll
            y_origin = self.border_top - vscroll

            if not den:
                # Display disabled - just show border
                return

            if bmm:
                # Bitmap mode
                bitmap_base = vic_bank + char_bank_offset
                if mcm:
                    self._render_multicolor_bitmap(surface, ram, color_ram, bitmap_base, screen_base, bg_colors[0], x_origin, y_origin)
                else:
                    self._render_hires_bitmap(surface, ram, bitmap_base, screen_base, x_origin, y_origin)
            elif ecm:
                # Extended background color mode
                self._render_ecm_text(surface, ram, color_ram, char_bank_offset, screen_base, bg_colors, x_origin, y_origin)
            elif mcm:
                # Multicolor text mode
                self._render_multicolor_text(surface, ram, color_ram, char_bank_offset, screen_base, bg_colors, x_origin, y_origin)
            else:
                # Standard text mode
                self._render_standard_text(surface, ram, color_ram, char_bank_offset, screen_base, bg_colors[0], x_origin, y_origin)

            # Render sprites on top
            self._render_sprites(surface, ram, vic_bank, screen_base, x_origin, y_origin)

        def _render_standard_text(self, surface, ram, color_ram, char_offset, screen_base, bg_color, x_origin, y_origin):
            """Render standard 40x25 text mode."""
            for row in range(25):
                for col in range(40):
                    cell_addr = screen_base + row * 40 + col
                    char_code = ram[cell_addr]

                    color_offset = row * 40 + col
                    color = color_ram[color_offset] & 0x0F

                    # Reverse video if bit 7 set
                    reverse = char_code & 0x80
                    char_code &= 0x7F

                    # Fetch 8×8 glyph from char ROM
                    glyph_addr = (char_code * 8) + char_offset
                    glyph_addr &= 0x0FFF
                    glyph = self.char_rom[glyph_addr : glyph_addr + 8]

                    base_x = x_origin + col * 8
                    base_y = y_origin + row * 8

                    for y in range(8):
                        line = glyph[y]
                        for x in range(8):
                            bit = (line >> (7 - x)) & 0x01

                            if reverse:
                                fg = COLORS[bg_color]
                                bg = COLORS[color]
                            else:
                                fg = COLORS[color]
                                bg = COLORS[bg_color]

                            surface.set_at((base_x + x, base_y + y), fg if bit else bg)

        def _render_multicolor_text(self, surface, ram, color_ram, char_offset, screen_base, bg_colors, x_origin, y_origin):
            """Render multicolor text mode (MCM=1, BMM=0, ECM=0)."""
            for row in range(25):
                for col in range(40):
                    cell_addr = screen_base + row * 40 + col
                    char_code = ram[cell_addr]

                    color_offset = row * 40 + col
                    char_color = color_ram[color_offset] & 0x0F

                    # If color bit 3 is set, use multicolor mode for this cell
                    use_multicolor = char_color & 0x08

                    glyph_addr = (char_code * 8) + char_offset
                    glyph_addr &= 0x0FFF
                    glyph = self.char_rom[glyph_addr : glyph_addr + 8]

                    base_x = x_origin + col * 8
                    base_y = y_origin + row * 8

                    for y in range(8):
                        line = glyph[y]
                        if use_multicolor:
                            # Multicolor: 4 double-width pixels
                            for x in range(4):
                                bits = (line >> (6 - x * 2)) & 0x03
                                if bits == 0:
                                    c = COLORS[bg_colors[0]]
                                elif bits == 1:
                                    c = COLORS[bg_colors[1]]
                                elif bits == 2:
                                    c = COLORS[bg_colors[2]]
                                else:
                                    c = COLORS[char_color & 0x07]
                                surface.set_at((base_x + x * 2, base_y + y), c)
                                surface.set_at((base_x + x * 2 + 1, base_y + y), c)
                        else:
                            # Standard: 8 single-width pixels
                            for x in range(8):
                                bit = (line >> (7 - x)) & 0x01
                                c = COLORS[char_color] if bit else COLORS[bg_colors[0]]
                                surface.set_at((base_x + x, base_y + y), c)

        def _render_ecm_text(self, surface, ram, color_ram, char_offset, screen_base, bg_colors, x_origin, y_origin):
            """Render extended background color mode (ECM=1, BMM=0, MCM=0)."""
            for row in range(25):
                for col in range(40):
                    cell_addr = screen_base + row * 40 + col
                    char_code = ram[cell_addr]

                    color_offset = row * 40 + col
                    char_color = color_ram[color_offset] & 0x0F

                    # Bits 6-7 select background color
                    bg_select = (char_code >> 6) & 0x03
                    char_code &= 0x3F  # Only 64 characters available

                    glyph_addr = (char_code * 8) + char_offset
                    glyph_addr &= 0x0FFF
                    glyph = self.char_rom[glyph_addr : glyph_addr + 8]

                    base_x = x_origin + col * 8
                    base_y = y_origin + row * 8

                    for y in range(8):
                        line = glyph[y]
                        for x in range(8):
                            bit = (line >> (7 - x)) & 0x01
                            c = COLORS[char_color] if bit else COLORS[bg_colors[bg_select]]
                            surface.set_at((base_x + x, base_y + y), c)

        def _render_hires_bitmap(self, surface, ram, bitmap_base, screen_base, x_origin, y_origin):
            """Render standard hires bitmap mode (320x200, BMM=1, MCM=0)."""
            for char_row in range(25):
                for char_col in range(40):
                    # Get colors from screen RAM
                    cell_addr = screen_base + char_row * 40 + char_col
                    color_byte = ram[cell_addr]
                    fg_color = (color_byte >> 4) & 0x0F
                    bg_color = color_byte & 0x0F

                    # Get 8 bytes of bitmap data
                    bitmap_addr = bitmap_base + char_row * 320 + char_col * 8

                    base_x = x_origin + char_col * 8
                    base_y = y_origin + char_row * 8

                    for y in range(8):
                        byte_val = ram[bitmap_addr + y]
                        for x in range(8):
                            bit = (byte_val >> (7 - x)) & 0x01
                            c = COLORS[fg_color] if bit else COLORS[bg_color]
                            surface.set_at((base_x + x, base_y + y), c)

        def _render_multicolor_bitmap(self, surface, ram, color_ram, bitmap_base, screen_base, bg_color, x_origin, y_origin):
            """Render multicolor bitmap mode (160x200, BMM=1, MCM=1)."""
            for char_row in range(25):
                for char_col in range(40):
                    # Get colors
                    cell_addr = screen_base + char_row * 40 + char_col
                    color_byte = ram[cell_addr]
                    color1 = (color_byte >> 4) & 0x0F
                    color2 = color_byte & 0x0F
                    color3 = color_ram[char_row * 40 + char_col] & 0x0F

                    colors = [bg_color, color1, color2, color3]

                    bitmap_addr = bitmap_base + char_row * 320 + char_col * 8

                    base_x = x_origin + char_col * 8
                    base_y = y_origin + char_row * 8

                    for y in range(8):
                        byte_val = ram[bitmap_addr + y]
                        for x in range(4):
                            bits = (byte_val >> (6 - x * 2)) & 0x03
                            c = COLORS[colors[bits]]
                            surface.set_at((base_x + x * 2, base_y + y), c)
                            surface.set_at((base_x + x * 2 + 1, base_y + y), c)

        def _render_sprites(self, surface, ram, vic_bank, screen_base, x_origin, y_origin):
            """Render all 8 sprites with priority handling."""
            sprite_enable = self.regs[0x15]
            sprite_priority = self.regs[0x1B]  # 0 = sprite in front, 1 = behind
            sprite_multicolor = self.regs[0x1C]
            sprite_x_expand = self.regs[0x1D]
            sprite_y_expand = self.regs[0x17]
            sprite_x_msb = self.regs[0x10]

            mc_color0 = self.regs[0x25] & 0x0F
            mc_color1 = self.regs[0x26] & 0x0F

            # Sprite pointer base is at end of screen RAM
            sprite_ptr_base = screen_base + 0x3F8

            # Render sprites from 7 to 0 (lower numbers have higher priority)
            for sprite_num in range(7, -1, -1):
                if not (sprite_enable & (1 << sprite_num)):
                    continue

                # Get sprite position
                x_pos = self.regs[sprite_num * 2]
                if sprite_x_msb & (1 << sprite_num):
                    x_pos += 256
                y_pos = self.regs[sprite_num * 2 + 1]

                # Convert to screen coordinates
                sprite_x = x_pos - 24 + self.border_left
                sprite_y = y_pos - 50 + self.border_top

                # Get sprite data pointer
                sprite_ptr = ram[sprite_ptr_base + sprite_num]
                sprite_data_addr = vic_bank + sprite_ptr * 64

                # Get sprite color
                sprite_color = self.regs[0x27 + sprite_num] & 0x0F

                # Check expand flags
                x_expand = bool(sprite_x_expand & (1 << sprite_num))
                y_expand = bool(sprite_y_expand & (1 << sprite_num))
                is_multicolor = bool(sprite_multicolor & (1 << sprite_num))

                # Render 21 lines of 24 pixels (3 bytes per line)
                for line in range(21):
                    y_screen = sprite_y + line * (2 if y_expand else 1)
                    if y_expand:
                        y_screen2 = y_screen + 1

                    for byte_idx in range(3):
                        byte_val = ram[sprite_data_addr + line * 3 + byte_idx]

                        if is_multicolor:
                            # Multicolor: 4 double-width pixels per byte
                            for px in range(4):
                                bits = (byte_val >> (6 - px * 2)) & 0x03
                                if bits == 0:
                                    continue  # Transparent
                                elif bits == 1:
                                    c = COLORS[mc_color0]
                                elif bits == 2:
                                    c = COLORS[sprite_color]
                                else:
                                    c = COLORS[mc_color1]

                                x_screen = sprite_x + byte_idx * 8 + px * 2
                                if x_expand:
                                    x_screen *= 2
                                    for dx in range(4):
                                        self._set_sprite_pixel(surface, x_screen + dx, y_screen, c)
                                        if y_expand:
                                            self._set_sprite_pixel(surface, x_screen + dx, y_screen2, c)
                                else:
                                    self._set_sprite_pixel(surface, x_screen, y_screen, c)
                                    self._set_sprite_pixel(surface, x_screen + 1, y_screen, c)
                                    if y_expand:
                                        self._set_sprite_pixel(surface, x_screen, y_screen2, c)
                                        self._set_sprite_pixel(surface, x_screen + 1, y_screen2, c)
                        else:
                            # Standard: 8 single-width pixels per byte
                            for px in range(8):
                                if not (byte_val & (0x80 >> px)):
                                    continue  # Transparent

                                c = COLORS[sprite_color]
                                x_screen = sprite_x + byte_idx * 8 + px
                                if x_expand:
                                    x_screen *= 2
                                    self._set_sprite_pixel(surface, x_screen, y_screen, c)
                                    self._set_sprite_pixel(surface, x_screen + 1, y_screen, c)
                                    if y_expand:
                                        self._set_sprite_pixel(surface, x_screen, y_screen2, c)
                                        self._set_sprite_pixel(surface, x_screen + 1, y_screen2, c)
                                else:
                                    self._set_sprite_pixel(surface, x_screen, y_screen, c)
                                    if y_expand:
                                        self._set_sprite_pixel(surface, x_screen, y_screen2, c)

        def _set_sprite_pixel(self, surface, x, y, color):
            """Set a sprite pixel with bounds checking."""
            if 0 <= x < self.total_width and 0 <= y < self.total_height:
                surface.set_at((x, y), color)

    class C64Memory:
        def __init__(self, ram, *, basic_rom, kernal_rom, char_rom, cia1, cia2, vic, dirty_tracker=None) -> None:
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
            self.dirty_tracker = dirty_tracker

            # Color RAM - 1000 bytes ($D800-$DBE7), only low 4 bits used
            self.ram_color = bytearray(1024)

            # CPU I/O port
            self.ddr = 0x00  # $0000
            self.port = 0x37  # $0001 default value

            # Cartridge support - set by C64.load_cartridge()
            # The Cartridge object handles all banking logic and provides
            # EXROM/GAME signals and read methods for ROML/ROMH/IO regions
            self.cartridge: Optional[Cartridge] = None

        def _read_ram_direct(self, addr) -> int:
            """Read directly from RAM storage without delegation."""
            # RAM lists now store plain ints, not Byte objects
            if 0 <= addr < 256:
                return self.ram_zeropage[addr]
            elif 256 <= addr < 512:
                return self.ram_stack[addr - 256]
            elif addr <= 65535:
                return self.ram_heap[addr - 512]
            return 0

        def _write_ram_direct(self, addr, value) -> None:
            """Write directly to RAM storage without delegation."""
            # RAM lists now store plain ints, not Byte objects
            int_value = int(value) & 0xFF
            if 0 <= addr < 256:
                self.ram_zeropage[addr] = int_value
            elif 256 <= addr < 512:
                self.ram_stack[addr - 256] = int_value
            elif addr <= 65535:
                self.ram_heap[addr - 512] = int_value

        def snapshot_ram(self) -> bytes:
            """Create a fast RAM snapshot by directly accessing underlying storage.

            This bypasses the memory handler to avoid triggering VIC/CIA reads
            and the infinite recursion that would cause. The snapshot captures
            the raw RAM state, not the banked view the CPU sees.

            Returns:
                65536 bytes representing the full 64KB RAM.
            """
            # Concatenate the three RAM regions directly - no memory handler involved
            # This is O(n) but avoids 65536 individual memory handler calls
            return bytes(self.ram_zeropage) + bytes(self.ram_stack) + bytes(self.ram_heap)

        def snapshot_vic_bank(self, vic_bank: int) -> bytes:
            """Create a fast snapshot of only the 16KB VIC bank the VIC can see.

            The VIC can only see 16KB of RAM at a time, selected by CIA2:
            - Bank 0: $0000-$3FFF (includes screen at $0400)
            - Bank 1: $4000-$7FFF
            - Bank 2: $8000-$BFFF
            - Bank 3: $C000-$FFFF

            Arguments:
                vic_bank: Base address of VIC bank (0x0000, 0x4000, 0x8000, or 0xC000)

            Returns:
                16384 bytes representing the 16KB VIC bank.
            """
            # Use slice operations for speed instead of byte-by-byte copy
            # RAM layout: zeropage[0:256], stack[256:512], heap[512:65536]
            bank_size = 0x4000  # 16KB

            if vic_bank == 0x0000:
                # Bank 0: $0000-$3FFF (zeropage + stack + heap[0:0x3E00])
                return (bytes(self.ram_zeropage) +
                        bytes(self.ram_stack) +
                        bytes(self.ram_heap[:bank_size - 512]))
            elif vic_bank == 0x4000:
                # Bank 1: $4000-$7FFF (all from heap)
                heap_start = vic_bank - 512
                return bytes(self.ram_heap[heap_start:heap_start + bank_size])
            elif vic_bank == 0x8000:
                # Bank 2: $8000-$BFFF (all from heap)
                heap_start = vic_bank - 512
                return bytes(self.ram_heap[heap_start:heap_start + bank_size])
            else:  # vic_bank == 0xC000
                # Bank 3: $C000-$FFFF (all from heap)
                heap_start = vic_bank - 512
                return bytes(self.ram_heap[heap_start:heap_start + bank_size])

        def snapshot_screen_area(self, screen_base: int, bitmap_mode: bool = False) -> bytes:
            """Create a minimal snapshot of just the video memory the VIC needs.

            For text mode: Just 1024 bytes at screen_base (1000 chars + sprite ptrs)
            For bitmap mode: 8192 bytes of bitmap data + 1024 bytes screen/color info

            Arguments:
                screen_base: Starting address of screen RAM (e.g., 0x0400)
                bitmap_mode: If True, snapshot includes 8KB bitmap data

            Returns:
                Snapshot of just the visible screen area.
            """
            # Screen RAM is 1000 bytes (40*25), but we grab 1024 to include
            # sprite pointers at screen+$3F8 (8 bytes)
            size = 0x2400 if bitmap_mode else 0x0400  # 9KB or 1KB

            return self._snapshot_range(screen_base, size)

        def _snapshot_range(self, start: int, size: int) -> bytes:
            """Snapshot a specific memory range directly from RAM storage.

            Arguments:
                start: Starting address
                size: Number of bytes to snapshot

            Returns:
                bytes object containing the memory range
            """
            end = start + size

            # Fast path: entire range is in heap (addresses >= 512)
            # This is the common case for screen RAM at $0400, $0800, etc.
            if start >= 512:
                heap_start = start - 512
                heap_end = end - 512
                return bytes(self.ram_heap[heap_start:heap_end])

            # Slow path: range spans multiple regions (rare)
            result = bytearray(size)
            for addr in range(start, end):
                offset = addr - start
                if addr < 256:
                    result[offset] = self.ram_zeropage[addr]
                elif addr < 512:
                    result[offset] = self.ram_stack[addr - 256]
                else:
                    result[offset] = self.ram_heap[addr - 512]

            return bytes(result)

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
            # Cartridge I/O1 ($DE00-$DEFF)
            if IO1_START <= addr <= IO1_END:
                if self.cartridge is not None:
                    return self.cartridge.read_io1(addr)
                return 0xFF
            # Cartridge I/O2 ($DF00-$DFFF)
            if IO2_START <= addr <= IO2_END:
                if self.cartridge is not None:
                    return self.cartridge.read_io2(addr)
                return 0xFF
            return 0xFF

        def read(self, addr) -> int:
            # CPU internal port
            if addr == 0x0000: return self.ddr
            if addr == 0x0001:
                # Bits with DDR=0 read as 1
                return (self.port | (~self.ddr)) & 0xFF

            # $0002-$7FFF is ALWAYS RAM (never banked on C64)
            # This includes zero page, stack, KERNAL/BASIC working storage, and screen RAM
            if 0x0002 <= addr <= 0x7FFF:
                return self._read_ram_direct(addr)

            # Cartridge ROML ($8000-$9FFF)
            # Visible when EXROM=0 (8KB/16KB modes) or in Ultimax mode (EXROM=1, GAME=0)
            # This has priority over RAM in this region
            if ROML_START <= addr <= ROML_END:
                if self.cartridge is not None:
                    # ROML visible in 8KB mode (EXROM=0, GAME=1)
                    # ROML visible in 16KB mode (EXROM=0, GAME=0)
                    # ROML visible in Ultimax mode (EXROM=1, GAME=0) if present
                    if not self.cartridge.exrom or (self.cartridge.exrom and not self.cartridge.game):
                        return self.cartridge.read_roml(addr)
                # No cartridge or ROML not visible, fall through to RAM
                return self._read_ram_direct(addr)

            # Memory banking logic (only applies to $A000-$FFFF)
            io_enabled = self.port & 0b00000100
            basic_enabled = self.port & 0b00000001
            kernal_enabled = self.port & 0b00000010

            # Cartridge ROMH ($A000-$BFFF) - visible when EXROM=0 AND GAME=0 (16KB mode)
            # Takes priority over BASIC ROM
            if ROMH_START <= addr <= ROMH_END:
                if self.cartridge is not None and not self.cartridge.exrom and not self.cartridge.game:
                    return self.cartridge.read_romh(addr)
                # Fall through to BASIC ROM check
                if basic_enabled:
                    return self.basic[addr - C64.BASIC_ROM_START]
                # RAM fallback
                return self._read_ram_direct(addr)

            # KERNAL ROM ($E000-$FFFF)
            # In Ultimax mode (EXROM=1, GAME=0), cartridge ROM replaces KERNAL
            if C64.KERNAL_ROM_START <= addr <= C64.KERNAL_ROM_END:
                if self.cartridge is not None and self.cartridge.exrom and not self.cartridge.game:
                    # Ultimax mode: cartridge ROM at $E000-$FFFF
                    return self.cartridge.read_ultimax_romh(addr)
                if kernal_enabled:
                    return self.kernal[addr - C64.KERNAL_ROM_START]
                # RAM fallback when KERNAL disabled
                return self._read_ram_direct(addr)

            # I/O or CHAR ROM ($D000-$DFFF)
            if C64.CHAR_ROM_START <= addr <= C64.CHAR_ROM_END:
                if io_enabled:
                    return self._read_io_area(addr)
                else:
                    return self.char[addr - C64.CHAR_ROM_START]

            # RAM fallback (for $C000-$CFFF and $A000-$FFFF when banking is off)
            return self._read_ram_direct(addr)

        def _write_io_area(self, addr: int, value: int) -> None:
            """Write to I/O area ($D000-$DFFF)."""
            # VIC registers
            if 0xD000 <= addr <= 0xD3FF:
                self.vic.write(addr, value)
                # Track VIC register changes (may affect global rendering)
                if self.dirty_tracker is not None and addr <= 0xD02E:
                    self.dirty_tracker.mark_vic_dirty()
                return
            # SID registers (stub)
            if 0xD400 <= addr <= 0xD7FF:
                return  # Ignore writes to SID
            # Color RAM
            if 0xD800 <= addr <= 0xDBFF:
                self.ram_color[addr - 0xD800] = value & 0x0F  # Only 4 bits
                # Track color RAM changes
                if self.dirty_tracker is not None:
                    self.dirty_tracker.mark_color_dirty(addr)
                return
            # CIA1
            if 0xDC00 <= addr <= 0xDCFF:
                self.cia1.write(addr, value)
                return
            # CIA2
            if 0xDD00 <= addr <= 0xDDFF:
                self.cia2.write(addr, value)
                return
            # Cartridge I/O1 ($DE00-$DEFF) - bank switching registers for many cartridge types
            if IO1_START <= addr <= IO1_END:
                if self.cartridge is not None:
                    self.cartridge.write_io1(addr, value)
                return
            # Cartridge I/O2 ($DF00-$DFFF)
            if IO2_START <= addr <= IO2_END:
                if self.cartridge is not None:
                    self.cartridge.write_io2(addr, value)
                return

        def write(self, addr, value) -> None:
            """Write to C64 memory with banking logic."""
            # Temporary debug: log ALL write calls
            if DEBUG_SCREEN and 0x0400 <= addr <= 0x07E7:
                log.info(f"*** C64Memory.write() CALLED: addr=${addr:04X}, value=${value:02X} ***")
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
                if 0xA0 <= addr <= 0xA2 and DEBUG_JIFFY:
                    log.info(f"*** JIFFY CLOCK WRITE: addr=${addr:04X}, value=${value:02X} ***")
                # Log writes to screen RAM ($0400-$07E7)
                if 0x0400 <= addr <= 0x07E7:
                    if DEBUG_SCREEN:
                        log.info(f"*** SCREEN WRITE: addr=${addr:04X}, value=${value:02X} (char={chr(value) if 32 <= value < 127 else '?'}) ***")
                    # Track dirty screen cells for optimized rendering
                    if self.dirty_tracker is not None:
                        self.dirty_tracker.mark_screen_dirty(addr)
                # Log writes to cursor position variables ($D1-$D6)
                if 0xD1 <= addr <= 0xD6 and DEBUG_CURSOR:
                    var_names = {0xD1: "PNT_LO", 0xD2: "PNT_HI", 0xD3: "PNTR(col)", 0xD4: "QTSW", 0xD5: "LNMX", 0xD6: "TBLX(row)"}
                    addr_int = int(addr) if hasattr(addr, '__int__') else addr
                    val_int = int(value) if hasattr(value, '__int__') else value
                    log.info(f"*** CURSOR VAR: {var_names.get(addr_int, '?')} (${addr_int:02X}) = ${val_int:02X} ({val_int}) ***")
                # Log writes to screen line table ($D9-$F1)
                if 0xD9 <= addr <= 0xF1 and DEBUG_CURSOR:
                    addr_int = int(addr) if hasattr(addr, '__int__') else addr
                    val_int = int(value) if hasattr(value, '__int__') else value
                    row = addr_int - 0xD9
                    log.info(f"*** SCREEN LINE TABLE: row {row} (${addr_int:02X}) = ${val_int:02X} ***")
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


    def __init__(self, rom_dir: Path = Path("./roms"), display_mode: str = "pygame", scale: int = 2, enable_irq: bool = True, video_chip: str = "6569", verbose_cycles: bool = False) -> None:
        """Initialize the C64 emulator.

        Arguments:
            rom_dir: Directory containing ROM files (basic, kernal, char)
            display_mode: Display mode (pygame [default], terminal, headless)
                         If pygame fails to initialize, will automatically fall back to terminal
            scale: Pygame window scaling factor
            enable_irq: Enable IRQ injection (default: True)
            video_chip: VIC-II chip variant ("6569" for PAL, "6567R8" for NTSC,
                       "6567R56A" for old NTSC). PAL/NTSC are aliases.
            verbose_cycles: Enable per-cycle CPU logging (default: False)
        """
        self.rom_dir = Path(rom_dir)
        self.display_mode = display_mode
        self.scale = scale
        self.enable_irq = enable_irq

        # Map video chip selection to VideoTiming
        video_chip_upper = video_chip.upper()
        if video_chip_upper in ("6569", "PAL"):
            self.video_timing = VideoTiming.VIC_6569
        elif video_chip_upper in ("6567R8", "NTSC"):
            self.video_timing = VideoTiming.VIC_6567R8
        elif video_chip_upper == "6567R56A":
            self.video_timing = VideoTiming.VIC_6567R56A
        else:
            raise ValueError(f"Unknown video chip: {video_chip}")

        self.video_chip = self.video_timing.chip_name

        # If pygame mode requested, try to initialize it and fall back to terminal if it fails
        if self.display_mode == "pygame":
            try:
                import pygame
                # Test if pygame can actually initialize (might fail on headless systems)
                pygame.init()
                pygame.quit()
            except (ImportError, Exception) as e:
                log.warning(f"Pygame initialization failed: {e}")
                log.warning("Falling back to terminal display mode")
                self.display_mode = "terminal"

        # Initialize CPU (6510 is essentially a 6502 with I/O ports)
        # We'll use NMOS 6502 as the base
        self.cpu = CPU(cpu_variant=CPUVariant.NMOS_6502, verbose_cycles=verbose_cycles)

        log.info(f"Initialized CPU: {self.cpu.variant_name}")

        # Storage for ROMs
        self.basic_rom: Optional[bytes] = None
        self.kernal_rom: Optional[bytes] = None
        self.char_rom: Optional[bytes] = None
        self.vic: Optional[C64.C64VIC] = None
        self.cia1: Optional[C64.CIA1] = None
        self.cia2: Optional[C64.CIA2] = None

        # Cartridge support - the Cartridge object handles all banking logic
        # and provides EXROM/GAME signals. Stored on C64Memory, accessed via self.memory.cartridge
        # Cartridge type string for display purposes
        self.cartridge_type: str = "none"  # "none", "8k", "16k", "error"

        # Pygame display attributes
        self.pygame_screen = None
        self.pygame_surface = None
        self.pygame_available = False

        # Screen dirty tracking for optimized rendering
        self.dirty_tracker = ScreenDirtyTracker()

        # Debug logging control
        self.basic_logging_enabled = False
        self.last_pc_region = None

        # BASIC ready detection (set by pc_callback when PC enters BASIC ROM range)
        self._basic_ready = False
        self._stop_on_basic = False

        # KERNAL keyboard input detection (PC at $E5CF-$E5D6 = waiting for input)
        self._kernal_waiting_for_input = False
        self._stop_on_kernal_input = False

        # Load ROMs during initialization
        # This sets up the memory handler and all peripherals (VIC, CIAs)
        self.load_roms()

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

        # DON'T write ROMs to CPU RAM! The C64Memory handler reads from ROM arrays directly.
        # Writing them to RAM would:
        # 1. Waste memory (duplicate data)
        # 2. Cause banking issues (RAM vs ROM access)
        # 3. Corrupt I/O space in case of CHAR ROM ($D000-$DFFF)
        #
        # The memory handler (installed at line 1086) provides ROM access via banking logic:
        # - BASIC ROM at $A000-$BFFF when bit 0 of $0001 is set
        # - KERNAL ROM at $E000-$FFFF when bit 1 of $0001 is set
        # - CHAR ROM at $D000-$DFFF when bit 2 of $0001 is clear (I/O disabled)
        #
        # self._write_rom_to_memory(self.BASIC_ROM_START, self.basic_rom)
        # self._write_rom_to_memory(self.KERNAL_ROM_START, self.kernal_rom)
        # self._write_rom_to_memory(self.CHAR_ROM_START, self.char_rom)


        # Now set up the CIA1 and CIA2 and VIC
        self.cia1 = C64.CIA1(cpu=self.cpu)
        self.cia2 = C64.CIA2(cpu=self.cpu)
        self.vic = C64.C64VIC(char_rom=self.char_rom, cpu=self.cpu, cia2=self.cia2, video_timing=self.video_timing)

        # Initialize memory
        self.memory = C64.C64Memory(
            self.cpu.ram,
            basic_rom=self.basic_rom,
            kernal_rom=self.kernal_rom,
            char_rom=self.char_rom,
            cia1=self.cia1,
            cia2=self.cia2,
            vic=self.vic,
            dirty_tracker=self.dirty_tracker,
        )
        # Hook up the memory handler so CPU RAM accesses go through C64Memory
        self.cpu.ram.memory_handler = self.memory

        # Give VIC access to C64Memory for VBlank snapshots
        self.vic.set_memory(self.memory)

        # Set up periodic update callback for VIC, CIA1, and CIA2
        # VIC checks cycle count and triggers raster IRQs
        # CIA1 counts down timers and triggers timer IRQs
        # CIA2 counts down timers and triggers NMIs
        def update_peripherals():
            self.vic.update()
            self.cia1.update()
            self.cia2.update()

        self.cpu.periodic_callback = update_peripherals
        self.cpu.periodic_callback_interval = self.vic.cycles_per_line   # Update every raster line

        log.info("All ROMs loaded into memory")

        # Note: PC is already set from reset vector by cpu.reset() in main()
        # The reset() method handles the complete reset sequence including
        # fetching the vector from $FFFC/$FFFD and setting PC accordingly
        log.info(f"PC initialized to ${self.cpu.PC:04X} (from reset vector at ${self.RESET_VECTOR_ADDR:04X})")

    def load_cartridge(self, path: Path, cart_type: str = "auto") -> None:
        """Load a cartridge ROM file.

        Supports:
        - Raw binary files (.bin, .rom): 8KB or 16KB
        - CRT files (.crt): Standard C64 cartridge format with header

        Arguments:
            path: Path to cartridge file
            cart_type: "auto" (detect from file), "8k", or "16k"

        Raises:
            FileNotFoundError: If cartridge file doesn't exist
            ValueError: If cartridge format is invalid or unsupported
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Cartridge file not found: {path}")

        data = path.read_bytes()
        suffix = path.suffix.lower()

        # Check for CRT format (has "C64 CARTRIDGE" signature)
        if suffix == ".crt" or data[:16] == b"C64 CARTRIDGE   ":
            self._load_crt_cartridge(data, path)
        else:
            # Raw binary format
            self._load_raw_cartridge(data, path, cart_type)

        # Log cartridge status
        if self.memory is not None and self.memory.cartridge is not None:
            cart = self.memory.cartridge
            log.info(
                f"Cartridge loaded: {path.name} "
                f"(type: {self.cartridge_type}, EXROM={0 if not cart.exrom else 1}, GAME={0 if not cart.game else 1})"
            )

    def _load_raw_cartridge(self, data: bytes, path: Path, cart_type: str) -> None:
        """Load a raw binary cartridge file.

        Arguments:
            data: Raw cartridge data
            path: Path to cartridge file (for error messages)
            cart_type: "auto", "8k", "16k", or "ultimax"

        Raises:
            ValueError: If size doesn't match expected cartridge size
        """
        size = len(data)

        # Determine cartridge type from size and content if auto
        if cart_type == "auto":
            if size == self.ROML_SIZE:
                # 8KB file - check if it's a standard 8K cart or Ultimax
                # Standard 8K carts have CBM80 signature at offset 4 ($8004)
                # Ultimax carts have reset vector at end pointing to $E000-$FFFF
                has_cbm80 = data[4:9] == b"CBM80"

                if has_cbm80:
                    cart_type = "8k"
                    log.debug(f"Auto-detected 8K cartridge (CBM80 signature found)")
                else:
                    # Check reset vector at end of file (offsets $1FFC/$1FFD)
                    # For Ultimax, this should point to $E000-$FFFF range
                    reset_lo = data[0x1FFC]
                    reset_hi = data[0x1FFD]
                    reset_vector = reset_lo | (reset_hi << 8)

                    if 0xE000 <= reset_vector <= 0xFFFF:
                        cart_type = "ultimax"
                        log.info(
                            f"Auto-detected Ultimax cartridge: reset vector ${reset_vector:04X} "
                            f"points to cartridge ROM space"
                        )
                    else:
                        # Default to 8K if we can't determine
                        cart_type = "8k"
                        log.debug(
                            f"Assuming 8K cartridge (no CBM80, reset vector ${reset_vector:04X})"
                        )
            elif size == self.ROML_SIZE + self.ROMH_SIZE:
                cart_type = "16k"
            else:
                raise ValueError(
                    f"Cannot auto-detect cartridge type for {path.name}: "
                    f"size {size} bytes (expected 8192 or 16384)"
                )

        # Validate size matches specified type and create Cartridge object
        if cart_type == "8k":
            if size != self.ROML_SIZE:
                raise ValueError(
                    f"8K cartridge {path.name} has wrong size: "
                    f"{size} bytes (expected {self.ROML_SIZE})"
                )
            cartridge = StaticROMCartridge(
                roml_data=data,
                romh_data=None,
                name=path.stem,
            )
            self.cartridge_type = "8k"
        elif cart_type == "16k":
            if size != self.ROML_SIZE + self.ROMH_SIZE:
                raise ValueError(
                    f"16K cartridge {path.name} has wrong size: "
                    f"{size} bytes (expected {self.ROML_SIZE + self.ROMH_SIZE})"
                )
            cartridge = StaticROMCartridge(
                roml_data=data[:self.ROML_SIZE],
                romh_data=data[self.ROML_SIZE:],
                name=path.stem,
            )
            self.cartridge_type = "16k"
        elif cart_type == "ultimax":
            if size != self.ROMH_SIZE:
                raise ValueError(
                    f"Ultimax cartridge {path.name} has wrong size: "
                    f"{size} bytes (expected {self.ROMH_SIZE})"
                )
            cartridge = StaticROMCartridge(
                roml_data=None,
                romh_data=None,
                ultimax_romh_data=data,
                name=path.stem,
            )
            self.cartridge_type = "ultimax"
        else:
            raise ValueError(f"Unknown cartridge type: {cart_type}")

        # Attach cartridge to memory handler
        if self.memory is not None:
            self.memory.cartridge = cartridge

        log.info(f"Loaded raw {cart_type.upper()} cartridge: {path.name} ({size} bytes)")

    def _create_error_cartridge(self, error_lines: list[str]) -> bytes:
        """Create an 8KB cartridge ROM that displays an error message.

        This is used when an unsupported cartridge type is loaded, to give
        the user a friendly on-screen message instead of crashing.

        Arguments:
            error_lines: List of text lines to display (max ~38 chars each)

        Returns:
            8KB cartridge ROM data
        """
        # Use the shared function from cartridges module (single source of truth)
        return create_error_cartridge_rom(error_lines, border_color=0x02)

    def _load_error_cartridge_with_results(self, results: CartridgeTestResults) -> None:
        """Generate and load an error cartridge displaying test results.

        Arguments:
            results: CartridgeTestResults with current pass/fail state
        """
        error_lines = results.to_display_lines()
        error_roml_data = self._create_error_cartridge(error_lines)

        # Create ErrorCartridge object
        cartridge = ErrorCartridge(
            roml_data=error_roml_data,
            original_type=results.hardware_type,
            original_name=results.cart_name,
        )
        self.cartridge_type = "error"

        # Attach cartridge to memory handler
        if self.memory is not None:
            self.memory.cartridge = cartridge

        log.info(f"Loaded error cartridge with test results for type {results.hardware_type}")

    def _load_crt_cartridge(self, data: bytes, path: Path) -> None:
        """Load a CRT format cartridge file.

        CRT format:
        - 64-byte header with signature, hardware type, EXROM/GAME lines
        - CHIP packets containing ROM data with load addresses

        Arguments:
            data: CRT file data
            path: Path to cartridge file (for error messages)

        Raises:
            ValueError: If CRT format is invalid or unsupported
        """
        # Create test results - starts with all FAILs
        results = CartridgeTestResults()

        # Validate CRT header size
        if len(data) < 64:
            # Generate error cart with current results (all FAIL)
            self._load_error_cartridge_with_results(results)
            return

        results.header_size_valid = True

        # Check signature
        signature = data[:16]
        if signature != b"C64 CARTRIDGE   ":
            # Generate error cart with current results
            self._load_error_cartridge_with_results(results)
            return

        results.signature_valid = True

        # Parse header (big-endian values)
        header_length = int.from_bytes(data[0x10:0x14], "big")
        version_hi = data[0x14]
        version_lo = data[0x15]
        hardware_type = int.from_bytes(data[0x16:0x18], "big")
        exrom_line = data[0x18]
        game_line = data[0x19]
        cart_name = data[0x20:0x40].rstrip(b"\x00").decode("latin-1", errors="replace")

        # Update results with parsed values
        results.version_valid = True  # We parsed it successfully
        results.hardware_type = hardware_type
        results.hardware_name = self.CRT_HARDWARE_TYPES.get(hardware_type, f"Unknown type {hardware_type}")
        results.exrom_line = exrom_line
        results.game_line = game_line
        results.cart_name = cart_name

        log.info(
            f"CRT header: name='{cart_name}', version={version_hi}.{version_lo}, "
            f"hardware_type={hardware_type} ({results.hardware_name}), EXROM={exrom_line}, GAME={game_line}"
        )

        # Check if hardware type is supported
        mapper_supported = hardware_type in CARTRIDGE_TYPES
        if mapper_supported:
            results.mapper_supported = True
        else:
            log.warning(
                f"Unsupported cartridge type {hardware_type} ({results.hardware_name}). "
                f"Will parse CHIP packets for diagnostics."
            )

        # Parse CHIP packets (even for unsupported types, for diagnostics)
        offset = header_length

        # For Type 0 (standard cartridge)
        roml_data = None
        romh_data = None
        ultimax_romh_data = None

        # For banked cartridges (Type 1+)
        banks: dict[int, bytes] = {}  # bank_number -> rom_data

        # Ultimax mode detection from CRT header
        # EXROM=1, GAME=0 indicates Ultimax mode
        is_ultimax = (exrom_line == 1 and game_line == 0)

        while offset < len(data):
            if offset + 16 > len(data):
                break  # Not enough data for another CHIP header

            chip_sig = data[offset:offset + 4]
            if chip_sig != b"CHIP":
                # Invalid CHIP signature - generate error cart with results so far
                self._load_error_cartridge_with_results(results)
                return

            packet_length = int.from_bytes(data[offset + 4:offset + 8], "big")
            chip_type = int.from_bytes(data[offset + 8:offset + 10], "big")
            bank_number = int.from_bytes(data[offset + 10:offset + 12], "big")
            load_address = int.from_bytes(data[offset + 12:offset + 14], "big")
            rom_size = int.from_bytes(data[offset + 14:offset + 16], "big")

            log.debug(
                f"CHIP packet: type={chip_type}, bank={bank_number}, "
                f"load=${load_address:04X}, size={rom_size}"
            )

            # Track that we found a CHIP packet
            results.chip_count += 1
            results.chip_packets_found = True

            # Only handle ROM chips (type 0) for now
            if chip_type != 0:
                log.warning(f"Skipping non-ROM CHIP type {chip_type}")
                offset += packet_length
                continue

            # Extract ROM data
            rom_data = data[offset + 16:offset + 16 + rom_size]

            if hardware_type == 0:
                # Type 0: Standard cartridge - single bank only
                if bank_number != 0:
                    log.warning(f"Skipping bank {bank_number} for Type 0 cartridge")
                    offset += packet_length
                    continue

                if load_address == self.ROML_START:
                    # Check if this is a 16KB ROM that needs to be split
                    if rom_size > self.ROML_SIZE:
                        # Split 16KB ROM: first 8KB to ROML, second 8KB to ROMH
                        roml_data = rom_data[:self.ROML_SIZE]
                        romh_data = rom_data[self.ROML_SIZE:]
                        results.roml_valid = True
                        results.romh_valid = True
                        log.info(f"Loaded ROML: ${load_address:04X}-${load_address + self.ROML_SIZE - 1:04X} ({self.ROML_SIZE} bytes)")
                        log.info(f"Loaded ROMH: ${self.ROMH_START:04X}-${self.ROMH_START + len(romh_data) - 1:04X} ({len(romh_data)} bytes)")
                    else:
                        roml_data = rom_data
                        results.roml_valid = True
                        log.info(f"Loaded ROML: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                elif load_address == self.ROMH_START:
                    romh_data = rom_data
                    results.romh_valid = True
                    log.info(f"Loaded ROMH: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                elif load_address == self.KERNAL_ROM_START:
                    # Ultimax mode: ROM at $E000-$FFFF replaces KERNAL
                    ultimax_romh_data = rom_data
                    results.ultimax_romh_valid = True
                    log.info(f"Loaded Ultimax ROMH: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                else:
                    log.warning(f"Unknown CHIP load address: ${load_address:04X}")
            else:
                # Banked cartridges (Type 1+): Collect all banks
                # For Action Replay, each bank is 8KB at $8000
                if load_address == self.ROML_START:
                    banks[bank_number] = rom_data
                    results.roml_valid = True  # At least one bank loaded to ROML region
                    results.bank_switching_valid = len(banks) > 1  # Multiple banks = bank switching works
                    log.info(f"Loaded bank {bank_number}: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                else:
                    log.warning(f"Unexpected load address ${load_address:04X} for bank {bank_number}")

            offset += packet_length

        # If mapper not supported, generate error cart with diagnostics
        if not mapper_supported:
            self._load_error_cartridge_with_results(results)
            return

        # Create appropriate cartridge object based on hardware type
        if hardware_type == 0:
            # Validate we got valid ROM data for Type 0
            if ultimax_romh_data is None and roml_data is None:
                # No usable ROM data - generate error cart
                self._load_error_cartridge_with_results(results)
                return

            cartridge = create_cartridge(
                hardware_type=0,
                roml_data=roml_data,
                romh_data=romh_data,
                ultimax_romh_data=ultimax_romh_data,
                name=cart_name,
            )

            # Determine cartridge type from what we loaded
            if ultimax_romh_data is not None:
                self.cartridge_type = "ultimax"
            elif romh_data is not None:
                self.cartridge_type = "16k"
            else:
                self.cartridge_type = "8k"
        else:
            # Banked cartridges - convert bank dict to sorted list
            if not banks:
                # No bank data - generate error cart
                self._load_error_cartridge_with_results(results)
                return

            # Create sorted list of banks (fill missing banks with empty data)
            max_bank = max(banks.keys())
            bank_list = []
            for i in range(max_bank + 1):
                if i in banks:
                    bank_list.append(banks[i])
                else:
                    # Fill missing banks with empty 8KB
                    log.warning(f"Bank {i} missing, filling with empty data")
                    bank_list.append(bytes(ROML_SIZE))

            cartridge = create_cartridge(
                hardware_type=hardware_type,
                banks=bank_list,
                name=cart_name,
            )
            self.cartridge_type = results.hardware_name.lower().replace(" ", "_")

        # Mark as fully loaded
        results.fully_loaded = True

        # Attach cartridge to memory handler
        if self.memory is not None:
            self.memory.cartridge = cartridge

        log.info(f"Loaded CRT cartridge: '{cart_name}' (type {hardware_type}: {results.hardware_name})")

    def get_video_standard(self) -> str:
        """Get the video standard (PAL or NTSC) based on the current video chip.

        Returns:
            "PAL" for chip 6569, "NTSC" for chips 6567R8 or 6567R56A
        """
        if self.video_chip == "6569":
            return "PAL"
        else:  # 6567R8 or 6567R56A
            return "NTSC"

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
            pygame.display.set_caption(f"C64 Emulator - {self.get_video_standard()} ({self.video_chip})")

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

    def load_program(
        self, program_path: Path, load_address: Optional[int] = None
    ) -> tuple[int, int]:
        """Load a program into memory.

        Arguments:
            program_path: Path to the program file
            load_address: Address to load program at (default: $0801 for BASIC programs)
                         If None and file has a 2-byte header, use header address

        Returns:
            Tuple of (load_address, end_address) - the address range used
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

        end_address = load_address + len(program_data)

        log.info(
            f"Loaded program: {program_path.name} "
            f"at ${load_address:04X}-${end_address - 1:04X} "
            f"({len(program_data)} bytes)"
        )

        return load_address, end_address

    def update_basic_pointers(self, program_end: int) -> None:
        """Update BASIC memory pointers after loading a program.

        When loading a BASIC program at $0801, BASIC's internal pointers
        must be updated so that RUN knows where the program ends.

        Arguments:
            program_end: Address immediately after the last byte of the program
        """
        # VARTAB, ARYTAB, and STREND should all point to the end of the program
        # (They get properly set up when BASIC parses the program, but for
        # directly loaded programs we need to set them manually)
        lo = program_end & 0xFF
        hi = (program_end >> 8) & 0xFF

        # Set VARTAB (start of variables = end of program)
        self.cpu.ram[self.VARTAB] = lo
        self.cpu.ram[self.VARTAB + 1] = hi

        # Set ARYTAB (start of arrays = end of variables)
        self.cpu.ram[self.ARYTAB] = lo
        self.cpu.ram[self.ARYTAB + 1] = hi

        # Set STREND (end of arrays = bottom of strings)
        self.cpu.ram[self.STREND] = lo
        self.cpu.ram[self.STREND + 1] = hi

        log.info(f"Updated BASIC pointers: VARTAB/ARYTAB/STREND = ${program_end:04X}")

    def inject_keyboard_buffer(self, text: str) -> None:
        """Inject a string into the KERNAL keyboard buffer.

        This writes directly to the keyboard buffer at $0277-$0280 and sets
        the buffer count at $00C6. The KERNAL will process these characters
        as if they were typed. Maximum 10 characters.

        Arguments:
            text: String to inject (max 10 chars, typically ending with \\r for RETURN)
        """
        # Convert to PETSCII (for simple ASCII chars, it's mostly the same)
        # RETURN key is 0x0D in PETSCII
        petscii_text = text.replace('\r', '\x0d').replace('\n', '\x0d')

        # Limit to 10 characters (keyboard buffer size)
        if len(petscii_text) > 10:
            log.warning(f"Keyboard buffer overflow: truncating '{text}' to 10 chars")
            petscii_text = petscii_text[:10]

        # Write characters to buffer at $0277
        for i, char in enumerate(petscii_text):
            self.cpu.ram[self.KEYBOARD_BUFFER + i] = ord(char)

        # Set buffer count at $00C6
        self.cpu.ram[self.KEYBOARD_BUFFER_SIZE] = len(petscii_text)

        log.info(f"Injected '{text.strip()}' into keyboard buffer ({len(petscii_text)} chars)")

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

    @property
    def basic_ready(self) -> bool:
        """Return True if BASIC input loop has been reached."""
        return self._basic_ready

    @property
    def kernal_waiting_for_input(self) -> bool:
        """Return True if KERNAL is waiting for keyboard input.

        The KERNAL keyboard input loop is at $E5CF-$E5D6.
        When PC is in this range, the system is waiting for user input.
        """
        return self._kernal_waiting_for_input

    def _pc_callback(self, new_pc: int) -> None:
        """PC change callback - detects when BASIC is ready or KERNAL is waiting for input.

        This is called by the CPU every time PC changes.
        """
        # Check if PC is in BASIC ROM range
        if self.BASIC_ROM_START <= new_pc <= self.BASIC_ROM_END:
            self._basic_ready = True
            if self._stop_on_basic:
                raise StopIteration("BASIC is ready")

        # Check if PC is in KERNAL keyboard input loop ($E5CF-$E5D6)
        # This is the GETIN routine that waits for keyboard input
        if 0xE5CF <= new_pc <= 0xE5D6:
            self._kernal_waiting_for_input = True
            if self._stop_on_kernal_input:
                raise StopIteration("KERNAL waiting for input")
        else:
            # Reset when PC leaves the input loop
            self._kernal_waiting_for_input = False

    def _setup_pc_callback(
        self, stop_on_basic: bool = False, stop_on_kernal_input: bool = False
    ) -> None:
        """Set up the PC callback for BASIC/KERNAL detection.

        Arguments:
            stop_on_basic: If True, raise StopIteration when BASIC is ready
            stop_on_kernal_input: If True, raise StopIteration when KERNAL is waiting for input
        """
        self._stop_on_basic = stop_on_basic
        self._stop_on_kernal_input = stop_on_kernal_input
        self.cpu.pc_callback = self._pc_callback

    def _clear_pc_callback(self) -> None:
        """Remove the PC callback and reset detection flags."""
        self.cpu.pc_callback = None
        self._stop_on_basic = False
        self._stop_on_kernal_input = False

    def _check_pc_region(self) -> None:
        """Monitor PC and enable detailed logging when entering BASIC or KERNAL ROM."""
        region = self.get_pc_region()

        # Track important PC locations
        pc = self.cpu.PC

        # Log when we enter BASIC ROM
        if self.BASIC_ROM_START <= pc <= self.BASIC_ROM_END and not hasattr(self, '_logged_basic_entry'):
            self._logged_basic_entry = True
            self._basic_ready = True
            log.info(f"*** ENTERED BASIC ROM at ${pc:04X} ***")

        # Log when stuck at KERNAL idle loop ($E5CF-$E5D2)
        if 0xE5CF <= pc <= 0xE5D2:
            if not hasattr(self, '_e5cf_count'):
                self._e5cf_count = 0
            self._e5cf_count += 1
            if self._e5cf_count % 10000 == 0:
                log.info(f"*** Still in KERNAL idle loop at ${pc:04X} (count={self._e5cf_count}) ***")

        # Enable logging when entering KERNAL for the first time (for debugging)
        if DEBUG_KERNAL and region == "KERNAL" and self.last_pc_region != "KERNAL":
            logging.getLogger("mos6502").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.cpu").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.cpu.flags").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory.RAM").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory.Byte").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory.Word").setLevel(logging.DEBUG)
            log.info(f"*** ENTERING KERNAL ROM at ${self.cpu.PC:04X} - Enabling detailed CPU logging ***")

        # Enable logging when entering BASIC for the first time
        if DEBUG_BASIC and region == "BASIC" and not self.basic_logging_enabled:
            self.basic_logging_enabled = True
            logging.getLogger("mos6502").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.cpu").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.cpu.flags").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory.RAM").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory.Byte").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory.Word").setLevel(logging.DEBUG)
            log.info(f"*** ENTERING BASIC ROM at ${self.cpu.PC:04X} - Enabling detailed CPU logging ***")

        self.last_pc_region = region



    def run(
        self,
        max_cycles: int = INFINITE_CYCLES,
        stop_on_basic: bool = False,
        stop_on_kernal_input: bool = False,
        throttle: bool = True,
    ) -> None:
        """Run the C64 emulator.

        Arguments:
            max_cycles: Maximum number of CPU cycles to execute
                       (default: INFINITE_CYCLES for continuous execution)
            stop_on_basic: If True, stop execution when BASIC prompt is ready
            stop_on_kernal_input: If True, stop execution when KERNAL is waiting for keyboard input
            throttle: If True, throttle emulation to real-time speed (default: True)
                     Use --no-throttle for benchmarks to run at maximum speed
        """
        log.info(f"Starting execution at PC=${self.cpu.PC:04X}")
        log.info("Press Ctrl+C to stop")

        # Set up PC callback for BASIC/KERNAL detection if requested
        if stop_on_basic or stop_on_kernal_input:
            self._setup_pc_callback(
                stop_on_basic=stop_on_basic, stop_on_kernal_input=stop_on_kernal_input
            )

        try:
            # Execute with cycle counter display
            # Use threading for concurrent execution - multiprocessing has pickling issues
            # with closures and the GIL doesn't affect us since we're I/O bound on display
            # The frame_complete uses multiprocessing.Event for cross-process safety
            import threading
            import time
            import sys as _sys
            from mos6502.timing import FrameGovernor

            # Check if we're in a TTY (terminal) for interactive display
            is_tty = _sys.stdout.isatty()

            # For pygame mode, run CPU in background thread and pygame in main thread
            # For other modes, run display in background and CPU in main thread
            if self.display_mode == "pygame" and self.pygame_available:
                # Pygame mode: CPU in background, rendering + input in main thread
                cpu_done = threading.Event()
                cpu_error = None
                stop_cpu = threading.Event()

                # Create frame governor for real-time throttling
                governor = FrameGovernor(
                    fps=self.video_timing.refresh_hz,
                    enabled=throttle
                )
                cycles_per_frame = self.video_timing.cycles_per_frame

                def cpu_thread() -> None:
                    nonlocal cpu_error
                    try:
                        # Execute frame-by-frame with optional throttling
                        # This allows the governor to maintain real-time speed
                        cycles_remaining = max_cycles
                        while cycles_remaining > 0 and not stop_cpu.is_set():
                            # Execute one frame's worth of cycles
                            cycles_this_frame = min(cycles_per_frame, cycles_remaining)
                            try:
                                self.cpu.execute(cycles=cycles_this_frame)
                            except errors.CPUCycleExhaustionError:
                                pass  # Normal - frame completed
                            cycles_remaining -= cycles_this_frame

                            # Throttle to real-time (governor.throttle() returns
                            # immediately if throttling is disabled)
                            governor.throttle()
                    except Exception as e:
                        cpu_error = e
                    finally:
                        cpu_done.set()

                # Start CPU thread
                cpu_thread_obj = threading.Thread(target=cpu_thread, daemon=True)
                cpu_thread_obj.start()

                # Try to set up terminal input (REPL-style) alongside pygame
                terminal_input_available = False
                old_settings = None
                try:
                    import select
                    import termios
                    import tty
                    if _sys.stdin.isatty():
                        old_settings = termios.tcgetattr(_sys.stdin)
                        tty.setcbreak(_sys.stdin.fileno())
                        terminal_input_available = True
                except ImportError:
                    pass  # Terminal input not available (Windows, etc.)

                # Main thread handles pygame rendering + terminal input
                # Use blocking wait on frame_complete to avoid burning CPU
                try:
                    while not cpu_done.is_set():
                        # Check for BASIC ready or KERNAL input if requested
                        if stop_on_basic and self.basic_ready:
                            break
                        if stop_on_kernal_input and self.kernal_waiting_for_input:
                            break

                        # Handle terminal keyboard input if available
                        if terminal_input_available:
                            import select
                            if select.select([_sys.stdin], [], [], 0)[0]:
                                char = _sys.stdin.read(1)
                                if self._handle_terminal_input(char):
                                    break  # Ctrl+C pressed

                        # Wait for frame_complete (blocking) or timeout
                        # This efficiently waits without burning CPU
                        if self.vic.frame_complete.wait(timeout=0.02):
                            # Frame ready - render it
                            self._render_pygame()
                        else:
                            # Timeout - pump pygame events to stay responsive
                            self._pump_pygame_events()
                finally:
                    # Signal CPU thread to stop and wait for it
                    stop_cpu.set()
                    cpu_done.set()
                    cpu_thread_obj.join(timeout=0.5)

                    # Restore terminal settings if we changed them
                    if old_settings is not None:
                        import termios
                        termios.tcsetattr(_sys.stdin, termios.TCSADRAIN, old_settings)

                    # Cleanup pygame
                    if self.pygame_available:
                        try:
                            import pygame
                            pygame.quit()
                        except Exception:
                            pass

                    # Log governor stats if throttling was enabled
                    if throttle:
                        stats = governor.stats()
                        log.info(f"Governor stats: {stats['frame_count']} frames, "
                                f"avg sleep {stats['avg_sleep_per_frame']*1000:.1f}ms/frame, "
                                f"dropped {stats['frames_dropped']}")

                # Re-raise CPU thread exception if any
                if cpu_error:
                    raise cpu_error

            else:
                # Terminal or headless mode: display in background, CPU in main thread
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

                # Create frame governor for real-time throttling (terminal/headless modes)
                governor = FrameGovernor(
                    fps=self.video_timing.refresh_hz,
                    enabled=throttle
                )
                cycles_per_frame = self.video_timing.cycles_per_frame

                try:
                    if throttle:
                        # Execute frame-by-frame with throttling
                        cycles_remaining = max_cycles
                        while cycles_remaining > 0:
                            cycles_this_frame = min(cycles_per_frame, cycles_remaining)
                            try:
                                self.cpu.execute(cycles=cycles_this_frame)
                            except errors.CPUCycleExhaustionError:
                                pass  # Normal - frame completed
                            cycles_remaining -= cycles_this_frame
                            governor.throttle()
                    else:
                        # Run CPU at full speed - if stop_on_basic, pc_callback will raise StopIteration
                        self.cpu.execute(cycles=max_cycles)
                finally:
                    # Stop the display thread
                    stop_display.set()
                    display_thread.join(timeout=0.5)

                    # Log governor stats if throttling was enabled
                    if throttle:
                        stats = governor.stats()
                        log.info(f"Governor stats: {stats['frame_count']} frames, "
                                f"avg sleep {stats['avg_sleep_per_frame']*1000:.1f}ms/frame, "
                                f"dropped {stats['frames_dropped']}")

        except StopIteration as e:
            # PC callback requested stop (e.g., BASIC is ready or KERNAL waiting for input)
            log.info(f"Execution stopped at PC=${self.cpu.PC:04X} ({e})")
        except errors.CPUCycleExhaustionError as e:
            log.info(f"CPU execution completed: {e}")
        except errors.CPUBreakError as e:
            log.info(f"Program terminated (BRK at PC=${self.cpu.PC:04X})")
        except KeyboardInterrupt:
            log.info("\nExecution interrupted by user")
            log.info(f"PC=${self.cpu.PC:04X}, Cycles={self.cpu.cycles_executed}")
        except (errors.IllegalCPUInstructionError, RuntimeError) as e:
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
            # Clean up PC callback
            self._clear_pc_callback()
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
        """Render C64 screen to terminal with dirty region optimization."""
        import sys as _sys

        screen_start = 0x0400
        cols = 40
        rows = 25

        # Header row offset (3 lines: border, title, border)
        header_offset = 3

        # Check if we need a full redraw
        needs_full = self.dirty_tracker.needs_full_redraw()

        if needs_full:
            # Full screen redraw
            _sys.stdout.write("\033[2J\033[H")  # Clear screen and move to top

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

        elif self.dirty_tracker.has_changes():
            # Incremental update - only redraw dirty cells
            dirty_cells = self.dirty_tracker.get_dirty_cells()
            for row, col in dirty_cells:
                # Move cursor to the cell position
                # Terminal rows are 1-indexed, add header offset
                term_row = row + header_offset + 1
                term_col = col + 1
                _sys.stdout.write(f"\033[{term_row};{term_col}H")

                # Get and render the character
                addr = screen_start + (row * cols) + col
                petscii = int(self.cpu.ram[addr])
                char = self.petscii_to_ascii(petscii)
                _sys.stdout.write(char)

        # Always update status line (at row 29: 3 header + 25 screen + 1 border)
        status_row = header_offset + rows + 2

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

        # Move to status line and update it
        _sys.stdout.write(f"\033[{status_row};1H")
        status = (f"Cycles: {self.cpu.cycles_executed:,} | "
                f"PC=${self.cpu.PC:04X}[{region}] {inst_display:20s} | "
                f"A=${self.cpu.A:02X} X=${self.cpu.X:02X} "
                f"Y=${self.cpu.Y:02X} S=${self.cpu.S & 0xFF:02X} P={flags}")
        # Clear line and write status
        _sys.stdout.write("\033[K" + status)
        _sys.stdout.flush()

        # Clear dirty flags after rendering
        self.dirty_tracker.clear()

    def _render_terminal_debug(self) -> None:
        """Render C64 screen and CPU state to terminal (for pygame mode debug).

        This version uses ANSI escape codes to update in place without scrolling.
        It shows the screen, CPU registers, and current instruction.
        """
        import sys as _sys

        screen_start = 0x0400
        cols = 40
        rows = 25

        # Get colors
        bg_color = self.vic.regs[0x21] & 0x0F
        bg_ansi = c64_to_ansi_bg(bg_color)
        border_color = self.vic.regs[0x20] & 0x0F
        border_ansi = c64_to_ansi_bg(border_color)

        # Clear screen and move to top
        _sys.stdout.write("\033[2J\033[H")

        # Border and title
        _sys.stdout.write(border_ansi + " " * 44 + ANSI_RESET + "\n")
        _sys.stdout.write(border_ansi + " " + ANSI_RESET +
                         " C64 (pygame mode) " +
                         border_ansi + " " * 24 + ANSI_RESET + "\n")
        _sys.stdout.write(border_ansi + " " * 44 + ANSI_RESET + "\n")

        # Screen content with colors
        for row in range(rows):
            # Left border
            _sys.stdout.write(border_ansi + "  " + ANSI_RESET)

            last_fg = -1
            for col in range(cols):
                screen_addr = screen_start + (row * cols) + col
                color_addr = row * cols + col
                petscii = int(self.cpu.ram[screen_addr])
                fg_color = self.memory.ram_color[color_addr] & 0x0F

                # Check for reverse video (screen codes 128-255)
                if petscii >= 128:
                    char = self.petscii_to_ascii(petscii)
                    _sys.stdout.write(c64_to_ansi_bg(fg_color) +
                                    c64_to_ansi_fg(bg_color) + char)
                    last_fg = -1
                else:
                    if fg_color != last_fg:
                        _sys.stdout.write(bg_ansi + c64_to_ansi_fg(fg_color))
                        last_fg = fg_color
                    char = self.petscii_to_ascii(petscii)
                    _sys.stdout.write(char)

            # Right border
            _sys.stdout.write(ANSI_RESET + border_ansi + "  " + ANSI_RESET + "\n")

        # Bottom border
        _sys.stdout.write(border_ansi + " " * 44 + ANSI_RESET + "\n")

        # CPU state
        from mos6502.flags import format_flags
        flags = format_flags(self.cpu._flags.value)
        pc = self.cpu.PC
        region = self.get_pc_region()

        # Disassemble current instruction
        try:
            inst_str = self.disassemble_instruction(pc)
            inst_display = inst_str.strip()
        except (KeyError, ValueError, IndexError):
            try:
                b0 = self.cpu.ram[pc]
                b1 = self.cpu.ram[pc+1]
                b2 = self.cpu.ram[pc+2]
                inst_display = f"{b0:02X} {b1:02X} {b2:02X}  ???"
            except IndexError:
                inst_display = "???"

        # Status line
        status = (f"Cycles: {self.cpu.cycles_executed:,} | "
                f"PC=${pc:04X}[{region}] {inst_display:20s} | "
                f"A=${self.cpu.A:02X} X=${self.cpu.X:02X} "
                f"Y=${self.cpu.Y:02X} S=${self.cpu.S & 0xFF:02X} P={flags}")
        _sys.stdout.write(status + "\n")
        _sys.stdout.flush()

    def _render_terminal_repl(self) -> None:
        """Render C64 screen to terminal for REPL mode with color support.

        This version uses \r\n for line endings to work correctly in cbreak mode.
        Colors are rendered using ANSI 256-color escape codes.
        """
        import sys as _sys

        screen_start = 0x0400
        cols = 40
        rows = 25

        # Get background color from VIC register $D021
        bg_color = self.vic.regs[0x21] & 0x0F
        bg_ansi = c64_to_ansi_bg(bg_color)

        # Get border color from VIC register $D020
        border_color = self.vic.regs[0x20] & 0x0F
        border_ansi = c64_to_ansi_bg(border_color)

        # Header row offset (3 lines: border, title, border)
        header_offset = 3

        # Check if we need a full redraw
        needs_full = self.dirty_tracker.needs_full_redraw()

        if needs_full:
            # Full screen redraw
            _sys.stdout.write("\033[2J\033[H")  # Clear screen and move to top

            # Border line
            _sys.stdout.write(border_ansi + " " * 44 + ANSI_RESET + "\r\n")
            title_text = f" C64 REPL (Ctrl+C to exit) - {self.get_video_standard()} ({self.video_chip}) "
            # Total width is 44: 1 space + title_text + padding
            title_padding = max(0, 43 - len(title_text))
            _sys.stdout.write(border_ansi + " " + ANSI_RESET +
                            title_text +
                            border_ansi + " " * title_padding + ANSI_RESET + "\r\n")
            _sys.stdout.write(border_ansi + " " * 44 + ANSI_RESET + "\r\n")

            for row in range(rows):
                # Left border
                _sys.stdout.write(border_ansi + "  " + ANSI_RESET)

                # Screen content with colors
                last_fg = -1
                for col in range(cols):
                    screen_addr = screen_start + (row * cols) + col
                    color_addr = row * cols + col
                    petscii = int(self.cpu.ram[screen_addr])
                    fg_color = self.memory.ram_color[color_addr] & 0x0F

                    # Check for reverse video (screen codes 128-255)
                    if petscii >= 128:
                        # Reverse video: swap fg and bg
                        char = self.petscii_to_ascii(petscii)
                        _sys.stdout.write(c64_to_ansi_bg(fg_color) +
                                        c64_to_ansi_fg(bg_color) + char)
                        last_fg = -1  # Force color reset
                    else:
                        # Normal: fg on bg
                        if fg_color != last_fg:
                            _sys.stdout.write(bg_ansi + c64_to_ansi_fg(fg_color))
                            last_fg = fg_color
                        char = self.petscii_to_ascii(petscii)
                        _sys.stdout.write(char)

                # Right border and reset
                _sys.stdout.write(ANSI_RESET + border_ansi + "  " + ANSI_RESET + "\r\n")

            # Bottom border
            _sys.stdout.write(border_ansi + " " * 44 + ANSI_RESET + "\r\n")

        elif self.dirty_tracker.has_changes():
            # Incremental update - only redraw dirty cells
            dirty_cells = self.dirty_tracker.get_dirty_cells()
            for row, col in dirty_cells:
                # Move cursor to the cell position
                # Terminal rows are 1-indexed, add header offset, +2 for left border
                term_row = row + header_offset + 1
                term_col = col + 3  # +2 for border, +1 for 1-indexing
                _sys.stdout.write(f"\033[{term_row};{term_col}H")

                # Get screen and color data
                screen_addr = screen_start + (row * cols) + col
                color_addr = row * cols + col
                petscii = int(self.cpu.ram[screen_addr])
                fg_color = self.memory.ram_color[color_addr] & 0x0F

                # Render with color
                if petscii >= 128:
                    # Reverse video
                    char = self.petscii_to_ascii(petscii)
                    _sys.stdout.write(c64_to_ansi_bg(fg_color) +
                                    c64_to_ansi_fg(bg_color) + char + ANSI_RESET)
                else:
                    char = self.petscii_to_ascii(petscii)
                    _sys.stdout.write(bg_ansi + c64_to_ansi_fg(fg_color) + char + ANSI_RESET)

        # Always update status line (at row 30: 3 header + 25 screen + 1 border + 1)
        status_row = header_offset + rows + 2

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

        # Move to status line and update it
        _sys.stdout.write(f"\033[{status_row};1H")
        status = (f"Cycles: {self.cpu.cycles_executed:,} | "
                f"PC=${self.cpu.PC:04X}[{region}] {inst_display:20s} | "
                f"A=${self.cpu.A:02X} X=${self.cpu.X:02X} "
                f"Y=${self.cpu.Y:02X} S=${self.cpu.S & 0xFF:02X} P={flags}")
        # Clear line and write status
        _sys.stdout.write("\033[K" + status)
        _sys.stdout.flush()

        # Clear dirty flags after rendering
        self.dirty_tracker.clear()

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
            # pygame.K_POUND: (6, 0),    # £ (pound symbol on C64, no direct US keyboard equivalent)
            pygame.K_QUOTE: (3, 0),      # Map to '7' key - SHIFT+7 produces apostrophe on C64
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
            pygame.K_QUOTEDBL: (7, 3),   # " (double quote) - same as '2' key (SHIFT+2 on C64)
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

                # Special handling for quote keys - also press SHIFT
                if event.key == pygame.K_QUOTE:
                    # Press LEFT SHIFT (row 1, col 7) along with the key
                    self.cia1.press_key(1, 7)  # SHIFT
                    self.cia1.press_key(row, col)  # '7' key
                elif event.key == pygame.K_QUOTEDBL:
                    # Press LEFT SHIFT (row 1, col 7) along with the key
                    self.cia1.press_key(1, 7)  # SHIFT
                    self.cia1.press_key(row, col)  # '2' key
                else:
                    self.cia1.press_key(row, col)

                if DEBUG_KEYBOARD:
                    petscii_key = self.cia1._get_key_name(row, col)
                    log.info(f"*** KEYDOWN: pygame='{key_name}' (code={event.key}), ASCII='{ascii_char}' (0x{ascii_code:02X}), matrix position=({row},{col}), PETSCII={petscii_key} ***")
            else:
                if DEBUG_KEYBOARD:
                    log.info(f"*** UNMAPPED KEYDOWN: pygame='{key_name}' (code={event.key}), ASCII='{ascii_char}' ***")
        elif event.type == pygame.KEYUP:
            if event.key in key_map:
                row, col = key_map[event.key]

                # Special handling for quote keys - also release SHIFT
                if event.key == pygame.K_QUOTE:
                    self.cia1.release_key(1, 7)  # SHIFT
                    self.cia1.release_key(row, col)  # '7' key
                elif event.key == pygame.K_QUOTEDBL:
                    self.cia1.release_key(1, 7)  # SHIFT
                    self.cia1.release_key(row, col)  # '2' key
                else:
                    self.cia1.release_key(row, col)

                if DEBUG_KEYBOARD:
                    log.info(f"*** KEY RELEASED: pygame key {event.key}, row={row}, col={col} ***")

    def _render_pygame(self) -> None:
        """Render C64 screen to pygame window with dirty region optimization."""
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
                    if DEBUG_KEYBOARD:
                        log.info(f"*** PYGAME KEYDOWN EVENT: key={event.key} ***")
                    self._handle_pygame_keyboard(event, pygame)
                elif event.type == pygame.KEYUP:
                    self._handle_pygame_keyboard(event, pygame)

            # Check if VIC has a new frame ready (VBlank)
            # VIC takes the snapshot at the exact moment of VBlank for consistency
            new_frame = self.vic.frame_complete.is_set()
            if new_frame:
                self.vic.frame_complete.clear()
                self._frame_count = getattr(self, '_frame_count', 0) + 1
                if self._frame_count <= 5 or self._frame_count % 50 == 0:
                    log.info(f"*** PYGAME: Caught frame {self._frame_count}, cycles={self.cpu.cycles_executed} ***")

            # Create memory wrappers for VIC
            # Use VIC's snapshot (taken at VBlank) if available, otherwise live RAM
            # The snapshot is only 16KB (one VIC bank), so we need to adjust addresses
            class RAMWrapper:
                def __init__(wrapper_self, snapshot, snapshot_bank, live_ram):
                    wrapper_self.snapshot = snapshot
                    wrapper_self.snapshot_bank = snapshot_bank
                    wrapper_self.live_ram = live_ram

                def __getitem__(wrapper_self, index):
                    if wrapper_self.snapshot is not None:
                        # Convert absolute address to bank-relative offset
                        # The snapshot covers snapshot_bank to snapshot_bank + 16KB
                        relative_index = index - wrapper_self.snapshot_bank
                        if 0 <= relative_index < len(wrapper_self.snapshot):
                            return wrapper_self.snapshot[relative_index]
                        # Address outside snapshot bank - fall through to live RAM
                    return int(wrapper_self.live_ram[index])

            class ColorRAMWrapper:
                def __init__(wrapper_self, snapshot, live_color):
                    wrapper_self.snapshot = snapshot
                    wrapper_self.live_color = live_color

                def __getitem__(wrapper_self, index):
                    if wrapper_self.snapshot is not None:
                        return wrapper_self.snapshot[index] & 0x0F
                    return wrapper_self.live_color[index] & 0x0F

            ram_wrapper = RAMWrapper(
                self.vic.ram_snapshot,
                self.vic.ram_snapshot_bank,
                self.cpu.ram
            )
            color_wrapper = ColorRAMWrapper(
                self.vic.color_snapshot,
                self.memory.ram_color
            )

            # Let VIC render the complete frame (border + text)
            self.vic.render_frame(self.pygame_surface, ram_wrapper, color_wrapper)

            # Scale and blit to screen
            scaled_surface = pygame.transform.scale(
                self.pygame_surface,
                (self.vic.total_width * self.scale, self.vic.total_height * self.scale)
            )
            self.pygame_screen.blit(scaled_surface, (0, 0))
            pygame.display.flip()

            # Also render terminal repl output (screen with colors)
            # Force full redraw since pygame already handled the dirty tracking
            self.dirty_tracker.force_redraw()
            self._render_terminal_repl()

        except Exception as e:
            log.error(f"Error rendering pygame display: {e}")

    def _pump_pygame_events(self) -> None:
        """Process pygame events without rendering.

        Called when the frame_complete wait times out to keep the UI
        responsive (handle window close, keyboard input, etc.).
        """
        if not self.pygame_available or self.pygame_screen is None:
            return

        try:
            import pygame

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    import sys
                    sys.exit(0)
                elif event.type == pygame.KEYDOWN:
                    if DEBUG_KEYBOARD:
                        log.info(f"*** PYGAME KEYDOWN EVENT: key={event.key} ***")
                    self._handle_pygame_keyboard(event, pygame)
                elif event.type == pygame.KEYUP:
                    self._handle_pygame_keyboard(event, pygame)

        except Exception as e:
            log.error(f"Error pumping pygame events: {e}")

    # ASCII to C64 keyboard matrix mapping
    # Maps ASCII characters to (row, col) positions in the C64 keyboard matrix
    # Some characters require SHIFT to be pressed
    ASCII_TO_MATRIX = {
        # Letters (unshifted = uppercase on C64 in default mode)
        'A': (1, 2), 'B': (3, 4), 'C': (2, 4), 'D': (2, 2), 'E': (1, 6),
        'F': (2, 5), 'G': (3, 2), 'H': (3, 5), 'I': (4, 1), 'J': (4, 2),
        'K': (4, 5), 'L': (5, 2), 'M': (4, 4), 'N': (4, 7), 'O': (4, 6),
        'P': (5, 1), 'Q': (7, 6), 'R': (2, 1), 'S': (1, 5), 'T': (2, 6),
        'U': (3, 6), 'V': (3, 7), 'W': (1, 1), 'X': (2, 7), 'Y': (3, 1),
        'Z': (1, 4),
        # Lowercase (same matrix position, C64 handles shift mode internally)
        'a': (1, 2), 'b': (3, 4), 'c': (2, 4), 'd': (2, 2), 'e': (1, 6),
        'f': (2, 5), 'g': (3, 2), 'h': (3, 5), 'i': (4, 1), 'j': (4, 2),
        'k': (4, 5), 'l': (5, 2), 'm': (4, 4), 'n': (4, 7), 'o': (4, 6),
        'p': (5, 1), 'q': (7, 6), 'r': (2, 1), 's': (1, 5), 't': (2, 6),
        'u': (3, 6), 'v': (3, 7), 'w': (1, 1), 'x': (2, 7), 'y': (3, 1),
        'z': (1, 4),
        # Digits
        '0': (4, 3), '1': (7, 0), '2': (7, 3), '3': (1, 0), '4': (1, 3),
        '5': (2, 0), '6': (2, 3), '7': (3, 0), '8': (3, 3), '9': (4, 0),
        # Special characters
        ' ': (7, 4),      # SPACE
        '\n': (0, 1),     # RETURN
        '\r': (0, 1),     # RETURN
        '+': (5, 0),
        '-': (5, 3),
        '*': (6, 1),
        '/': (6, 7),
        '=': (6, 5),
        '.': (5, 4),
        ',': (5, 7),
        ':': (5, 5),
        ';': (6, 2),
        '@': (5, 6),
        '#': None,        # Requires SHIFT+3 (handled specially)
        '$': None,        # Requires SHIFT+4 (handled specially)
        '%': None,        # Requires SHIFT+5 (handled specially)
        '(': None,        # Requires SHIFT+8 (handled specially)
        ')': None,        # Requires SHIFT+9 (handled specially)
        '"': None,        # Requires SHIFT+2 (handled specially)
        '!': None,        # Requires SHIFT+1 (handled specially)
        '?': None,        # Requires SHIFT+/ (handled specially)
        '<': None,        # Requires SHIFT+, (handled specially)
        '>': None,        # Requires SHIFT+. (handled specially)
    }

    # Characters that require SHIFT: (shift_row, shift_col, key_row, key_col)
    ASCII_SHIFTED = {
        '!': (1, 7, 7, 0),   # SHIFT + 1
        '"': (1, 7, 7, 3),   # SHIFT + 2
        '#': (1, 7, 1, 0),   # SHIFT + 3
        '$': (1, 7, 1, 3),   # SHIFT + 4
        '%': (1, 7, 2, 0),   # SHIFT + 5
        '&': (1, 7, 2, 3),   # SHIFT + 6
        "'": (1, 7, 3, 0),   # SHIFT + 7
        '(': (1, 7, 3, 3),   # SHIFT + 8
        ')': (1, 7, 4, 0),   # SHIFT + 9
        '?': (1, 7, 6, 7),   # SHIFT + /
        '<': (1, 7, 5, 7),   # SHIFT + ,
        '>': (1, 7, 5, 4),   # SHIFT + .
    }

    def ascii_to_key_press(self, char: str) -> tuple:
        """Convert ASCII character to C64 key press.

        Arguments:
            char: Single ASCII character

        Returns:
            Tuple of (needs_shift, row, col) or None if not mappable
        """
        if char in self.ASCII_SHIFTED:
            shift_row, shift_col, key_row, key_col = self.ASCII_SHIFTED[char]
            return (True, key_row, key_col)
        elif char in self.ASCII_TO_MATRIX:
            pos = self.ASCII_TO_MATRIX[char]
            if pos is not None:
                return (False, pos[0], pos[1])
        return None

    def type_character(self, char: str, hold_cycles: int = 5000) -> None:
        """Simulate typing a character on the C64 keyboard.

        Arguments:
            char: Single ASCII character to type
            hold_cycles: Number of CPU cycles to hold the key down
        """
        key_info = self.ascii_to_key_press(char)
        if key_info is None:
            log.warning(f"Cannot type character: {repr(char)}")
            return

        needs_shift, row, col = key_info

        # Press SHIFT if needed
        if needs_shift:
            self.cia1.press_key(1, 7)  # Left SHIFT

        # Press the key
        self.cia1.press_key(row, col)

        # Run CPU for some cycles to let the KERNAL process the keypress
        try:
            self.cpu.execute(cycles=hold_cycles)
        except errors.CPUCycleExhaustionError:
            pass

        # Release the key
        self.cia1.release_key(row, col)

        # Release SHIFT if it was pressed
        if needs_shift:
            self.cia1.release_key(1, 7)

        # Run a bit more to ensure key release is processed
        try:
            self.cpu.execute(cycles=hold_cycles // 2)
        except errors.CPUCycleExhaustionError:
            pass

    def type_string(self, text: str, hold_cycles: int = 5000) -> None:
        """Type a string of characters on the C64 keyboard.

        Arguments:
            text: String to type
            hold_cycles: Number of CPU cycles to hold each key down
        """
        for char in text:
            self.type_character(char, hold_cycles)

    def _handle_terminal_input(self, char: str) -> bool:
        """Handle a single character of terminal input.

        Converts ASCII input to C64 key presses. Handles escape sequences
        for arrow keys and other special keys.

        Arguments:
            char: Single character from terminal input

        Returns:
            True if Ctrl+C was pressed (should exit), False otherwise
        """
        import sys as _sys
        import time

        # Handle special keys
        if char == '\x03':  # Ctrl+C
            return True
        elif char == '\x1b':  # Escape sequence
            # Read the rest of the escape sequence
            try:
                import select
                if select.select([_sys.stdin], [], [], 0.1)[0]:
                    seq = _sys.stdin.read(2)
                    if seq == '[A':  # Up arrow -> CRSR UP (SHIFT + CRSR DOWN)
                        self.cia1.press_key(1, 7)  # SHIFT
                        self.cia1.press_key(0, 7)  # CRSR DOWN
                        time.sleep(0.05)
                        self.cia1.release_key(0, 7)
                        self.cia1.release_key(1, 7)
                    elif seq == '[B':  # Down arrow -> CRSR DOWN
                        self.cia1.press_key(0, 7)
                        time.sleep(0.05)
                        self.cia1.release_key(0, 7)
                    elif seq == '[C':  # Right arrow -> CRSR RIGHT
                        self.cia1.press_key(0, 2)
                        time.sleep(0.05)
                        self.cia1.release_key(0, 2)
                    elif seq == '[D':  # Left arrow -> CRSR LEFT (SHIFT + CRSR RIGHT)
                        self.cia1.press_key(1, 7)  # SHIFT
                        self.cia1.press_key(0, 2)  # CRSR RIGHT
                        time.sleep(0.05)
                        self.cia1.release_key(0, 2)
                        self.cia1.release_key(1, 7)
                    elif seq == '[3':  # Delete key (followed by ~)
                        if select.select([_sys.stdin], [], [], 0.1)[0]:
                            _sys.stdin.read(1)  # Consume the ~
                        self.cia1.press_key(0, 0)  # DEL
                        time.sleep(0.05)
                        self.cia1.release_key(0, 0)
            except ImportError:
                pass  # select not available
        elif char == '\x7f':  # Backspace
            self.cia1.press_key(0, 0)  # DEL
            time.sleep(0.05)
            self.cia1.release_key(0, 0)
        else:
            # Regular character - just press and release the key
            key_info = self.ascii_to_key_press(char)
            if key_info:
                needs_shift, row, col = key_info
                if needs_shift:
                    self.cia1.press_key(1, 7)  # SHIFT
                self.cia1.press_key(row, col)
                time.sleep(0.05)  # Hold key briefly
                self.cia1.release_key(row, col)
                if needs_shift:
                    self.cia1.release_key(1, 7)

        return False

    def run_repl(self, max_cycles: int = INFINITE_CYCLES) -> None:
        """Run the C64 in REPL mode with terminal input.

        This mode renders the C64 screen to the terminal and accepts
        keyboard input, converting ASCII to C64 key presses.

        Note: REPL mode requires Unix-like terminal support (termios, tty).
        It is not available on Windows.

        Arguments:
            max_cycles: Maximum cycles to run (default: infinite)
        """
        import sys as _sys
        import threading
        import time

        try:
            import select
            import termios
            import tty
        except ImportError:
            log.error("REPL mode requires Unix-like terminal support (termios, tty).")
            log.error("This mode is not available on Windows. Use --display terminal instead.")
            return

        if not _sys.stdin.isatty():
            log.error("REPL mode requires an interactive terminal (stdin must be a TTY).")
            return

        # Save terminal settings
        old_settings = termios.tcgetattr(_sys.stdin)

        # Shared state between threads
        stop_event = threading.Event()
        cpu_error = None

        def cpu_thread():
            """Run CPU in background thread."""
            nonlocal cpu_error
            try:
                self.cpu.execute(cycles=max_cycles)
            except errors.CPUCycleExhaustionError:
                pass  # Normal termination when max_cycles reached
            except Exception as e:
                cpu_error = e
                log.error(f"CPU thread error: {e}")
            finally:
                stop_event.set()

        try:
            # Put terminal in cbreak mode (character-at-a-time, no echo)
            tty.setcbreak(_sys.stdin.fileno())

            # Start CPU in background thread
            cpu_thread_obj = threading.Thread(target=cpu_thread, daemon=True)
            cpu_thread_obj.start()

            # Main loop: handle input and render
            # Limit render rate to match video timing (PAL ~50Hz, NTSC ~60Hz)
            last_render = 0
            render_interval = self.video_timing.render_interval

            while not stop_event.is_set():
                # Check for input (non-blocking with short timeout)
                if select.select([_sys.stdin], [], [], 0.01)[0]:
                    char = _sys.stdin.read(1)
                    if self._handle_terminal_input(char):
                        break  # Ctrl+C pressed

                # Render at limited rate to avoid terminal buffer overflow
                now = time.time()
                if now - last_render >= render_interval:
                    self.dirty_tracker.force_redraw()
                    self._render_terminal_repl()
                    last_render = now

        except KeyboardInterrupt:
            pass
        finally:
            stop_event.set()
            # Wait for CPU thread to finish
            cpu_thread_obj.join(timeout=0.5)

            # Restore terminal settings
            termios.tcsetattr(_sys.stdin, termios.TCSADRAIN, old_settings)

            # Clear screen and show final state
            _sys.stdout.write("\033[2J\033[H")
            _sys.stdout.flush()
            self.show_screen()

            # Re-raise CPU error if any
            if cpu_error:
                raise cpu_error

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
    C64.args(parser)
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Set debug flags from command-line arguments
    global DEBUG_CIA, DEBUG_VIC, DEBUG_JIFFY, DEBUG_KEYBOARD
    global DEBUG_SCREEN, DEBUG_CURSOR, DEBUG_KERNAL, DEBUG_BASIC
    if args.debug_cia:
        DEBUG_CIA = True
    if args.debug_vic:
        DEBUG_VIC = True
    if args.debug_jiffy:
        DEBUG_JIFFY = True
    if args.debug_keyboard:
        DEBUG_KEYBOARD = True
    if args.debug_screen:
        DEBUG_SCREEN = True
    if args.debug_cursor:
        DEBUG_CURSOR = True
    if args.debug_kernal:
        DEBUG_KERNAL = True
    if args.debug_basic:
        DEBUG_BASIC = True

    try:
        # Initialize C64
        c64 = C64(rom_dir=args.rom_dir, display_mode=args.display, scale=args.scale, enable_irq=not args.no_irq, video_chip=args.video_chip)
        log.info(f"VIC-II chip: {c64.video_chip} ({c64.video_timing.refresh_hz:.2f}Hz, {c64.video_timing.cpu_freq/1e6:.3f}MHz)")

        # Start with minimal logging - will auto-enable when BASIC ROM is entered
        # This avoids flooding the console during KERNAL boot
        logging.getLogger("mos6502").setLevel(logging.CRITICAL)
        logging.getLogger("mos6502.cpu.flags").setLevel(logging.CRITICAL)
        log.info("CPU logging will enable when BASIC ROM is entered")

        # Load cartridge BEFORE reset if specified
        # Cartridge ROMs affect memory banking and may provide auto-start vectors
        if args.cartridge:
            c64.load_cartridge(args.cartridge, args.cartridge_type)
            log.info(f"Cartridge type: {c64.cartridge_type}")

        # ROMs are automatically loaded in C64.__init__()
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
        program_end_addr = None
        if args.program:
            actual_load_addr, program_end_addr = c64.load_program(
                args.program, load_address=args.load_address
            )
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

        # Handle --run: boot to BASIC, load program, inject RUN command, then continue
        if args.run and args.program and not args.no_roms:
            log.info("Auto-run enabled: booting until KERNAL waits for input...")
            # Boot until KERNAL is waiting for keyboard input (more reliable than stop_on_basic)
            c64.run(max_cycles=args.max_cycles, stop_on_kernal_input=True, throttle=args.throttle)
            # Re-load the program AFTER boot (KERNAL clears $0801 during boot)
            # This is the same as a real C64's LOAD command
            actual_load_addr, program_end_addr = c64.load_program(
                args.program, load_address=args.load_address
            )
            log.info(f"Program loaded at ${actual_load_addr:04X}-${program_end_addr - 1:04X}")
            # Update BASIC pointers so RUN knows where the program ends
            if program_end_addr is not None:
                c64.update_basic_pointers(program_end_addr)
            # Inject "RUN" + RETURN into keyboard buffer
            c64.inject_keyboard_buffer("RUN\r")
            log.info("RUN command injected, continuing execution...")
            # Continue running
            if args.display == "repl":
                c64.run_repl(max_cycles=args.max_cycles)
            else:
                c64.run(max_cycles=args.max_cycles, throttle=args.throttle)
        elif args.display == "repl":
            # REPL mode: interactive terminal with keyboard input
            c64.run_repl(max_cycles=args.max_cycles)
        else:
            c64.run(max_cycles=args.max_cycles, stop_on_basic=args.stop_on_basic, throttle=args.throttle)

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
