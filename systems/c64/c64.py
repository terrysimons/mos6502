"""Commodore 64 Emulator - Core class."""

from mos6502.compat import logging
import sys
from mos6502.compat import Path
from mos6502.compat import Optional, Union, List, Dict, Tuple

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

# Import mixins
from c64.mixins import (
    C64DriveMixin,
    C64CartridgeMixin,
    C64DisplayMixin,
    C64KeyboardMixin,
    C64InputDevicesMixin,
    C64DebugMixin,
    C64ProgramMixin,
    C64RunnerMixin,
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


class C64(
    C64DriveMixin,
    C64CartridgeMixin,
    C64DisplayMixin,
    C64KeyboardMixin,
    C64InputDevicesMixin,
    C64DebugMixin,
    C64ProgramMixin,
    C64RunnerMixin,
):
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
            choices=["synchronous", "threaded", "multiprocess"],
            default="synchronous",
            dest="drive_runner",
            help="Drive emulation runner: synchronous (default), threaded, or multiprocess",
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

    def get_video_standard(self) -> str:
        """Get the video standard (PAL or NTSC) based on the current video chip.

        Returns:
            "PAL" for chip 6569, "NTSC" for chips 6567R8 or 6567R56A
        """
        if self.video_chip == "6569":
            return "PAL"
        else:  # 6567R8 or 6567R56A
            return "NTSC"

    def _write_rom_to_memory(self, start_addr: int, rom_data: bytes) -> None:
        """Write ROM data to CPU memory.

        Arguments:
            start_addr: Starting address in CPU memory
            rom_data: ROM data to write
        """
        for offset, byte_value in enumerate(rom_data):
            self.cpu.ram[start_addr + offset] = byte_value

        log.debug(f"Wrote ROM to ${start_addr:04X}-${start_addr + len(rom_data) - 1:04X}")

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
