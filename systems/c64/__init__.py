#!/usr/bin/env python3
"""Commodore 64 Emulator using the mos6502 CPU package."""

import logging
import sys
from pathlib import Path
from typing import Optional

from mos6502 import CPU, CPUVariant, errors, add_cpu_arguments
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
from c64.cia1 import (
    CIA1,
    PADDLE_1_FIRE,
    PADDLE_2_FIRE,
    MOUSE_LEFT_BUTTON,
    MOUSE_RIGHT_BUTTON,
    LIGHTPEN_BUTTON,
    JOYSTICK_UP,
    JOYSTICK_DOWN,
    JOYSTICK_LEFT,
    JOYSTICK_RIGHT,
    JOYSTICK_FIRE,
)
from c64.cia2 import CIA2
from c64.sid import SID
from c64.vic import (
    VideoTiming,
    ScreenDirtyTracker,
    C64VIC,
    COLORS,
    c64_to_ansi_fg,
    c64_to_ansi_bg,
    ANSI_RESET,
    PAL,
    NTSC,
)
from c64.memory import (
    C64Memory,
    BASIC_ROM_START,
    BASIC_ROM_END,
    BASIC_ROM_SIZE,
    KERNAL_ROM_START,
    KERNAL_ROM_END,
    KERNAL_ROM_SIZE,
    CHAR_ROM_START,
    CHAR_ROM_END,
    CHAR_ROM_SIZE,
    VIC_START,
    VIC_END,
    SID_START,
    SID_END,
    COLOR_RAM_START,
    COLOR_RAM_END,
    CIA1_START,
    CIA1_END,
    CIA2_START,
    CIA2_END,
    BASIC_PROGRAM_START,
)
from c64.drive import (
    Drive1541,
    IECBus,
    D64Image,
    ThreadedDrive1541,
    ThreadedIECBus,
    MultiprocessDrive1541,
    MultiprocessIECBus,
    SharedIECState,
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
        core_group.add_argument(
            "--mouse",
            action="store_true",
            help="Enable 1351 proportional mouse emulation (pygame mode only)",
        )
        core_group.add_argument(
            "--mouse-port",
            type=int,
            choices=[1, 2],
            default=1,
            help="Joystick port for mouse (1 or 2, default: 1)",
        )
        core_group.add_argument(
            "--mouse-sensitivity",
            type=float,
            default=1.0,
            help="Mouse sensitivity multiplier (default: 1.0)",
        )
        core_group.add_argument(
            "--paddle",
            action="store_true",
            help="Enable paddle emulation using mouse position (pygame mode only)",
        )
        core_group.add_argument(
            "--paddle-port",
            type=int,
            choices=[1, 2],
            default=1,
            help="Joystick port for paddles (1 or 2, default: 1)",
        )
        core_group.add_argument(
            "--lightpen",
            action="store_true",
            help="Enable lightpen emulation using mouse position (pygame mode only, port 1)",
        )
        core_group.add_argument(
            "--joystick",
            action="store_true",
            help="Enable keyboard joystick emulation (numpad or WASD+Space)",
        )
        # CPU variant selection - uses core library function
        add_cpu_arguments(parser, group_name="CPU Options")

        core_group.add_argument(
            "--joystick-port",
            type=int,
            choices=[1, 2],
            default=2,
            help="Joystick port for keyboard emulation (1 or 2, default: 2)",
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

        # Disk drive options
        drive_group = parser.add_argument_group("Disk Drive Options")
        drive_group.add_argument(
            "--disk",
            type=Path,
            help="D64 disk image to insert into drive 8",
        )
        drive_group.add_argument(
            "--drive-rom",
            type=Path,
            help="1541 DOS ROM file (default: <rom-dir>/1541.rom)",
        )
        drive_group.add_argument(
            "--no-drive",
            action="store_true",
            help="Disable 1541 drive emulation (faster boot, no disk access)",
        )
        drive_group.add_argument(
            "--drive-runner",
            choices=["threaded", "synchronous", "multiprocess"],
            default="threaded",
            dest="drive_runner",
            help="Drive emulation runner: threaded (default), synchronous, or multiprocess",
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
        exec_group.add_argument(
            "--stop-on-illegal-instruction",
            action="store_true",
            help="Stop and dump crash report when an illegal instruction is executed",
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
            cpu_variant=getattr(args, 'cpu', '6502'),
            verbose_cycles=getattr(args, 'verbose_cycles', False),
        )


    def __init__(self, rom_dir: Path = Path("./roms"), display_mode: str = "pygame", scale: int = 2, enable_irq: bool = True, video_chip: str = "6569", cpu_variant: str = "6502", verbose_cycles: bool = False) -> None:
        """Initialize the C64 emulator.

        Arguments:
            rom_dir: Directory containing ROM files (basic, kernal, char)
            display_mode: Display mode (pygame [default], terminal, headless)
                         If pygame fails to initialize, will automatically fall back to terminal
            scale: Pygame window scaling factor
            enable_irq: Enable IRQ injection (default: True)
            video_chip: VIC-II chip variant ("6569" for PAL, "6567R8" for NTSC,
                       "6567R56A" for old NTSC). PAL/NTSC are aliases.
            cpu_variant: CPU variant to emulate ("6502", "6502A", "6502C", "65C02").
                        Default is "6502" (NMOS 6502). Note: The C64 uses a 6510
                        which is essentially a 6502 with I/O ports.
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
        # Parse the cpu_variant string to get the enum
        self._cpu_variant = CPUVariant.from_string(cpu_variant)
        self.cpu = CPU(cpu_variant=self._cpu_variant, verbose_cycles=verbose_cycles)

        log.info(f"Initialized CPU: {self.cpu.variant_name}")

        # Storage for ROMs
        self.basic_rom: Optional[bytes] = None
        self.kernal_rom: Optional[bytes] = None
        self.char_rom: Optional[bytes] = None
        self.vic: Optional[C64VIC] = None
        self.cia1: Optional[CIA1] = None
        self.cia2: Optional[CIA2] = None

        # Cartridge support - the Cartridge object handles all banking logic
        # and provides EXROM/GAME signals. Stored on C64Memory, accessed via self.memory.cartridge
        # Cartridge type string for display purposes
        self.cartridge_type: str = "none"  # "none", "8k", "16k", "error"

        # 1541 Disk Drive support
        self.iec_bus: Optional[IECBus] = None
        self.drive8: Optional[Drive1541] = None
        self.drive_enabled: bool = False  # Set by attach_drive()

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

        # Execution timing for speedup calculation
        self._execution_start_time: Optional[float] = None
        self._execution_end_time: Optional[float] = None

        # Rolling average speed tracking (default 10 samples = 10 second window)
        from collections import deque
        self._speed_sample_count: int = 10
        self._speed_samples: deque[float] = deque(maxlen=self._speed_sample_count)
        self._last_sample_time: float = 0.0
        self._last_sample_cycles: int = 0

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
                self.basic_rom = self.load_rom(name, BASIC_ROM_SIZE, "BASIC")
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
                self.kernal_rom = self.load_rom(name, KERNAL_ROM_SIZE, "KERNAL")
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
                self.char_rom = self.load_rom(name, CHAR_ROM_SIZE, "CHAR")
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
        # self._write_rom_to_memory(BASIC_ROM_START, self.basic_rom)
        # self._write_rom_to_memory(KERNAL_ROM_START, self.kernal_rom)
        # self._write_rom_to_memory(CHAR_ROM_START, self.char_rom)


        # Now set up the CIA1, CIA2, SID, and VIC
        self.cia1 = CIA1(cpu=self.cpu)
        self.cia2 = CIA2(cpu=self.cpu)

        # Link the CIAs for FLAG pin cross-triggering (IEC bus simulation)
        self.cia1.set_other_cia(self.cia2)
        self.cia2.set_other_cia(self.cia1)

        self.sid = SID()
        self.vic = C64VIC(char_rom=self.char_rom, cpu=self.cpu, cia2=self.cia2, video_timing=self.video_timing)

        # Initialize memory
        self.memory = C64Memory(
            self.cpu.ram,
            basic_rom=self.basic_rom,
            kernal_rom=self.kernal_rom,
            char_rom=self.char_rom,
            cia1=self.cia1,
            cia2=self.cia2,
            vic=self.vic,
            sid=self.sid,
            dirty_tracker=self.dirty_tracker,
        )
        # Hook up the memory handler so CPU RAM accesses go through C64Memory
        self.cpu.ram.memory_handler = self.memory

        # Give VIC access to C64Memory for VBlank snapshots
        self.vic.set_memory(self.memory)

        # Set up periodic update callback for VIC, CIA1, CIA2, and disk drive
        # VIC checks cycle count and triggers raster IRQs
        # CIA1 counts down timers and triggers timer IRQs
        # CIA2 counts down timers and triggers NMIs
        # IEC bus and drive: The bus updates happen immediately when CIA2 port A
        # is written, and the drive CPU is synchronized at that time. The periodic
        # callback just ensures regular updates for VIC/CIA timers.
        def update_peripherals():
            self.vic.update()
            self.cia1.update()
            self.cia2.update()
            # Note: Drive CPU sync is now handled per-instruction via
            # post_instruction_callback for cycle-accurate IEC timing
            # In headless mode, clear frame_complete since there's no render thread
            if self.display_mode == "headless" and self.vic.frame_complete.is_set():
                self.vic.frame_complete.clear()

        self.cpu.periodic_callback = update_peripherals
        self.cpu.periodic_callback_interval = self.vic.cycles_per_line   # Update every raster line

        log.info("All ROMs loaded into memory")

        # Note: PC is already set from reset vector by cpu.reset() in main()
        # The reset() method handles the complete reset sequence including
        # fetching the vector from $FFFC/$FFFD and setting PC accordingly
        log.info(f"PC initialized to ${self.cpu.PC:04X} (from reset vector at ${self.RESET_VECTOR_ADDR:04X})")

    def attach_drive(self, drive_rom_path: Optional[Path] = None, disk_path: Optional[Path] = None,
                      runner: str = "threaded") -> bool:
        """Attach a 1541 disk drive to the IEC bus.

        Supports multiple ROM formats:
        - Single 16KB ROM (1541-II style): 1541.rom, 1541-II.251968-03.bin, etc.
        - Two 8KB ROMs (original 1541): 1541-c000.bin + 1541-e000.bin

        Args:
            drive_rom_path: Path to 1541 DOS ROM (default: auto-detect in rom_dir)
            disk_path: Optional D64 disk image to insert
            runner: Drive execution mode:
                    - "threaded" (default): Uses ThreadedIECBus for atomic state
                    - "synchronous": Cycle-accurate emulation
                    - "multiprocess": Drive runs in separate process (bypasses GIL)

        Returns:
            True if drive attached successfully, False otherwise
        """
        rom_path = drive_rom_path
        rom_path_e000 = None

        if rom_path is None:
            # Try to find 1541 ROM(s) in rom_dir
            # Priority 1: Single 16KB ROM files (most common)
            rom_16k_names = [
                "1541.rom",
                "1541-II.rom",
                "1541-II.251968-03.bin",  # Most compatible 1541-II ROM
                "1541C.251968-01.bin",
                "1541C.251968-02.bin",
                "1541-II.355640-01.bin",
                "dos1541",
                "dos1541.rom",
            ]
            for name in rom_16k_names:
                candidate = self.rom_dir / name
                if candidate.exists():
                    rom_path = candidate
                    break

            # Priority 2: Two 8KB ROM files (original 1541 style)
            if rom_path is None:
                # Look for C000 ROM
                c000_names = [
                    "1541-c000.325302-01.bin",
                    "1541-c000.bin",
                    "1540-c000.325302-01.bin",
                ]
                # Look for E000 ROM (multiple revisions available)
                e000_names = [
                    "1541-e000.901229-05.bin",  # Short-board, most common
                    "1541-e000.901229-03.bin",  # Long-board with autoboot
                    "1541-e000.901229-02.bin",
                    "1541-e000.901229-01.bin",
                    "1541-e000.bin",
                ]

                for c000_name in c000_names:
                    c000_candidate = self.rom_dir / c000_name
                    if c000_candidate.exists():
                        # Found C000 ROM, now look for E000 ROM
                        for e000_name in e000_names:
                            e000_candidate = self.rom_dir / e000_name
                            if e000_candidate.exists():
                                rom_path = c000_candidate
                                rom_path_e000 = e000_candidate
                                break
                        if rom_path_e000 is not None:
                            break

        if rom_path is None or not rom_path.exists():
            log.warning(f"1541 ROM not found in {self.rom_dir}. Drive disabled.")
            log.warning("  Expected: 1541.rom (16KB) or 1541-c000.bin + 1541-e000.bin (8KB each)")
            return False

        # Track the runner mode
        self.drive_runner = runner

        if runner == "multiprocess":
            # Multiprocess mode: Drive runs in separate process (bypasses GIL)
            import os
            import time

            # Create shared memory for IEC state (use PID + time for uniqueness)
            unique_id = f"{os.getpid()}_{int(time.time() * 1000) % 1000000}"
            self._iec_shared_state = SharedIECState(
                name=f"iec_bus_{unique_id}",
                create=True
            )

            # Create multiprocess IEC bus
            self.iec_bus = MultiprocessIECBus(self._iec_shared_state)
            self.iec_bus.connect_c64(self.cia2)
            self.cia2.set_iec_bus(self.iec_bus)

            # Create and start drive subprocess
            self.drive8 = MultiprocessDrive1541(device_number=8)
            self.drive8.start_process(
                rom_path=rom_path,
                rom_path_e000=rom_path_e000,
                disk_path=disk_path,
                shared_state=self._iec_shared_state,
            )

            # Wire up tick synchronization Events
            tick_request, tick_done = self.drive8.get_tick_events()
            self.iec_bus.set_tick_events(tick_request, tick_done)

            self.drive_enabled = True

            # Set up synchronous tick-based execution
            # Similar to threaded mode but with batching to reduce IPC overhead
            self._mp_accumulated_cycles = 0
            self._mp_batch_size = 100  # Cycles per IPC call (balance timing vs overhead)

            def sync_multiprocess(cpu, cycles):
                """Accumulate cycles and sync with drive subprocess."""
                if self.drive8 and self._iec_shared_state:
                    # Update IEC bus state
                    self.iec_bus.update()

                    # Accumulate cycles
                    self._mp_accumulated_cycles += cycles

                    # When batch is full, sync with drive
                    if self._mp_accumulated_cycles >= self._mp_batch_size:
                        batch = self._mp_accumulated_cycles
                        self._mp_accumulated_cycles = 0

                        # Update C64 cycle counter
                        self._iec_shared_state.set_c64_cycles(cpu.cycles_executed)

                        # Wait for drive to catch up to our cycle count
                        tick_request, tick_done = self.drive8.get_tick_events()
                        target_cycles = cpu.cycles_executed

                        # Signal drive and wait for it to process
                        import time
                        max_wait = 0.1  # seconds
                        start = time.time()
                        while time.time() - start < max_wait:
                            tick_request.set()
                            drive_cycles = self._iec_shared_state.get_drive_cycles()
                            if drive_cycles >= target_cycles - 50:
                                break
                            time.sleep(0.00001)  # 10us

                        # Read bus state after drive processed
                        self.iec_bus.atn, self.iec_bus.clk, self.iec_bus.data = \
                            self._iec_shared_state.get_bus_state(is_drive=False)

            self.cpu.post_tick_callback = sync_multiprocess
            log.info(f"1541 drive 8 attached in MULTIPROCESS mode (ROM: {rom_path.name})")
            return True

        elif runner == "threaded":
            # Threaded mode: Uses ThreadedIECBus for atomic state updates
            self.iec_bus = ThreadedIECBus()
            self.iec_bus.connect_c64(self.cia2)
            self.cia2.set_iec_bus(self.iec_bus)

            # Create threaded drive 8
            self.drive8 = ThreadedDrive1541(device_number=8)
        else:
            # Synchronous mode: Cycle-accurate but slower
            self.iec_bus = IECBus()
            self.iec_bus.connect_c64(self.cia2)
            self.cia2.set_iec_bus(self.iec_bus)

            # Create standard drive 8
            self.drive8 = Drive1541(device_number=8)

        # Create a separate CPU for the drive (for threaded/synchronous modes)
        # The 1541 uses a full 6502 (not 6510)
        drive_cpu = CPU(cpu_variant=CPUVariant.NMOS_6502, verbose_cycles=False)
        self.drive8.cpu = drive_cpu

        # Set up drive CPU memory handler
        drive_cpu.ram.memory_handler = self.drive8.memory

        # Load 1541 ROM (supports both 16KB single file and 8KB+8KB split)
        try:
            self.drive8.load_rom(rom_path, rom_path_e000)
        except Exception as e:
            log.error(f"Failed to load 1541 ROM: {e}")
            self.drive8 = None
            self.iec_bus = None
            return False

        # Connect drive to IEC bus
        if runner == "threaded":
            self.drive8.connect_to_threaded_bus(self.iec_bus)
        else:
            self.iec_bus.connect_drive(self.drive8)

        # Insert disk if provided
        if disk_path is not None:
            try:
                self.drive8.insert_disk(disk_path)
            except Exception as e:
                log.error(f"Failed to insert disk: {e}")

        # Reset drive to initialize
        self.drive8.reset()

        self.drive_enabled = True

        if runner == "threaded":
            # Threaded mode: Uses ThreadedIECBus for thread-safe state
            # but still runs drive in lockstep via post_tick_callback
            # The threading benefit is that bus state updates are atomic

            def sync_drive_on_tick_threaded(cpu, cycles):
                """Sync drive CPU and IEC bus after each C64 cycle consumption."""
                if self.drive8 and self.drive8.cpu:
                    # Update IEC bus state so drive sees current C64 outputs
                    self.iec_bus.update()

                    # Run drive for the same number of cycles (1:1 sync)
                    # Call the base class tick() directly since ThreadedDrive1541.tick() is a no-op
                    Drive1541.tick(self.drive8, cycles)

                    # Update IEC bus again so C64 sees drive's response
                    self.iec_bus.update()

            self.cpu.post_tick_callback = sync_drive_on_tick_threaded
            # Note: Not starting drive thread - running synchronously with ThreadedIECBus
            log.info(f"1541 drive 8 attached with ThreadedIECBus (ROM: {rom_path.name})")
        else:
            # Synchronous mode: Set up cycle-accurate IEC synchronization
            # using post_tick_callback. The tick() function is called every
            # time the CPU spends cycles, which is the natural place to
            # synchronize connected hardware.
            #
            # The IEC serial bus is bit-banged and requires tight timing between
            # the C64 and 1541 CPUs. By hooking into tick(), we ensure the drive
            # runs in lockstep with every cycle the C64 spends.

            def sync_drive_on_tick(cpu, cycles):
                """Sync drive CPU and IEC bus after each C64 cycle consumption."""
                if self.drive8 and self.drive8.cpu:
                    # Update IEC bus state so drive sees current C64 outputs
                    self.iec_bus.update()

                    # Run drive for the same number of cycles
                    # The drive's tick() method handles its own cycle budget
                    self.drive8.tick(cycles)

                    # Update IEC bus again so C64 sees drive's response
                    self.iec_bus.update()

            self.cpu.post_tick_callback = sync_drive_on_tick
            log.info(f"1541 drive 8 attached in SYNCHRONOUS mode (ROM: {rom_path.name})")

        return True

    def insert_disk(self, disk_path: Path) -> bool:
        """Insert a D64 disk image into drive 8.

        Args:
            disk_path: Path to D64 disk image

        Returns:
            True if disk inserted successfully
        """
        if not self.drive_enabled or self.drive8 is None:
            log.error("No drive attached. Use --disk or attach_drive() first.")
            return False

        try:
            self.drive8.insert_disk(disk_path)
            return True
        except Exception as e:
            log.error(f"Failed to insert disk: {e}")
            return False

    def eject_disk(self) -> None:
        """Eject the disk from drive 8."""
        if self.drive8 is not None:
            self.drive8.eject_disk()

    def cleanup(self) -> None:
        """Clean up resources (drive subprocess, shared memory, etc.)."""
        # Stop multiprocess drive if running
        if self.drive8 is not None:
            if isinstance(self.drive8, MultiprocessDrive1541):
                self.drive8.stop_process()
            elif isinstance(self.drive8, ThreadedDrive1541):
                self.drive8.stop_thread()

        # Clean up shared memory
        if hasattr(self, '_iec_shared_state') and self._iec_shared_state is not None:
            try:
                self._iec_shared_state.close()
                self._iec_shared_state.unlink()
            except Exception:
                pass
            self._iec_shared_state = None

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
                elif load_address == KERNAL_ROM_START:
                    # Ultimax mode: ROM at $E000-$FFFF replaces KERNAL
                    ultimax_romh_data = rom_data
                    results.ultimax_romh_valid = True
                    log.info(f"Loaded Ultimax ROMH: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                else:
                    log.warning(f"Unknown CHIP load address: ${load_address:04X}")
            elif hardware_type == 3:
                # Type 3: Final Cartridge III - 4 x 16KB banks
                # Each bank is a single 16KB CHIP packet at $8000
                if load_address == self.ROML_START:
                    banks[bank_number] = rom_data
                    results.roml_valid = True
                    results.bank_switching_valid = len(banks) > 1
                    log.info(f"Loaded FC3 bank {bank_number}: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                else:
                    log.warning(f"Unknown CHIP load address for Type 3: ${load_address:04X}")
            elif hardware_type == 4 or hardware_type == 13:
                # Type 4: Simons' BASIC - 16KB cartridge with ROML + ROMH
                # Type 13: Final Cartridge I - 16KB cartridge with ROML + ROMH
                # Two CHIP packets: one for ROML at $8000, one for ROMH at $A000
                if load_address == self.ROML_START:
                    roml_data = rom_data
                    results.roml_valid = True
                    log.info(f"Loaded ROML: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                elif load_address == self.ROMH_START:
                    romh_data = rom_data
                    results.romh_valid = True
                    log.info(f"Loaded ROMH: ${load_address:04X}-${load_address + rom_size - 1:04X} ({rom_size} bytes)")
                else:
                    log.warning(f"Unknown CHIP load address for Type {hardware_type}: ${load_address:04X}")
            else:
                # Banked cartridges (Type 1, 5+): Collect all banks
                # Each bank is typically 8KB at $8000
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
        elif hardware_type == 4:
            # Type 4: Simons' BASIC - needs both ROML and ROMH
            if roml_data is None or romh_data is None:
                # Missing ROM data - generate error cart
                self._load_error_cartridge_with_results(results)
                return

            cartridge = create_cartridge(
                hardware_type=4,
                roml_data=roml_data,
                romh_data=romh_data,
                name=cart_name,
            )
            self.cartridge_type = "simons_basic"
        elif hardware_type == 13:
            # Type 13: Final Cartridge I - needs both ROML and ROMH
            if roml_data is None:
                # Missing ROM data - generate error cart
                self._load_error_cartridge_with_results(results)
                return

            cartridge = create_cartridge(
                hardware_type=13,
                roml_data=roml_data,
                romh_data=romh_data,
                name=cart_name,
            )
            self.cartridge_type = "final_cartridge_i"
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
            # Disable pygame vsync - we do our own frame timing via VIC
            # This prevents pygame.display.flip() from blocking
            width = total_width * self.scale
            height = total_height * self.scale
            try:
                # pygame 2.0+ supports vsync parameter
                self.pygame_screen = pygame.display.set_mode((width, height), vsync=0)
            except TypeError:
                # Older pygame doesn't support vsync parameter
                self.pygame_screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption(f"C64 Emulator - {self.get_video_standard()} ({self.video_chip})")

            # Enable key repeat (delay=300ms before repeat, interval=30ms between repeats)
            # This matches typical terminal key repeat behavior
            pygame.key.set_repeat(300, 30)

            # Initialize clipboard support for Ctrl+V paste
            try:
                pygame.scrap.init()
            except Exception as e:
                log.warning(f"Clipboard support unavailable: {e}")

            # Create the rendering surface (384x270 with border)
            self.pygame_surface = pygame.Surface((total_width, total_height))

            log.info(f"Pygame display initialized: {width}x{height} (scale={self.scale})")
            return True

        except Exception as e:
            log.error(f"Failed to initialize pygame: {e}")
            self.pygame_available = False
            return False

    def set_speed_sample_count(self, count: int) -> None:
        """Set the number of samples for rolling average speed calculation.

        Args:
            count: Number of samples to keep (e.g., 10 = 10 second rolling window).
                   Set to 0 to disable rolling average.
        """
        from collections import deque
        self._speed_sample_count = count
        if count > 0:
            self._speed_samples = deque(maxlen=count)
        else:
            self._speed_samples = deque(maxlen=1)  # Keep at least 1 for the API
            self._speed_samples.clear()

    def _record_speed_sample(self) -> bool:
        """Record a speed sample for rolling average (rate-limited to once per second).

        Returns:
            True if a sample was recorded, False if rate-limited.
        """
        import time
        now = time.time()

        # Only record once per second
        if self._last_sample_time > 0 and now - self._last_sample_time < 1.0:
            return False

        # Calculate cycles since last sample
        current_cycles = self.cpu.cycles_executed
        if self._last_sample_time > 0:
            delta_time = now - self._last_sample_time
            delta_cycles = current_cycles - self._last_sample_cycles
            if delta_time > 0:
                sample_cps = delta_cycles / delta_time
                self._speed_samples.append(sample_cps)

        self._last_sample_time = now
        self._last_sample_cycles = current_cycles
        return True

    def _update_pygame_title(self, pygame) -> None:
        """Update pygame window title with speed stats (rate-limited to once per second)."""
        if not self._record_speed_sample():
            return

        # Use rolling average if we have samples
        if self._speed_samples:
            cycles_per_second = sum(self._speed_samples) / len(self._speed_samples)
            real_cpu_freq = self.video_timing.cpu_freq
            speedup = cycles_per_second / real_cpu_freq
            chip = self.video_timing.chip_name
            region = "PAL" if chip == "6569" else "NTSC"
            actual_mhz = cycles_per_second / 1e6
            real_mhz = real_cpu_freq / 1e6
            title = (f"C64 Emulator - {region} ({chip}) - "
                     f"{actual_mhz:.3f}MHz ({speedup:.1%} of {real_mhz:.3f}MHz)")
            pygame.display.set_caption(title)

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
            load_address = BASIC_PROGRAM_START

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

    def inject_keyboard_string(self, text: str, cycles_per_chunk: int = 100_000) -> None:
        """Inject a string into the keyboard buffer, handling strings longer than 10 chars.

        For strings longer than 10 characters, this method injects them in chunks
        of 10 characters each, running the CPU between chunks to allow KERNAL
        to process the buffer.

        Arguments:
            text: String to inject (any length, typically ending with \\r for RETURN)
            cycles_per_chunk: CPU cycles to run between chunks (default 100,000)
        """
        from mos6502.errors import CPUCycleExhaustionError

        # Convert to PETSCII
        petscii_text = text.replace('\r', '\x0d').replace('\n', '\x0d')

        # Process in chunks of 10 characters
        chunk_size = 10
        position = 0

        while position < len(petscii_text):
            # Wait for keyboard buffer to be empty
            max_wait_cycles = 1_000_000
            waited = 0
            while int(self.cpu.ram[self.KEYBOARD_BUFFER_SIZE]) > 0 and waited < max_wait_cycles:
                try:
                    self.cpu.execute(cycles=10_000)
                except CPUCycleExhaustionError:
                    pass
                waited += 10_000

            if waited >= max_wait_cycles:
                log.warning("Timeout waiting for keyboard buffer to empty")
                break

            # Inject next chunk
            chunk = petscii_text[position:position + chunk_size]
            for i, char in enumerate(chunk):
                self.cpu.ram[self.KEYBOARD_BUFFER + i] = ord(char)
            self.cpu.ram[self.KEYBOARD_BUFFER_SIZE] = len(chunk)

            log.debug(f"Injected chunk {position//chunk_size + 1}: {len(chunk)} chars")
            position += chunk_size

            # Run CPU to process this chunk
            if position < len(petscii_text):
                try:
                    self.cpu.execute(cycles=cycles_per_chunk)
                except CPUCycleExhaustionError:
                    pass

        log.info(f"Injected '{text.strip()}' into keyboard buffer ({len(petscii_text)} chars total)")

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

        if pc < BASIC_ROM_START:
            return "RAM"
        elif BASIC_ROM_START <= pc <= BASIC_ROM_END:
            # BASIC ROM only visible if bit 0 of port is set
            return "BASIC" if (port & 0x01) else "RAM"
        elif CHAR_ROM_START <= pc <= CHAR_ROM_END:
            # I/O vs CHAR vs RAM depends on bits in port
            if port & 0x04:
                return "I/O"
            elif (port & 0x03) == 0x01:
                return "CHAR"
            else:
                return "RAM"
        elif KERNAL_ROM_START <= pc <= KERNAL_ROM_END:
            # KERNAL ROM only visible if bit 1 of port is set
            return "KERNAL" if (port & 0x02) else "RAM"
        else:
            return "???"

    def get_drive_pc_region(self) -> str:
        """Determine which memory region the drive's PC is currently in.

        1541 memory map:
        - $0000-$07FF: RAM (2KB)
        - $1800-$1BFF: VIA1
        - $1C00-$1FFF: VIA2
        - $C000-$FFFF: ROM (DOS)

        Returns:
            String describing the region: "RAM", "VIA1", "VIA2", "DOS", or "???"
        """
        if not self.drive8 or not self.drive8.cpu:
            return "???"

        pc = self.drive8.cpu.PC

        if pc < 0x0800:
            return "RAM"
        elif 0x1800 <= pc < 0x1C00:
            return "VIA1"
        elif 0x1C00 <= pc < 0x2000:
            return "VIA2"
        elif pc >= 0xC000:
            return "DOS"
        else:
            return "???"

    def _format_cpu_status(self, prefix: str = "C64") -> str:
        """Format C64 CPU status line.

        Args:
            prefix: Label prefix for the status line

        Returns:
            Formatted status string
        """
        from mos6502.flags import format_flags
        flags = format_flags(self.cpu._flags.value)
        region = self.get_pc_region()
        pc = self.cpu.PC

        # Disassemble current instruction
        try:
            inst_str = self.disassemble_instruction(pc)
            inst_display = inst_str.strip()
        except (KeyError, ValueError, IndexError):
            try:
                b0 = self.cpu.ram[pc]
                b1 = self.cpu.ram[pc + 1]
                b2 = self.cpu.ram[pc + 2]
                inst_display = f"{b0:02X} {b1:02X} {b2:02X}  ???"
            except IndexError:
                inst_display = "???"

        return (f"{prefix}: Cycles: {self.cpu.cycles_executed:,} | "
                f"PC=${pc:04X}[{region}] {inst_display:20s} | "
                f"A=${self.cpu.A:02X} X=${self.cpu.X:02X} "
                f"Y=${self.cpu.Y:02X} S=${self.cpu.S & 0xFF:02X} P={flags}")

    def _format_drive_status(self) -> str:
        """Format 1541 drive CPU status line.

        Returns:
            Formatted status string, or empty string if no drive attached
        """
        if not self.drive8 or not self.drive8.cpu:
            return ""

        from mos6502.flags import format_flags
        from mos6502 import instructions

        drive_cpu = self.drive8.cpu
        flags = format_flags(drive_cpu._flags.value)
        region = self.get_drive_pc_region()
        pc = drive_cpu.PC

        # Disassemble current instruction from drive memory
        try:
            b0 = self.drive8.memory.read(pc)
            b1 = self.drive8.memory.read(pc + 1)
            b2 = self.drive8.memory.read(pc + 2)

            # Use the instruction set to get mnemonic and operand size
            if b0 in instructions.InstructionSet.map:
                inst_info = instructions.InstructionSet.map[b0]
                try:
                    num_bytes = int(inst_info.get("bytes", 1))
                except (ValueError, TypeError):
                    num_bytes = 1
                assembler = inst_info.get("assembler", "???")
                mnemonic = assembler.split()[0] if assembler != "???" else "???"
                mode = inst_info.get("addressing", "")
            elif b0 in instructions.OPCODE_LOOKUP:
                opcode_obj = instructions.OPCODE_LOOKUP[b0]
                func_name = opcode_obj.function
                mnemonic = func_name.split("_")[0].upper()
                if "implied" in func_name or "accumulator" in func_name:
                    num_bytes = 1
                elif "relative" in func_name or "immediate" in func_name or "zeropage" in func_name:
                    num_bytes = 2
                else:
                    num_bytes = 3
                mode = ""
            else:
                num_bytes = 1
                mnemonic = "???"
                mode = ""

            # Build hex dump
            hex_bytes = [f"{self.drive8.memory.read(pc + i):02X}"
                        for i in range(min(num_bytes, 3))]
            hex_str = " ".join(hex_bytes).ljust(8)

            # Build operand display
            if num_bytes == 1:
                operand_str = ""
            elif num_bytes == 2:
                operand_str = f" ${b1:02X}"
            else:
                operand = (b2 << 8) | b1
                operand_str = f" ${operand:04X}"

            if mode:
                inst_display = f"{hex_str}  {mnemonic}{operand_str}  ; {mode}"
            else:
                inst_display = f"{hex_str}  {mnemonic}{operand_str}"

        except Exception:
            inst_display = "???"

        return (f"1541: Cycles: {drive_cpu.cycles_executed:,} | "
                f"PC=${pc:04X}[{region}] {inst_display:20s} | "
                f"A=${drive_cpu.A:02X} X=${drive_cpu.X:02X} "
                f"Y=${drive_cpu.Y:02X} S=${drive_cpu.S & 0xFF:02X} P={flags}")

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
        if BASIC_ROM_START <= new_pc <= BASIC_ROM_END:
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
        if BASIC_ROM_START <= pc <= BASIC_ROM_END and not hasattr(self, '_logged_basic_entry'):
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
        stop_on_illegal_instruction: bool = False,
    ) -> None:
        """Run the C64 emulator.

        Arguments:
            max_cycles: Maximum number of CPU cycles to execute
                       (default: INFINITE_CYCLES for continuous execution)
            stop_on_basic: If True, stop execution when BASIC prompt is ready
            stop_on_kernal_input: If True, stop execution when KERNAL is waiting for keyboard input
            throttle: If True, throttle emulation to real-time speed (default: True)
                     Use --no-throttle for benchmarks to run at maximum speed
            stop_on_illegal_instruction: If True, dump crash report on illegal instruction
        """
        # Store for use in error handler
        self._stop_on_illegal_instruction = stop_on_illegal_instruction
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

            # Record execution start time for speedup calculation
            self._execution_start_time = time.perf_counter()

            # Check if we're in a TTY (terminal) for interactive display
            is_tty = _sys.stdout.isatty()

            # All modes: CPU in background thread, display + input in main thread
            # This ensures responsive input handling regardless of display mode
            pygame_mode = self.display_mode == "pygame" and self.pygame_available

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

            # Set up terminal input (works for all modes)
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

            # Main thread handles display + input
            try:
                last_terminal_render = time.perf_counter()
                TERMINAL_RENDER_INTERVAL = 0.1  # 100ms between terminal renders

                while not cpu_done.is_set():
                    # Check stop conditions
                    if stop_on_basic and self.basic_ready:
                        break
                    if stop_on_kernal_input and self.kernal_waiting_for_input:
                        break

                    # Handle terminal keyboard input (all modes)
                    if terminal_input_available:
                        import select
                        if select.select([_sys.stdin], [], [], 0)[0]:
                            char = _sys.stdin.read(1)
                            if self._handle_terminal_input(char):
                                break  # Ctrl+C pressed

                    # Process any pending key releases (non-blocking)
                    self._process_pending_key_releases()

                    # Pump pygame events every iteration (outside of draw loop)
                    if pygame_mode:
                        self._pump_pygame_events()
                        self._process_pygame_key_buffer()

                    # Mode-specific rendering
                    # Use half frame time as timeout - ensures we check twice per frame
                    # even if CPU is slow, while not wasting CPU on excessive polling
                    frame_timeout = 0.5 / self.video_timing.refresh_hz  # ~10ms PAL, ~8ms NTSC

                    if pygame_mode:
                        # Render when VIC has a new frame ready (both pygame and terminal)
                        if self.vic.frame_complete.is_set():
                            self._render_pygame()
                        else:
                            # Tiny sleep to prevent busy-spinning when no frame ready
                            time.sleep(0.001)  # 1ms
                    else:
                        # Terminal/headless: render when VIC has a new frame ready
                        if self.vic.frame_complete.is_set():
                            self.vic.frame_complete.clear()
                            self._check_pc_region()
                            self._render_terminal()
                        else:
                            time.sleep(0.001)  # 1ms

            finally:
                # Signal CPU thread to stop and wait for it
                stop_cpu.set()
                cpu_done.set()
                cpu_thread_obj.join(timeout=0.5)

                # Stop drive thread if running in threaded mode
                if self.drive_enabled and getattr(self, 'drive_threaded', False):
                    if self.drive8 is not None and hasattr(self.drive8, 'stop_thread'):
                        self.drive8.stop_thread()

                # Restore terminal settings if we changed them
                if old_settings is not None:
                    import termios
                    termios.tcsetattr(_sys.stdin, termios.TCSADRAIN, old_settings)

                # Cleanup pygame if used
                if pygame_mode:
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

        except StopIteration as e:
            # PC callback requested stop (e.g., BASIC is ready or KERNAL waiting for input)
            log.info(f"Execution stopped at PC=${self.cpu.PC:04X} ({e})")
        except errors.CPUCycleExhaustionError as e:
            log.info(f"CPU execution completed: {e}")
        except errors.CPUBreakError as e:
            log.info(f"Program terminated (BRK at PC=${self.cpu.PC:04X})")
        except (KeyboardInterrupt, errors.QuitRequestError) as e:
            if isinstance(e, errors.QuitRequestError):
                log.info(f"\nExecution stopped: {e}")
            else:
                log.info("\nExecution interrupted by user")
            log.info(f"PC=${self.cpu.PC:04X}, Cycles={self.cpu.cycles_executed}")
        except (errors.IllegalCPUInstructionError, RuntimeError) as e:
            # Check if we should dump crash report and stop (vs raising)
            if getattr(self, '_stop_on_illegal_instruction', False) and isinstance(e, errors.IllegalCPUInstructionError):
                self.dump_crash_report(exception=e)
                # Don't re-raise - just stop execution cleanly
            else:
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
            # Record execution end time for speedup calculation
            import time
            self._execution_end_time = time.perf_counter()
            # Clean up PC callback
            self._clear_pc_callback()
            # Show screen buffer on termination
            self.show_screen()
            # Clean up drive subprocess if running
            self.cleanup()

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

    def dump_crash_report(self, exception: Exception = None) -> None:
        """Dump comprehensive crash report for illegal instruction or other CPU errors.

        Arguments:
            exception: The exception that triggered the crash (optional)
        """
        print("\n" + "=" * 70)
        print("CRASH REPORT - Illegal Instruction")
        print("=" * 70)

        # Show exception info
        if exception:
            print(f"\nException: {type(exception).__name__}: {exception}")

        # CPU state
        pc = int(self.cpu.PC)
        opcode = self.cpu.ram[pc]
        print(f"\nCPU State at crash:")
        print(f"  PC:     ${pc:04X}  (opcode: ${opcode:02X})")
        print(f"  A:      ${self.cpu.A:02X}")
        print(f"  X:      ${self.cpu.X:02X}")
        print(f"  Y:      ${self.cpu.Y:02X}")
        print(f"  S:      ${self.cpu.S & 0xFF:02X}  (stack pointer)")
        print(f"  P:      ${self.cpu._flags.value:02X}  (N={int(self.cpu.N)} V={int(self.cpu.V)} B={int(self.cpu.B)} D={int(self.cpu.D)} I={int(self.cpu.I)} Z={int(self.cpu.Z)} C={int(self.cpu.C)})")
        print(f"  Cycles: {self.cpu.cycles_executed:,}")

        # Memory region
        region = "RAM"
        if 0xA000 <= pc <= 0xBFFF and (self.memory.read(1) & 0x03):
            region = "BASIC ROM"
        elif 0xD000 <= pc <= 0xDFFF:
            region = "I/O" if (self.memory.read(1) & 0x04) else "CHAR ROM"
        elif 0xE000 <= pc <= 0xFFFF and (self.memory.read(1) & 0x02):
            region = "KERNAL ROM"
        print(f"  Region: {region}")

        # Stack contents (show 16 bytes from current SP)
        sp = self.cpu.S & 0xFF
        print(f"\nStack (${sp:02X} -> $FF):")
        stack_addr = 0x0100 + sp
        print("       ", end="")
        for i in range(16):
            print(f" {i:02X}", end="")
        print()
        for row_start in range(stack_addr, 0x0200, 16):
            if row_start >= 0x0200:
                break
            print(f"  {row_start:04X}:", end="")
            for offset in range(16):
                addr = row_start + offset
                if addr < 0x0200:
                    print(f" {self.cpu.ram[addr]:02X}", end="")
                else:
                    print("   ", end="")
            print()

        # Disassembly around crash
        print(f"\nDisassembly around PC ${pc:04X}:")
        try:
            start_addr = max(0, pc - 16)
            self.show_disassembly(start_addr, num_instructions=20)
        except Exception as e:
            print(f"  Could not disassemble: {e}")

        # Memory around PC
        print(f"\nMemory around PC ${pc:04X}:")
        mem_start = max(0, pc - 32)
        mem_end = min(0xFFFF, pc + 32)
        self.dump_memory(mem_start, mem_end)

        # Zero page (important for 6502)
        print("\nZero page ($00-$FF):")
        self.dump_memory(0x00, 0xFF)

        # Key C64 memory locations
        print("\nKey C64 Memory Locations:")
        print(f"  $00 (DDR):       ${self.cpu.ram[0x00]:02X}")
        print(f"  $01 (Bank):      ${self.cpu.ram[0x01]:02X}")
        print(f"  $90 (KERNAL ST): ${self.cpu.ram[0x90]:02X}")
        print(f"  $9D (Direct):    ${self.cpu.ram[0x9D]:02X}")
        print(f"  $2B-$2C (TXTTAB):${self.cpu.ram[0x2B]:02X}{self.cpu.ram[0x2C]:02X}")
        print(f"  $2D-$2E (VARTAB):${self.cpu.ram[0x2D]:02X}{self.cpu.ram[0x2E]:02X}")

        # Vectors
        print("\nInterrupt Vectors:")
        nmi = self.cpu.ram[0xFFFA] | (self.cpu.ram[0xFFFB] << 8)
        reset = self.cpu.ram[0xFFFC] | (self.cpu.ram[0xFFFD] << 8)
        irq = self.cpu.ram[0xFFFE] | (self.cpu.ram[0xFFFF] << 8)
        print(f"  NMI:   ${nmi:04X}")
        print(f"  RESET: ${reset:04X}")
        print(f"  IRQ:   ${irq:04X}")

        print("\n" + "=" * 70)
        print("END CRASH REPORT")
        print("=" * 70 + "\n")

    def get_speed_stats(self) -> Optional[dict]:
        """Calculate CPU execution speed statistics.

        Returns:
            Dictionary with speed stats, or None if timing data not available:
            - elapsed_seconds: Wall-clock time elapsed
            - cycles_executed: Total CPU cycles executed
            - cycles_per_second: Actual execution rate (lifetime average)
            - rolling_cycles_per_second: Rolling average over last 10 seconds (if available)
            - real_cpu_freq: Real C64 CPU frequency for this chip
            - speedup: Ratio of actual speed to real hardware speed (lifetime)
            - rolling_speedup: Ratio based on rolling average (if available)
            - chip_name: VIC-II chip name (6569, 6567R8, etc.)
        """
        if self._execution_start_time is None:
            return None

        import time
        end_time = self._execution_end_time or time.perf_counter()
        elapsed = end_time - self._execution_start_time

        if elapsed <= 0:
            return None

        cycles_executed = self.cpu.cycles_executed
        cycles_per_second = cycles_executed / elapsed
        real_cpu_freq = self.video_timing.cpu_freq
        speedup = cycles_per_second / real_cpu_freq

        result = {
            "elapsed_seconds": elapsed,
            "cycles_executed": cycles_executed,
            "cycles_per_second": cycles_per_second,
            "real_cpu_freq": real_cpu_freq,
            "speedup": speedup,
            "chip_name": self.video_timing.chip_name,
        }

        # Add rolling average if we have samples
        if self._speed_samples:
            rolling_cps = sum(self._speed_samples) / len(self._speed_samples)
            result["rolling_cycles_per_second"] = rolling_cps
            result["rolling_speedup"] = rolling_cps / real_cpu_freq

        return result

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

        # Show speed stats if available
        stats = self.get_speed_stats()
        if stats:
            chip = stats['chip_name']
            region = "PAL" if chip == "6569" else "NTSC"
            actual_mhz = stats['cycles_per_second'] / 1e6
            print(f"  Speed: {stats['cycles_per_second']:,.0f} ({actual_mhz:.3f}MHz) cycles/sec "
                  f"({stats['speedup']:.1%} of {region} ({chip}) C64 @ "
                  f"{stats['real_cpu_freq']/1e6:.3f}MHz)")

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

        # Header row offset (4 lines: title, speed, separator, top border)
        header_offset = 4

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
        # Add extra row if drive is attached
        status_row = header_offset + rows + 2

        # Move to status line and update it
        _sys.stdout.write(f"\033[{status_row};1H")
        status = self._format_cpu_status("C64")
        # Clear line and write status
        _sys.stdout.write("\033[K" + status)

        # Add drive status line if drive is attached
        drive_status = self._format_drive_status()
        if drive_status:
            _sys.stdout.write(f"\n\033[K" + drive_status)

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

        # C64 CPU status line
        status = self._format_cpu_status("C64")
        _sys.stdout.write(status + "\n")

        # Drive status line (if drive is attached)
        drive_status = self._format_drive_status()
        if drive_status:
            _sys.stdout.write(drive_status + "\n")

        _sys.stdout.flush()

    def _render_terminal_repl(self) -> None:
        """Render C64 screen to terminal for REPL mode with color support.

        This version uses \r\n for line endings to work correctly in cbreak mode.
        Colors are rendered using ANSI 256-color escape codes.
        """
        import sys as _sys

        # Record speed sample for rolling average (once per second)
        self._record_speed_sample()

        screen_start = 0x0400
        cols = 40
        rows = 25

        # Get background color from VIC register $D021
        bg_color = self.vic.regs[0x21] & 0x0F
        bg_ansi = c64_to_ansi_bg(bg_color)

        # Get border color from VIC register $D020
        border_color = self.vic.regs[0x20] & 0x0F
        border_ansi = c64_to_ansi_bg(border_color)

        # Header row offset (4 lines: title, speed, separator, top border)
        header_offset = 4

        # Check if we need a full redraw
        needs_full = self.dirty_tracker.needs_full_redraw()

        if needs_full:
            # Full screen redraw
            _sys.stdout.write("\033[2J\033[H")  # Clear screen and move to top

            # Terminal header (not part of C64 display)
            title_line = f"C64 REPL (Ctrl+C to exit) - {self.get_video_standard()} ({self.video_chip})"
            stats = self.get_speed_stats()
            if stats:
                # Prefer rolling average if available, otherwise use lifetime average
                cps = stats.get('rolling_cycles_per_second', stats['cycles_per_second'])
                speedup = stats.get('rolling_speedup', stats['speedup'])
                actual_mhz = cps / 1e6
                real_mhz = stats['real_cpu_freq'] / 1e6
                speed_line = f"{actual_mhz:.3f}MHz ({speedup:.1%} of {real_mhz:.3f}MHz)"
            else:
                speed_line = "(calculating speed...)"
            _sys.stdout.write(f"{title_line}\r\n")
            _sys.stdout.write(f"{speed_line}\r\n")
            _sys.stdout.write("=" * 44 + "\r\n")

            # C64 screen with border (top border)
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

        # Move to status line and update it
        _sys.stdout.write(f"\033[{status_row};1H")
        status = self._format_cpu_status("C64")
        # Clear line and write status
        _sys.stdout.write("\033[K" + status)

        # Add drive status line if drive is attached
        drive_status = self._format_drive_status()
        if drive_status:
            _sys.stdout.write(f"\n\033[K" + drive_status)

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
            pygame.K_QUOTE: (7, 3),      # Map to '2' key - SHIFT+2 produces " (double quote) for BASIC strings
            pygame.K_ASTERISK: (6, 1),   # *
            pygame.K_KP_MULTIPLY: (6, 1),  # * on numpad
            pygame.K_SEMICOLON: (6, 2),  # ;
            pygame.K_HOME: (6, 3),       # HOME/CLR
            # pygame.K_CLR: (6, 4),      # CLR (combined with HOME)
            pygame.K_EQUALS: (6, 5),     # =
            pygame.K_UP: (6, 6),         # ↑ (up arrow, mapped to up key)
            pygame.K_SLASH: (6, 7),      # /
            # US keyboard Shift+number symbols mapped to C64 equivalents
            # On US keyboard: Shift+8=*, Shift+9=(, Shift+0=)
            # On C64: Shift+8=(, Shift+9=), * is separate key
            pygame.K_LEFTPAREN: (3, 3),  # ( -> maps to '8' key (C64: Shift+8 = '(')
            pygame.K_RIGHTPAREN: (4, 0), # ) -> maps to '9' key (C64: Shift+9 = ')')

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

        # Keys that should be held directly (not buffered) - modifiers and control keys
        # These affect the state of other keys and need real-time response
        direct_keys = {
            pygame.K_LSHIFT, pygame.K_RSHIFT,  # SHIFT modifiers
            pygame.K_LCTRL, pygame.K_RCTRL,    # CTRL
            pygame.K_ESCAPE,                    # RUN/STOP
        }

        # Keyboard-to-joystick mappings when joystick emulation is enabled
        # Numpad: 8=Up, 2=Down, 4=Left, 6=Right, 0=Fire, 5=Fire (alt)
        # Cursor keys: Up/Down/Left/Right arrows, Right Ctrl=Fire
        joystick_key_map = {
            # Numpad
            pygame.K_KP8: JOYSTICK_UP,
            pygame.K_KP2: JOYSTICK_DOWN,
            pygame.K_KP4: JOYSTICK_LEFT,
            pygame.K_KP6: JOYSTICK_RIGHT,
            pygame.K_KP0: JOYSTICK_FIRE,
            pygame.K_KP5: JOYSTICK_FIRE,      # Alt fire on numpad center
            # Cursor keys (when joystick enabled, these become joystick instead of C64 cursor)
            pygame.K_UP: JOYSTICK_UP,
            pygame.K_DOWN: JOYSTICK_DOWN,
            pygame.K_LEFT: JOYSTICK_LEFT,
            pygame.K_RIGHT: JOYSTICK_RIGHT,
            pygame.K_RCTRL: JOYSTICK_FIRE,    # Right Ctrl = Fire
            pygame.K_KP_ENTER: JOYSTICK_FIRE, # Numpad Enter = Fire
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

            # Handle Ctrl+V for paste from system clipboard
            ctrl_held = bool(event.mod & (pygame.KMOD_LCTRL | pygame.KMOD_RCTRL))
            if ctrl_held and event.key == pygame.K_v:
                try:
                    clipboard_text = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if clipboard_text:
                        # Decode bytes to string if needed
                        if isinstance(clipboard_text, bytes):
                            clipboard_text = clipboard_text.decode('utf-8', errors='ignore')
                        # Remove null terminator if present
                        clipboard_text = clipboard_text.rstrip('\x00')
                        if clipboard_text:
                            self._paste_text(clipboard_text)
                            log.info(f"Pasted {len(clipboard_text)} characters from clipboard")
                except Exception as e:
                    log.warning(f"Paste failed: {e}")
                return

            # Handle joystick keys first (if joystick enabled)
            if self._joystick_enabled and event.key in joystick_key_map:
                direction = joystick_key_map[event.key]
                self.set_joystick_direction(direction, True)
                if DEBUG_KEYBOARD:
                    log.info(f"*** JOYSTICK KEYDOWN: key={key_name}, direction=0x{direction:02X} ***")
                return  # Don't process as keyboard key

            # US keyboard to C64 symbol remapping when SHIFT is held
            # US keyboard: Shift+8=*, Shift+9=(, Shift+0=)
            # C64 keyboard: Shift+8=(, Shift+9=), * is separate key
            # Remap these to produce expected characters on C64
            shift_held = bool(event.mod & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT))
            remapped_key = event.key
            remap_needs_shift = False
            remap_suppress_shift = False
            if shift_held:
                if event.key == pygame.K_8:
                    # US Shift+8 = * → C64 * key (must suppress shift!)
                    remapped_key = pygame.K_ASTERISK
                    remap_needs_shift = False
                    remap_suppress_shift = True  # User is holding shift, but we want unshifted *
                elif event.key == pygame.K_9:
                    # US Shift+9 = ( → C64 Shift+8
                    remapped_key = pygame.K_8
                    remap_needs_shift = True
                elif event.key == pygame.K_0:
                    # US Shift+0 = ) → C64 Shift+9
                    remapped_key = pygame.K_9
                    remap_needs_shift = True

            if remapped_key in key_map:
                row, col = key_map[remapped_key]

                # Track physical key state
                self._pygame_keys_currently_pressed.add(event.key)

                # Direct keys (modifiers) are pressed immediately for real-time feel
                if event.key in direct_keys:
                    self.cia1.press_key(row, col)
                else:
                    # Buffer the key for injection with proper timing
                    # Some keys need SHIFT to produce the expected character on C64:
                    # - Quote/double-quote: SHIFT+2 on C64
                    # - Parentheses: SHIFT+8 for '(', SHIFT+9 for ')' on C64
                    # - Remapped shifted number keys (set above)
                    needs_shift = (remap_needs_shift or
                                   event.key == pygame.K_QUOTE or
                                   event.key == pygame.K_QUOTEDBL or
                                   event.key == pygame.K_LEFTPAREN or
                                   event.key == pygame.K_RIGHTPAREN)
                    self._buffer_pygame_key(row, col, needs_shift, remap_suppress_shift)

                if DEBUG_KEYBOARD:
                    petscii_key = self.cia1._get_key_name(row, col)
                    buffered = "BUFFERED" if event.key not in direct_keys else "DIRECT"
                    log.info(f"*** KEYDOWN [{buffered}]: pygame='{key_name}' (code={event.key}), ASCII='{ascii_char}' (0x{ascii_code:02X}), matrix=({row},{col}), PETSCII={petscii_key}, buffer_len={len(self._pygame_key_buffer)} ***")
            else:
                if DEBUG_KEYBOARD:
                    log.info(f"*** UNMAPPED KEYDOWN: pygame='{key_name}' (code={event.key}), ASCII='{ascii_char}' ***")

        elif event.type == pygame.KEYUP:
            # Handle joystick keys first (if joystick enabled)
            if self._joystick_enabled and event.key in joystick_key_map:
                direction = joystick_key_map[event.key]
                self.set_joystick_direction(direction, False)
                if DEBUG_KEYBOARD:
                    key_name = pygame.key.name(event.key) if hasattr(pygame.key, 'name') else str(event.key)
                    log.info(f"*** JOYSTICK KEYUP: key={key_name}, direction=0x{direction:02X} ***")
                return  # Don't process as keyboard key

            if event.key in key_map:
                row, col = key_map[event.key]

                # Track physical key state
                self._pygame_keys_currently_pressed.discard(event.key)

                # Direct keys are released immediately
                if event.key in direct_keys:
                    self.cia1.release_key(row, col)

                # Buffered keys don't need explicit release - buffer handles timing

                if DEBUG_KEYBOARD:
                    log.info(f"*** KEYUP: pygame key {event.key}, row={row}, col={col} ***")

    def _render_pygame(self) -> None:
        """Render C64 screen to pygame window with dirty region optimization."""
        if not self.pygame_available or self.pygame_screen is None:
            return

        try:
            import pygame

            # Check if we've entered BASIC ROM (for conditional logging)
            self._check_pc_region()

            # Handle pygame events (window close, keyboard, mouse, etc.)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise errors.QuitRequestError("Window closed")
                elif event.type == pygame.KEYDOWN:
                    if DEBUG_KEYBOARD:
                        log.info(f"*** PYGAME KEYDOWN EVENT: key={event.key} ***")
                    self._handle_pygame_keyboard(event, pygame)
                elif event.type == pygame.KEYUP:
                    self._handle_pygame_keyboard(event, pygame)
                elif event.type == pygame.MOUSEMOTION:
                    # Update mouse/paddle/lightpen position
                    if self._mouse_enabled:
                        # Mouse mode: relative motion (like 1351 proportional mouse)
                        self.update_mouse_motion(event.rel[0], event.rel[1])
                    elif self._paddle_enabled:
                        # Paddle mode: absolute position scaled to window
                        # Mouse X → Paddle 1 (POTX), Mouse Y → Paddle 2 (POTY)
                        window_size = self.pygame_screen.get_size()
                        self.update_paddle_position(event.pos[0], event.pos[1], window_size[0], window_size[1])
                    elif self._lightpen_enabled:
                        # Lightpen mode: absolute position to VIC registers
                        window_size = self.pygame_screen.get_size()
                        self.update_lightpen_position(event.pos[0], event.pos[1], window_size[0], window_size[1])
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Mouse/paddle/lightpen button pressed
                    if self._mouse_enabled:
                        self.set_mouse_button(event.button, True)
                    elif self._paddle_enabled:
                        # Left click → Paddle 1 fire, Right click → Paddle 2 fire
                        self.set_paddle_button(event.button, True)
                    elif self._lightpen_enabled:
                        self.set_lightpen_button(event.button, True)
                elif event.type == pygame.MOUSEBUTTONUP:
                    # Mouse/paddle/lightpen button released
                    if self._mouse_enabled:
                        self.set_mouse_button(event.button, False)
                    elif self._paddle_enabled:
                        self.set_paddle_button(event.button, False)
                    elif self._lightpen_enabled:
                        self.set_lightpen_button(event.button, False)

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

            # Initialize glyph cache if needed
            if not hasattr(self, '_glyph_cache'):
                self._glyph_cache = {}

            vic = self.vic
            ram_snapshot = vic.ram_snapshot
            ram_snapshot_bank = vic.ram_snapshot_bank
            color_snapshot = vic.color_snapshot

            def read_ram(addr):
                if ram_snapshot is not None:
                    rel = addr - ram_snapshot_bank
                    if 0 <= rel < len(ram_snapshot):
                        return ram_snapshot[rel]
                return int(self.cpu.ram[addr])

            def read_color(idx):
                if color_snapshot is not None:
                    return color_snapshot[idx] & 0x0F
                return self.memory.ram_color[idx] & 0x0F

            surface = self.pygame_surface

            # --- Display-side rendering ---
            border_color = vic.regs[0x20] & 0x0F
            surface.fill(COLORS[border_color])

            vic_bank = vic.get_vic_bank()
            mem_control = vic.regs[0x18]
            screen_base = vic_bank + ((mem_control & 0xF0) >> 4) * 0x0400
            char_bank_offset = ((mem_control & 0x0E) >> 1) * 0x0800

            ecm = bool(vic.regs[0x11] & 0x40)
            bmm = bool(vic.regs[0x11] & 0x20)
            den = bool(vic.regs[0x11] & 0x10)
            mcm = bool(vic.regs[0x16] & 0x10)
            bg_color = vic.regs[0x21] & 0x0F

            hscroll = vic.regs[0x16] & 0x07
            vscroll = vic.regs[0x11] & 0x07
            x_origin = vic.border_left - hscroll
            y_origin = vic.border_top - vscroll

            if den and not bmm and not ecm and not mcm:
                # Standard text mode - cached glyph rendering
                char_rom = vic.char_rom
                for row in range(25):
                    for col in range(40):
                        cell_addr = screen_base + row * 40 + col
                        char_code = read_ram(cell_addr)
                        color = read_color(row * 40 + col)

                        reverse = bool(char_code & 0x80)
                        char_code &= 0x7F

                        glyph_addr = (char_code * 8) + char_bank_offset
                        glyph_addr &= 0x0FFF
                        glyph = char_rom[glyph_addr : glyph_addr + 8]

                        if reverse:
                            fg, bg = bg_color, color
                        else:
                            fg, bg = color, bg_color

                        cache_key = (tuple(glyph), fg, bg)
                        if cache_key not in self._glyph_cache:
                            glyph_surf = pygame.Surface((8, 8))
                            fg_rgb = COLORS[fg]
                            bg_rgb = COLORS[bg]
                            for y in range(8):
                                line = glyph[y]
                                for x in range(8):
                                    bit = (line >> (7 - x)) & 0x01
                                    glyph_surf.set_at((x, y), fg_rgb if bit else bg_rgb)
                            self._glyph_cache[cache_key] = glyph_surf

                        base_x = x_origin + col * 8
                        base_y = y_origin + row * 8
                        surface.blit(self._glyph_cache[cache_key], (base_x, base_y))
            elif den:
                # Other modes - fall back to VIC for now
                ram_wrapper = RAMWrapper(ram_snapshot, ram_snapshot_bank, self.cpu.ram)
                color_wrapper = ColorRAMWrapper(color_snapshot, self.memory.ram_color)
                vic.render_frame(surface, ram_wrapper, color_wrapper)

            # Scale and blit to screen
            scaled_surface = pygame.transform.scale(
                surface,
                (vic.total_width * self.scale, vic.total_height * self.scale)
            )
            self.pygame_screen.blit(scaled_surface, (0, 0))
            pygame.display.flip()

            # Update window title with speed stats (rate-limited to once per second)
            self._update_pygame_title(pygame)

            # Also render terminal repl output (screen with colors)
            # Force full redraw since pygame already handled the dirty tracking
            # DO NOT REMOVE - useful for debugging pygame mode via terminal
            self.dirty_tracker.force_redraw()
            self._render_terminal_repl()

        except Exception as e:
            log.error(f"Error rendering pygame display: {e}")

    def _render_pygame_only(self) -> None:
        """Render C64 screen to pygame window.

        All pygame rendering happens here in the display loop, not in the VIC core.
        Uses glyph caching for fast text mode rendering.
        """
        if not self.pygame_available or self.pygame_screen is None:
            return

        try:
            import pygame
            import time as _time

            render_start = _time.perf_counter()

            # Check if VIC has a new frame ready (VBlank)
            new_frame = self.vic.frame_complete.is_set()
            if new_frame:
                self.vic.frame_complete.clear()
                self._frame_count = getattr(self, '_frame_count', 0) + 1

            # Initialize glyph cache if needed
            if not hasattr(self, '_glyph_cache'):
                self._glyph_cache = {}

            # Get RAM snapshot or live RAM
            vic = self.vic
            ram_snapshot = vic.ram_snapshot
            ram_snapshot_bank = vic.ram_snapshot_bank
            color_snapshot = vic.color_snapshot

            # Helper to read RAM
            def read_ram(addr):
                if ram_snapshot is not None:
                    rel = addr - ram_snapshot_bank
                    if 0 <= rel < len(ram_snapshot):
                        return ram_snapshot[rel]
                return int(self.cpu.ram[addr])

            def read_color(idx):
                if color_snapshot is not None:
                    return color_snapshot[idx] & 0x0F
                return self.memory.ram_color[idx] & 0x0F

            surface = self.pygame_surface

            # --- Render frame (display-side, no VIC pygame code) ---

            # Border colour
            border_color = vic.regs[0x20] & 0x0F
            surface.fill(COLORS[border_color])

            # Get VIC bank from CIA2
            vic_bank = vic.get_vic_bank()

            # Decode $D018
            mem_control = vic.regs[0x18]
            screen_base = vic_bank + ((mem_control & 0xF0) >> 4) * 0x0400
            char_bank_offset = ((mem_control & 0x0E) >> 1) * 0x0800

            # Mode flags
            ecm = bool(vic.regs[0x11] & 0x40)
            bmm = bool(vic.regs[0x11] & 0x20)
            den = bool(vic.regs[0x11] & 0x10)
            mcm = bool(vic.regs[0x16] & 0x10)

            bg_color = vic.regs[0x21] & 0x0F

            hscroll = vic.regs[0x16] & 0x07
            vscroll = vic.regs[0x11] & 0x07
            x_origin = vic.border_left - hscroll
            y_origin = vic.border_top - vscroll

            if den and not bmm and not ecm and not mcm:
                # Standard text mode - use cached glyph rendering
                char_rom = vic.char_rom

                for row in range(25):
                    for col in range(40):
                        cell_addr = screen_base + row * 40 + col
                        char_code = read_ram(cell_addr)

                        color = read_color(row * 40 + col)

                        reverse = bool(char_code & 0x80)
                        char_code &= 0x7F

                        glyph_addr = (char_code * 8) + char_bank_offset
                        glyph_addr &= 0x0FFF
                        glyph = char_rom[glyph_addr : glyph_addr + 8]

                        if reverse:
                            fg, bg = bg_color, color
                        else:
                            fg, bg = color, bg_color

                        # Cache lookup
                        cache_key = (tuple(glyph), fg, bg)
                        if cache_key not in self._glyph_cache:
                            # Render glyph to cache
                            glyph_surf = pygame.Surface((8, 8))
                            fg_rgb = COLORS[fg]
                            bg_rgb = COLORS[bg]
                            for y in range(8):
                                line = glyph[y]
                                for x in range(8):
                                    bit = (line >> (7 - x)) & 0x01
                                    glyph_surf.set_at((x, y), fg_rgb if bit else bg_rgb)
                            self._glyph_cache[cache_key] = glyph_surf

                        # Blit cached glyph
                        base_x = x_origin + col * 8
                        base_y = y_origin + row * 8
                        surface.blit(self._glyph_cache[cache_key], (base_x, base_y))

            elif den:
                # Other modes - fall back to VIC renderer for now
                # TODO: Move bitmap/multicolor/ECM rendering here too
                class RAMWrapper:
                    def __getitem__(wrapper_self, index):
                        return read_ram(index)

                class ColorWrapper:
                    def __getitem__(wrapper_self, index):
                        return read_color(index)

                vic.render_frame(surface, RAMWrapper(), ColorWrapper())

            # Scale and blit to screen
            scaled_surface = pygame.transform.scale(
                surface,
                (vic.total_width * self.scale, vic.total_height * self.scale)
            )
            self.pygame_screen.blit(scaled_surface, (0, 0))
            pygame.display.flip()

            # Log render time periodically
            render_time = _time.perf_counter() - render_start
            if self._frame_count <= 5 or self._frame_count % 60 == 0:
                cache_size = len(self._glyph_cache)
                log.critical(
                    f"*** RENDER: {render_time*1000:.1f}ms "
                    f"(frame {self._frame_count}, cache={cache_size}) ***"
                )

        except Exception as e:
            log.error(f"Error rendering pygame display: {e}")

    def _pump_pygame_events(self) -> None:
        """Process pygame events without rendering.

        Called when the frame_complete wait times out to keep the UI
        responsive (handle window close, keyboard input, mouse input, etc.).
        """
        if not self.pygame_available or self.pygame_screen is None:
            return

        try:
            import pygame

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise errors.QuitRequestError("Window closed")
                elif event.type == pygame.KEYDOWN:
                    if DEBUG_KEYBOARD:
                        log.info(f"*** PYGAME KEYDOWN EVENT: key={event.key} ***")
                    self._handle_pygame_keyboard(event, pygame)
                elif event.type == pygame.KEYUP:
                    self._handle_pygame_keyboard(event, pygame)
                elif event.type == pygame.MOUSEMOTION:
                    # Update mouse/paddle/lightpen position
                    if self._mouse_enabled:
                        # Mouse mode: relative motion (like 1351 proportional mouse)
                        self.update_mouse_motion(event.rel[0], event.rel[1])
                    elif self._paddle_enabled:
                        # Paddle mode: absolute position scaled to window
                        # Mouse X → Paddle 1 (POTX), Mouse Y → Paddle 2 (POTY)
                        window_size = self.pygame_screen.get_size()
                        self.update_paddle_position(event.pos[0], event.pos[1], window_size[0], window_size[1])
                    elif self._lightpen_enabled:
                        # Lightpen mode: absolute position to VIC registers
                        window_size = self.pygame_screen.get_size()
                        self.update_lightpen_position(event.pos[0], event.pos[1], window_size[0], window_size[1])
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Mouse/paddle/lightpen button pressed
                    if self._mouse_enabled:
                        self.set_mouse_button(event.button, True)
                    elif self._paddle_enabled:
                        # Left click → Paddle 1 fire, Right click → Paddle 2 fire
                        self.set_paddle_button(event.button, True)
                    elif self._lightpen_enabled:
                        self.set_lightpen_button(event.button, True)
                elif event.type == pygame.MOUSEBUTTONUP:
                    # Mouse/paddle/lightpen button released
                    if self._mouse_enabled:
                        self.set_mouse_button(event.button, False)
                    elif self._paddle_enabled:
                        self.set_paddle_button(event.button, False)
                    elif self._lightpen_enabled:
                        self.set_lightpen_button(event.button, False)

        except errors.QuitRequestError:
            raise  # Re-raise quit request to propagate up
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
        "'": (1, 7, 7, 3),   # SHIFT + 2 - produces " (double quote) for BASIC strings
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

    # -------------------------------------------------------------------------
    # Mouse Input (1351 proportional mouse emulation)
    # -------------------------------------------------------------------------
    # The Commodore 1351 mouse uses:
    # - SID POT registers ($D419/$D41A) for position (relative motion, wraps 0-255)
    # - Joystick port for buttons (active low):
    #   - Left button = Fire (bit 4)
    #   - Right button = Up (bit 0) in some implementations
    # Mouse is typically plugged into Port 1 (joystick_1)

    _mouse_enabled: bool = False
    _mouse_port: int = 1  # Which joystick port (1 or 2)
    _mouse_sensitivity: float = 1.0  # Scale factor for mouse motion

    def enable_mouse(self, enabled: bool = True, port: int = 1, sensitivity: float = 1.0) -> None:
        """Enable or disable mouse input.

        Args:
            enabled: Whether mouse input is enabled
            port: Which joystick port (1 or 2) the mouse is connected to
            sensitivity: Scale factor for mouse motion (1.0 = 1:1 mapping)
        """
        self._mouse_enabled = enabled
        self._mouse_port = port
        self._mouse_sensitivity = sensitivity
        self.sid.mouse_enabled = enabled
        log.info(f"Mouse input {'enabled' if enabled else 'disabled'} on port {port}, sensitivity={sensitivity}")

    def update_mouse_motion(self, delta_x: int, delta_y: int) -> None:
        """Update mouse position from motion delta.

        The 1351 mouse sends relative motion that wraps around 0-255.
        This method should be called with pygame MOUSEMOTION event rel values.

        Args:
            delta_x: Horizontal motion in pixels (positive = right)
            delta_y: Vertical motion in pixels (positive = down)
        """
        if not self._mouse_enabled:
            return

        # Apply sensitivity scaling
        scaled_x = int(delta_x * self._mouse_sensitivity)
        scaled_y = int(delta_y * self._mouse_sensitivity)

        # Update SID POT registers
        self.sid.update_mouse(scaled_x, scaled_y)

    def set_mouse_button(self, button: int, pressed: bool) -> None:
        """Set mouse button state.

        Args:
            button: Button number (1 = left, 3 = right for pygame)
            pressed: True if button is pressed, False if released
        """
        if not self._mouse_enabled:
            return

        # Get the joystick register for the configured port
        if self._mouse_port == 1:
            joystick = self.cia1.joystick_1
        else:
            joystick = self.cia1.joystick_2

        # Mouse buttons use active-low logic (0 = pressed, 1 = released)
        # Left button (1) = Fire (bit 4)
        # Right button (3) = Up (bit 0) - common mapping for 1351
        if button == 1:  # Left button
            if pressed:
                joystick &= ~MOUSE_LEFT_BUTTON  # Clear bit (pressed)
            else:
                joystick |= MOUSE_LEFT_BUTTON   # Set bit (released)
        elif button == 3:  # Right button
            if pressed:
                joystick &= ~MOUSE_RIGHT_BUTTON  # Clear bit (pressed)
            else:
                joystick |= MOUSE_RIGHT_BUTTON   # Set bit (released)

        # Update the joystick state
        if self._mouse_port == 1:
            self.cia1.joystick_1 = joystick
        else:
            self.cia1.joystick_2 = joystick

    # =========================================================================
    # Paddle Input Support
    # =========================================================================
    # Paddles use the same SID POT registers as the 1351 mouse, but with
    # absolute positioning instead of relative motion.
    # - Two paddles per port (directly reading the same POT registers)
    # - Each paddle has a fire button (directly triggers joystick port bits)
    # - Paddle 1: POTX ($D419), fire on bit 2 of joystick port
    # - Paddle 2: POTY ($D41A), fire on bit 3 of joystick port
    # Fire buttons active-low on the joystick port.

    _paddle_enabled: bool = False
    _paddle_port: int = 1  # Which joystick port (1 or 2)

    def enable_paddle(self, enabled: bool = True, port: int = 1) -> None:
        """Enable or disable paddle input.

        Args:
            enabled: Whether paddle input is enabled
            port: Which joystick port (1 or 2) the paddles are connected to
        """
        self._paddle_enabled = enabled
        self._paddle_port = port
        log.info(f"Paddle input {'enabled' if enabled else 'disabled'} on port {port}")

    def update_paddle_position(self, mouse_x: int, mouse_y: int, window_width: int, window_height: int) -> None:
        """Update paddle position from absolute mouse position.

        Args:
            mouse_x: Mouse X position in window (pixels)
            mouse_y: Mouse Y position in window (pixels)
            window_width: Window width (pixels)
            window_height: Window height (pixels)
        """
        if not self._paddle_enabled:
            return

        # Scale mouse position to paddle range (0-255)
        # Clamp to valid range in case mouse is outside window
        paddle_x = max(0, min(255, int((mouse_x / max(1, window_width)) * 255)))
        paddle_y = max(0, min(255, int((mouse_y / max(1, window_height)) * 255)))

        # Update SID POT registers
        self.sid.set_paddle(paddle_x, paddle_y)

    def set_paddle_button(self, button: int, pressed: bool) -> None:
        """Set paddle button state.

        C64 paddle fire buttons use different CIA bits than joystick fire:
        - Paddle 1 (X-axis paddle) fire: Bit 2 of CIA port
        - Paddle 2 (Y-axis paddle) fire: Bit 3 of CIA port

        Port 1 paddles read from $DC01 (CIA1 Port B)
        Port 2 paddles read from $DC00 (CIA1 Port A)

        Reference: https://www.c64-wiki.com/wiki/Paddle

        Args:
            button: Mouse button (1 = left → paddle 1 fire, 3 = right → paddle 2 fire)
            pressed: True if button is pressed, False if released
        """
        if not self._paddle_enabled:
            return

        # Get the joystick register for the configured port
        if self._paddle_port == 1:
            joystick = self.cia1.joystick_1
        else:
            joystick = self.cia1.joystick_2

        # Paddle buttons use active-low logic (0 = pressed, 1 = released)
        # Real C64 paddle fire buttons:
        # - Paddle 1 (X) fire = Bit 2 (directly wired to control port pin 3)
        # - Paddle 2 (Y) fire = Bit 3 (directly wired to control port pin 4)
        if button == 1:  # Left mouse button = Paddle 1 fire
            if pressed:
                joystick &= ~PADDLE_1_FIRE  # Clear bit 2 (pressed)
            else:
                joystick |= PADDLE_1_FIRE   # Set bit 2 (released)
        elif button == 3:  # Right mouse button = Paddle 2 fire
            if pressed:
                joystick &= ~PADDLE_2_FIRE  # Clear bit 3 (pressed)
            else:
                joystick |= PADDLE_2_FIRE   # Set bit 3 (released)

        # Update the joystick state
        if self._paddle_port == 1:
            self.cia1.joystick_1 = joystick
        else:
            self.cia1.joystick_2 = joystick

    # =========================================================================
    # Lightpen Input Support
    # =========================================================================
    # Lightpen uses VIC-II registers for position (not SID POT like mouse/paddle):
    # - $D013 (LPX): X coordinate divided by 2 (multiply by 2 to get actual X)
    # - $D014 (LPY): Y coordinate (same as sprite Y coordinates)
    # - Button triggers joystick fire on port 1 only (bit 4 of $DC01)
    # - Can also trigger VIC IRQ bit 3 when position is latched
    #
    # Lightpen only works on control port 1 (directly wired to VIC).
    # Reference: https://www.c64-wiki.com/wiki/Light_pen

    _lightpen_enabled: bool = False

    def enable_lightpen(self, enabled: bool = True) -> None:
        """Enable or disable lightpen input.

        Note: Lightpen only works on control port 1 (hardware limitation).

        Args:
            enabled: Whether lightpen input is enabled
        """
        self._lightpen_enabled = enabled
        log.info(f"Lightpen input {'enabled' if enabled else 'disabled'}")

    def update_lightpen_position(self, mouse_x: int, mouse_y: int,
                                  window_width: int, window_height: int) -> None:
        """Update lightpen position from mouse position.

        Maps mouse window coordinates to VIC-II lightpen registers.
        The VIC stores X/2 in $D013 and Y in $D014, using sprite coordinate space.

        Args:
            mouse_x: Mouse X position in window (pixels)
            mouse_y: Mouse Y position in window (pixels)
            window_width: Window width (pixels)
            window_height: Window height (pixels)
        """
        if not self._lightpen_enabled:
            return

        # VIC-II visible area in sprite coordinates:
        # PAL: X = 24-343 (320 pixels), Y = 50-249 (200 pixels)
        # We map the window to the visible screen area

        # X coordinate: map window X to sprite X range (24-343), then divide by 2
        # The visible screen is 320 pixels wide, starting at sprite X=24
        sprite_x = 24 + int((mouse_x / max(1, window_width)) * 320)
        sprite_x = max(0, min(511, sprite_x))  # Clamp to 9-bit range
        lpx = sprite_x // 2  # VIC stores X/2

        # Y coordinate: map window Y to sprite Y range (50-249)
        # The visible screen is 200 pixels tall, starting at sprite Y=50
        sprite_y = 50 + int((mouse_y / max(1, window_height)) * 200)
        sprite_y = max(0, min(255, sprite_y))  # Clamp to 8-bit range

        # Update VIC lightpen registers
        self.vic.regs[0x13] = lpx & 0xFF
        self.vic.regs[0x14] = sprite_y & 0xFF

    def set_lightpen_button(self, button: int, pressed: bool) -> None:
        """Set lightpen button state.

        Lightpen button is directly wired to joystick fire on port 1.
        Only left mouse button is used (lightpens have one button).

        Reference: https://www.c64-wiki.com/wiki/Light_pen

        Args:
            button: Mouse button (1 = left/lightpen button)
            pressed: True if button is pressed, False if released
        """
        if not self._lightpen_enabled:
            return

        # Lightpen only uses port 1 (hardware constraint)
        joystick = self.cia1.joystick_1

        # Lightpen button uses active-low logic (0 = pressed, 1 = released)
        # Only left button (1) triggers the lightpen
        if button == 1:
            if pressed:
                joystick &= ~LIGHTPEN_BUTTON  # Clear bit (pressed)
            else:
                joystick |= LIGHTPEN_BUTTON   # Set bit (released)

        self.cia1.joystick_1 = joystick

    # =========================================================================
    # Keyboard Joystick Emulation
    # =========================================================================
    # Maps keyboard keys to joystick directions and fire button.
    # Supports both numpad (8/2/4/6/0) and WASD+Space layouts.
    # Default port is 2 since most C64 games expect joystick in port 2.
    #
    # C64 joystick uses active-low logic (0 = pressed, 1 = released):
    # - Bit 0: Up
    # - Bit 1: Down
    # - Bit 2: Left
    # - Bit 3: Right
    # - Bit 4: Fire
    # Reference: https://www.c64-wiki.com/wiki/Joystick

    _joystick_enabled: bool = False
    _joystick_port: int = 2  # Default to port 2 (most common for C64 games)

    def enable_joystick(self, enabled: bool = True, port: int = 2) -> None:
        """Enable or disable keyboard joystick emulation.

        When enabled, keyboard keys are mapped to joystick directions:
        - Numpad: 8=Up, 2=Down, 4=Left, 6=Right, 0=Fire
        - WASD: W=Up, S=Down, A=Left, D=Right, Space=Fire

        Args:
            enabled: Whether joystick emulation is enabled
            port: Which joystick port to emulate (1 or 2, default: 2)
        """
        self._joystick_enabled = enabled
        self._joystick_port = port
        log.info(f"Keyboard joystick {'enabled' if enabled else 'disabled'} on port {port}")

    def set_joystick_direction(self, direction: int, pressed: bool) -> None:
        """Set a joystick direction or fire button state.

        Args:
            direction: Direction bit (JOYSTICK_UP, JOYSTICK_DOWN, etc.)
            pressed: True if pressed, False if released
        """
        if not self._joystick_enabled:
            return

        if self._joystick_port == 1:
            joystick = self.cia1.joystick_1
        else:
            joystick = self.cia1.joystick_2

        # Active-low logic: 0 = pressed, 1 = released
        if pressed:
            joystick &= ~direction  # Clear bit (pressed)
        else:
            joystick |= direction   # Set bit (released)

        if self._joystick_port == 1:
            self.cia1.joystick_1 = joystick
        else:
            self.cia1.joystick_2 = joystick

    # Pending key releases for non-blocking terminal input
    # Each entry is (release_cycles, row, col) - uses CPU cycles, not wall-clock time
    _pending_key_releases: list = []

    # Pygame keyboard buffer for type-ahead
    # Stores (row, col, needs_shift) tuples for keys waiting to be injected
    _pygame_key_buffer: list = []
    _pygame_keys_currently_pressed: set = set()  # Track physical key state
    _pygame_current_injection: tuple | None = None  # (row, col, needs_shift, start_cycles, released)

    # Timing in CPU cycles (not wall-clock) so keys inject correctly at any emulator speed
    # KERNAL scans keyboard once per frame (~17000-20000 cycles). We need to span one scan.
    # At ~1MHz: 20000 cycles = ~20ms (one full frame), 2000 cycles = ~2ms
    _key_hold_cycles: int = 20000   # Hold key for one full frame, guarantees KERNAL sees it
    _key_gap_cycles: int = 2000     # Gap between keys

    def _queue_key_release(self, row: int, col: int) -> bool:
        """Queue a key for release after a delay (cycle-based, not wall-clock).

        Uses CPU cycles for timing so key handling works correctly at any
        emulator speed (throttled or unthrottled).

        Implements debouncing: if this key already has a pending release,
        the keypress is skipped entirely to prevent key repeat issues.

        Args:
            row: Keyboard matrix row
            col: Keyboard matrix column

        Returns:
            True if key was queued, False if skipped due to debouncing
        """
        # Check if this key already has a pending release (debounce)
        for _, pending_row, pending_col in self._pending_key_releases:
            if pending_row == row and pending_col == col:
                # Key already pending - skip this press (debounce)
                return False

        release_cycles = self.cpu.cycles_executed + self._key_hold_cycles
        self._pending_key_releases.append((release_cycles, row, col))
        return True

    def _process_pending_key_releases(self) -> None:
        """Process any pending key releases (call from main loop).

        Uses CPU cycles for timing, which scales correctly with emulator speed.
        """
        if not self._pending_key_releases:
            return

        current_cycles = self.cpu.cycles_executed
        still_pending = []
        for release_cycles, row, col in self._pending_key_releases:
            if current_cycles >= release_cycles:
                self.cia1.release_key(row, col)
            else:
                still_pending.append((release_cycles, row, col))
        self._pending_key_releases = still_pending

    def _buffer_pygame_key(self, row: int, col: int, needs_shift: bool = False,
                            suppress_shift: bool = False) -> None:
        """Buffer a keypress from pygame for injection into CIA.

        Keys are buffered and injected one at a time with proper timing
        to ensure the KERNAL sees every keypress.

        Args:
            row: C64 keyboard matrix row
            col: C64 keyboard matrix column
            needs_shift: If True, press SHIFT along with this key
            suppress_shift: If True, release SHIFT while pressing this key
                           (for when user is holding shift but we want unshifted char)
        """
        self._pygame_key_buffer.append((row, col, needs_shift, suppress_shift))

    def _paste_text(self, text: str) -> None:
        """Paste text by buffering keystrokes for each character.

        Converts ASCII/Unicode text to C64 key matrix positions and buffers
        them for injection via the pygame key buffer system.

        Args:
            text: Text to paste (ASCII characters)
        """
        # ASCII character to C64 keyboard matrix mapping: (row, col, needs_shift)
        # Based on the C64 keyboard matrix
        ascii_to_matrix = {
            # Letters (unshifted = uppercase on C64)
            'A': (1, 2, False), 'B': (3, 4, False), 'C': (2, 4, False),
            'D': (2, 2, False), 'E': (1, 6, False), 'F': (2, 5, False),
            'G': (3, 2, False), 'H': (3, 5, False), 'I': (4, 1, False),
            'J': (4, 2, False), 'K': (4, 5, False), 'L': (5, 2, False),
            'M': (4, 4, False), 'N': (4, 7, False), 'O': (4, 6, False),
            'P': (5, 1, False), 'Q': (7, 6, False), 'R': (2, 1, False),
            'S': (1, 5, False), 'T': (2, 6, False), 'U': (3, 6, False),
            'V': (3, 7, False), 'W': (1, 1, False), 'X': (2, 7, False),
            'Y': (3, 1, False), 'Z': (1, 4, False),
            # Lowercase -> same as uppercase (C64 types uppercase by default)
            'a': (1, 2, False), 'b': (3, 4, False), 'c': (2, 4, False),
            'd': (2, 2, False), 'e': (1, 6, False), 'f': (2, 5, False),
            'g': (3, 2, False), 'h': (3, 5, False), 'i': (4, 1, False),
            'j': (4, 2, False), 'k': (4, 5, False), 'l': (5, 2, False),
            'm': (4, 4, False), 'n': (4, 7, False), 'o': (4, 6, False),
            'p': (5, 1, False), 'q': (7, 6, False), 'r': (2, 1, False),
            's': (1, 5, False), 't': (2, 6, False), 'u': (3, 6, False),
            'v': (3, 7, False), 'w': (1, 1, False), 'x': (2, 7, False),
            'y': (3, 1, False), 'z': (1, 4, False),
            # Numbers
            '1': (7, 0, False), '2': (7, 3, False), '3': (1, 0, False),
            '4': (1, 3, False), '5': (2, 0, False), '6': (2, 3, False),
            '7': (3, 0, False), '8': (3, 3, False), '9': (4, 0, False),
            '0': (4, 3, False),
            # Symbols (unshifted)
            ' ': (7, 4, False),   # SPACE
            '\r': (0, 1, False),  # RETURN
            '\n': (0, 1, False),  # RETURN (newline)
            ',': (5, 7, False),   # COMMA
            '.': (5, 4, False),   # PERIOD
            ':': (5, 5, False),   # COLON
            ';': (6, 2, False),   # SEMICOLON
            '/': (6, 7, False),   # SLASH
            '=': (6, 5, False),   # EQUALS
            '+': (5, 0, False),   # PLUS
            '-': (5, 3, False),   # MINUS
            '*': (6, 1, False),   # ASTERISK
            '@': (5, 6, False),   # AT
            # Shifted symbols
            '!': (7, 0, True),    # SHIFT+1
            '"': (7, 3, True),    # SHIFT+2 (quote)
            '#': (1, 0, True),    # SHIFT+3
            '$': (1, 3, True),    # SHIFT+4
            '%': (2, 0, True),    # SHIFT+5
            '&': (2, 3, True),    # SHIFT+6
            "'": (3, 0, True),    # SHIFT+7 (apostrophe)
            '(': (3, 3, True),    # SHIFT+8
            ')': (4, 0, True),    # SHIFT+9
            '<': (5, 7, True),    # SHIFT+COMMA
            '>': (5, 4, True),    # SHIFT+PERIOD
            '?': (6, 7, True),    # SHIFT+SLASH
        }

        for char in text:
            if char in ascii_to_matrix:
                row, col, needs_shift = ascii_to_matrix[char]
                self._buffer_pygame_key(row, col, needs_shift, suppress_shift=False)
            else:
                # Skip unmapped characters
                log.debug(f"Paste: skipping unmapped character '{char}' (0x{ord(char):02X})")

    def _process_pygame_key_buffer(self) -> None:
        """Process the pygame key buffer, injecting keys into CIA.

        Called from main loop. Handles timing for key injection using CPU cycles
        so keys inject faster when emulator runs faster than real-time.
        - Press key, hold for ~20000 cycles (~20ms at 1MHz)
        - Release key, wait ~5000 cycles gap
        - Repeat for next key
        """
        current_cycles = self.cpu.cycles_executed

        # If we have a current injection in progress, check timing
        if self._pygame_current_injection is not None:
            row, col, needs_shift, suppress_shift, start_cycles, released = self._pygame_current_injection

            if not released:
                # Key is being held - check if hold cycles elapsed
                if current_cycles - start_cycles >= self._key_hold_cycles:
                    # Release the key
                    self.cia1.release_key(row, col)
                    if needs_shift:
                        self.cia1.release_key(1, 7)  # Release SHIFT
                    if suppress_shift:
                        # Re-press shift if user is still holding it physically
                        import pygame
                        if pygame.K_LSHIFT in self._pygame_keys_currently_pressed or \
                           pygame.K_RSHIFT in self._pygame_keys_currently_pressed:
                            self.cia1.press_key(1, 7)
                    # Mark as released, record release cycle
                    self._pygame_current_injection = (row, col, needs_shift, suppress_shift, current_cycles, True)
            else:
                # Key is released - check if gap cycles elapsed
                if current_cycles - start_cycles >= self._key_gap_cycles:
                    # Done with this key, clear injection
                    self._pygame_current_injection = None

        # If no current injection and buffer has keys, start next one
        if self._pygame_current_injection is None and self._pygame_key_buffer:
            row, col, needs_shift, suppress_shift = self._pygame_key_buffer.pop(0)
            # Press the key
            if needs_shift:
                self.cia1.press_key(1, 7)  # Press SHIFT
            if suppress_shift:
                self.cia1.release_key(1, 7)  # Release SHIFT even if physically held
            self.cia1.press_key(row, col)
            # Record injection start (not released yet)
            self._pygame_current_injection = (row, col, needs_shift, suppress_shift, current_cycles, False)

    def _handle_terminal_input(self, char: str) -> bool:
        """Handle a single character of terminal input.

        Converts ASCII input to C64 key presses. Handles escape sequences
        for arrow keys and other special keys. Uses non-blocking key release
        queue to avoid stalling the main loop.

        Arguments:
            char: Single character from terminal input

        Returns:
            True if Ctrl+C was pressed (should exit), False otherwise
        """
        import sys as _sys

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
                        self._queue_key_release(0, 7)
                        self._queue_key_release(1, 7)
                    elif seq == '[B':  # Down arrow -> CRSR DOWN
                        self.cia1.press_key(0, 7)
                        self._queue_key_release(0, 7)
                    elif seq == '[C':  # Right arrow -> CRSR RIGHT
                        self.cia1.press_key(0, 2)
                        self._queue_key_release(0, 2)
                    elif seq == '[D':  # Left arrow -> CRSR LEFT (SHIFT + CRSR RIGHT)
                        self.cia1.press_key(1, 7)  # SHIFT
                        self.cia1.press_key(0, 2)  # CRSR RIGHT
                        self._queue_key_release(0, 2)
                        self._queue_key_release(1, 7)
                    elif seq == '[3':  # Delete key (followed by ~)
                        if select.select([_sys.stdin], [], [], 0.1)[0]:
                            _sys.stdin.read(1)  # Consume the ~
                        self.cia1.press_key(0, 0)  # DEL
                        self._queue_key_release(0, 0)
            except ImportError:
                pass  # select not available
        elif char == '\x7f':  # Backspace
            # Check if key is already pending (debounce)
            already_pending = any(r == 0 and c == 0 for _, r, c in self._pending_key_releases)
            if not already_pending:
                self.cia1.press_key(0, 0)  # DEL
                self._queue_key_release(0, 0)
        else:
            # Regular character - press key and queue release
            key_info = self.ascii_to_key_press(char)
            if key_info:
                needs_shift, row, col = key_info
                # Check if key is already pending (debounce)
                already_pending = any(r == row and c == col for _, r, c in self._pending_key_releases)
                if not already_pending:
                    if needs_shift:
                        self.cia1.press_key(1, 7)  # SHIFT
                    self.cia1.press_key(row, col)
                    self._queue_key_release(row, col)
                    if needs_shift:
                        self._queue_key_release(1, 7)

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

            # Record execution start time for speedup calculation
            self._execution_start_time = time.perf_counter()

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

                # Process any pending key releases
                self._process_pending_key_releases()

                # Render at limited rate to avoid terminal buffer overflow
                now = time.time()
                if now - last_render >= render_interval:
                    self.dirty_tracker.force_redraw()
                    self._render_terminal_repl()
                    last_render = now

        except (KeyboardInterrupt, errors.QuitRequestError):
            pass
        finally:
            # Record execution end time for speedup calculation
            self._execution_end_time = time.perf_counter()

            stop_event.set()
            # Wait for CPU thread to finish
            cpu_thread_obj.join(timeout=0.5)

            # Restore terminal settings
            termios.tcsetattr(_sys.stdin, termios.TCSADRAIN, old_settings)

            # Clear screen and show final state
            _sys.stdout.write("\033[2J\033[H")
            _sys.stdout.flush()
            self.show_screen()

            # Clean up drive subprocess if running
            self.cleanup()

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

        # Attach disk drive only if --disk is specified (and not disabled)
        # This avoids the overhead of drive emulation when not needed
        disk_path = getattr(args, 'disk', None)
        if disk_path and not getattr(args, 'no_drive', False):
            drive_rom = getattr(args, 'drive_rom', None)
            drive_runner = getattr(args, 'drive_runner', 'threaded')
            if c64.attach_drive(drive_rom_path=drive_rom, disk_path=disk_path, runner=drive_runner):
                log.info(f"Disk inserted: {disk_path.name} (runner: {drive_runner})")
            else:
                log.info("No 1541 ROM found - disk drive disabled")

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

        # Enable mouse if requested (only works with pygame)
        if getattr(args, 'mouse', False):
            if c64.display_mode == "pygame":
                c64.enable_mouse(
                    enabled=True,
                    port=getattr(args, 'mouse_port', 1),
                    sensitivity=getattr(args, 'mouse_sensitivity', 1.0)
                )
            else:
                log.warning("Mouse input only available in pygame mode")

        # Enable paddle if requested (only works with pygame, mutually exclusive with mouse)
        if getattr(args, 'paddle', False):
            if getattr(args, 'mouse', False):
                log.warning("Cannot enable both mouse and paddle - paddle takes precedence")
                c64._mouse_enabled = False
            if c64.display_mode == "pygame":
                c64.enable_paddle(
                    enabled=True,
                    port=getattr(args, 'paddle_port', 1)
                )
            else:
                log.warning("Paddle input only available in pygame mode")

        # Enable lightpen if requested (only works with pygame, mutually exclusive with mouse/paddle)
        if getattr(args, 'lightpen', False):
            if getattr(args, 'mouse', False) or getattr(args, 'paddle', False):
                log.warning("Cannot enable lightpen with mouse or paddle - lightpen takes precedence")
                c64._mouse_enabled = False
                c64._paddle_enabled = False
            if c64.display_mode == "pygame":
                c64.enable_lightpen(enabled=True)
            else:
                log.warning("Lightpen input only available in pygame mode")

        # Enable keyboard joystick emulation if requested
        if getattr(args, 'joystick', False):
            c64.enable_joystick(
                enabled=True,
                port=getattr(args, 'joystick_port', 2)
            )

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
            c64.run(max_cycles=args.max_cycles, stop_on_kernal_input=True, throttle=args.throttle, stop_on_illegal_instruction=args.stop_on_illegal_instruction)
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
                c64.run(max_cycles=args.max_cycles, throttle=args.throttle, stop_on_illegal_instruction=args.stop_on_illegal_instruction)
        elif args.display == "repl":
            # REPL mode: interactive terminal with keyboard input
            c64.run_repl(max_cycles=args.max_cycles)
        else:
            c64.run(max_cycles=args.max_cycles, stop_on_basic=args.stop_on_basic, throttle=args.throttle, stop_on_illegal_instruction=args.stop_on_illegal_instruction)

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
