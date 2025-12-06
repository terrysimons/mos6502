"""Base cartridge classes, enums, and utilities.

This module provides the foundation for cartridge emulation including:
- CartridgeType enum for hardware type identification
- MapperRequirements dataclass for mapper specifications
- Cartridge abstract base class
- Memory region constants
- Error cartridge ROM generation utilities
"""

from __future__ import annotations

import logging
import re
import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Protocol

log = logging.getLogger("c64.cartridge")


# Memory region constants
ROML_START = 0x8000
ROML_END = 0x9FFF
ROML_SIZE = 0x2000  # 8KB

ROMH_START = 0xA000
ROMH_END = 0xBFFF
ROMH_SIZE = 0x2000  # 8KB

# Ultimax mode: ROMH appears at $E000-$FFFF instead of $A000-$BFFF
ULTIMAX_ROMH_START = 0xE000
ULTIMAX_ROMH_END = 0xFFFF
ULTIMAX_ROMH_SIZE = 0x2000  # 8KB

IO1_START = 0xDE00
IO1_END = 0xDEFF

IO2_START = 0xDF00
IO2_END = 0xDFFF


class CartridgeType(IntEnum):
    """CRT hardware type IDs from the VICE emulator specification.

    These are the standard cartridge type IDs used in CRT files.
    The list comes from: http://rr.c64.org/wiki/CRT_ID
    """
    # Type 0-9
    NORMAL = 0                  # Generic/normal cartridge (8K/16K/Ultimax)
    ACTION_REPLAY = 1           # Action Replay freezer cartridge
    KCS_POWER = 2               # KCS Power Cartridge
    FINAL_CARTRIDGE_III = 3     # Final Cartridge III freezer
    SIMONS_BASIC = 4            # Simons' BASIC extension
    OCEAN_TYPE_1 = 5            # Ocean Type 1 bank switching
    EXPERT = 6                  # Expert Cartridge
    FUN_PLAY = 7                # Fun Play / Power Play
    SUPER_GAMES = 8             # Super Games
    ATOMIC_POWER = 9            # Atomic Power

    # Type 10-19
    EPYX_FASTLOAD = 10          # Epyx FastLoad disk speedup
    WESTERMANN = 11             # Westermann Learning
    REX_UTILITY = 12            # Rex Utility
    FINAL_CARTRIDGE_I = 13      # Final Cartridge I
    MAGIC_FORMEL = 14           # Magic Formel
    C64_GAME_SYSTEM = 15        # C64 Game System / System 3
    WARPSPEED = 16              # WarpSpeed
    DINAMIC = 17                # Dinamic bank switching
    ZAXXON = 18                 # Zaxxon / Super Zaxxon
    MAGIC_DESK = 19             # Magic Desk / Domark / HES Australia

    # Type 20-29
    SUPER_SNAPSHOT_5 = 20       # Super Snapshot 5
    COMAL_80 = 21               # COMAL 80
    STRUCTURED_BASIC = 22       # Structured Basic
    ROSS = 23                   # Ross
    DELA_EP64 = 24              # Dela EP64
    DELA_EP7X8 = 25             # Dela EP7x8
    DELA_EP256 = 26             # Dela EP256
    REX_EP256 = 27              # Rex EP256
    MIKRO_ASSEMBLER = 28        # Mikro Assembler
    FINAL_CARTRIDGE_PLUS = 29   # Final Cartridge Plus

    # Type 30-39
    ACTION_REPLAY_4 = 30        # Action Replay 4
    STARDOS = 31                # Stardos
    EASYFLASH = 32              # EasyFlash
    EASYFLASH_XBANK = 33        # EasyFlash Xbank
    CAPTURE = 34                # Capture
    ACTION_REPLAY_3 = 35        # Action Replay 3
    RETRO_REPLAY = 36           # Retro Replay
    MMC64 = 37                  # MMC64
    MMC_REPLAY = 38             # MMC Replay
    IDE64 = 39                  # IDE64

    # Type 40-49
    SUPER_SNAPSHOT_4 = 40       # Super Snapshot V4
    IEEE488 = 41                # IEEE-488
    GAME_KILLER = 42            # Game Killer
    PROPHET64 = 43              # Prophet64
    EXOS = 44                   # EXOS
    FREEZE_FRAME = 45           # Freeze Frame
    FREEZE_MACHINE = 46         # Freeze Machine
    SNAPSHOT64 = 47             # Snapshot64
    SUPER_EXPLODE_5 = 48        # Super Explode V5
    MAGIC_VOICE = 49            # Magic Voice

    # Type 50-59
    ACTION_REPLAY_2 = 50        # Action Replay 2
    MACH5 = 51                  # MACH 5
    DIASHOW_MAKER = 52          # Diashow-Maker
    PAGEFOX = 53                # Pagefox
    KINGSOFT = 54               # Kingsoft Business Basic
    SILVERROCK_128 = 55         # Silverrock 128K
    FORMEL64 = 56               # Formel 64
    RGCD = 57                   # RGCD
    RRNET_MK3 = 58              # RR-Net MK3
    EASY_CALC = 59              # Easy Calc Result

    # Type 60-69
    GMOD2 = 60                  # GMod2
    MAX_BASIC = 61              # MAX Basic
    GMOD3 = 62                  # GMod3
    ZIPP_CODE_48 = 63           # ZIPP-CODE 48
    BLACKBOX_V8 = 64            # Blackbox V8
    BLACKBOX_V3 = 65            # Blackbox V3
    BLACKBOX_V4 = 66            # Blackbox V4
    REX_RAM_FLOPPY = 67         # REX RAM-Floppy
    BIS_PLUS = 68               # BIS-Plus
    SD_BOX = 69                 # SD-BOX

    # Type 70-79
    MULTIMAX = 70               # MultiMAX
    BLACKBOX_V9 = 71            # Blackbox V9
    LT_KERNAL = 72              # Lt. Kernal Host Adaptor
    RAMLINK = 73                # RAMLink
    DREAN = 74                  # Drean (H.E.R.O. bootleg)
    IEEE_FLASH_64 = 75          # IEEE Flash! 64
    TURTLE_GRAPHICS_II = 76     # Turtle Graphics II
    FREEZE_FRAME_MK2 = 77       # Freeze Frame MK2
    PARTNER64 = 78              # Partner 64
    HYPER_BASIC = 79            # Hyper-BASIC

    # Type 80-85
    UNIVERSAL_1 = 80            # Universal Cartridge 1
    UNIVERSAL_15 = 81           # Universal Cartridge 1.5
    UNIVERSAL_2 = 82            # Universal Cartridge 2
    TURBO_2000 = 83             # BMP Data Turbo 2000
    PROFI_DOS = 84              # Profi-DOS
    MAGIC_DESK_16 = 85          # Magic Desk 16

    # Special internal type (not a real CRT type)
    ERROR = -1                  # Error cartridge (internal use only)


@dataclass
class MapperRequirements:
    """Requirements for a specific mapper type.

    Defines which memory regions and registers a mapper type needs.
    Each mapper has different hardware requirements - some use IO1/IO2,
    some have multiple ROM banks, etc.
    """
    # ROM regions this mapper uses
    uses_roml: bool = False              # Uses ROML ($8000-$9FFF)
    uses_romh: bool = False              # Uses ROMH ($A000-$BFFF)
    uses_ultimax_romh: bool = False      # Uses Ultimax ROMH ($E000-$FFFF)

    # Bank configuration
    num_banks: int = 1                   # Number of ROM banks
    bank_size: int = 0x2000              # Size of each bank (default 8KB)

    # I/O regions
    uses_io1: bool = False               # Uses IO1 ($DE00-$DEFF)
    uses_io2: bool = False               # Uses IO2 ($DF00-$DFFF)

    # Specific control registers (list of (address, name) tuples)
    control_registers: list = None       # e.g., [("$DE00", "Bank Select")]

    # RAM
    has_ram: bool = False                # Has built-in RAM
    ram_size: int = 0                    # Size of RAM

    def __post_init__(self):
        if self.control_registers is None:
            self.control_registers = []


@dataclass
class MapperTest:
    """A single test for mapper verification.

    Used by both test cart generation and error cart display.
    """
    name: str           # Display name, e.g., "Bank 0 $0000"
    test_id: str        # Unique ID, e.g., "bank_0"
    passed: bool = False  # Default to fail


class CartridgeInterface(Protocol):
    """Common cartridge metadata interface.

    Structural interface for type checking and test utilities.
    Enables generic comparison functions without coupling to specific classes.
    """
    description: str
    exrom: int
    game: int


@dataclass
class CartridgeVariant:
    """Configuration/specification for a cartridge mode.

    Describes a particular configuration of a cartridge type.
    For example, Type 0 can be 8k, 16k, or ultimax mode.
    Single-variant cartridges use an empty description.
    """
    description: str  # "8k", "16k", "" for single-variant carts
    exrom: int
    game: int
    extra: dict = None  # {"single_chip": True}, {"bank_count": 64}, etc.

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


@dataclass
class CartridgeImage(CartridgeVariant):
    """Serializable cartridge data - the file representation.

    Inherits variant configuration and adds ROM data and serialization.
    This is the result of calling create_test_cartridge().
    """
    rom_data: dict = None  # {"roml": bytes, "romh": bytes} or {"banks": list[bytes]}
    hardware_type: int = 0

    def __post_init__(self):
        super().__post_init__()
        if self.rom_data is None:
            self.rom_data = {}

    def to_bin(self) -> bytes:
        """Serialize to raw binary format.

        For Type 0 cartridges only. Concatenates ROML + ROMH data.
        For Ultimax mode (ultimax_romh), returns just the ultimax ROMH.
        """
        result = b""
        if "roml" in self.rom_data:
            result += self.rom_data["roml"]
        if "romh" in self.rom_data:
            result += self.rom_data["romh"]
        if "ultimax_romh" in self.rom_data:
            result += self.rom_data["ultimax_romh"]
        if result:
            return result
        elif "banks" in self.rom_data:
            return b"".join(self.rom_data["banks"])
        return b""

    def to_crt(self) -> bytes:
        """Serialize to CRT format."""
        header = self._build_crt_header()
        chips = self._build_chips()
        return header + chips

    def _build_crt_header(self) -> bytes:
        """Build 64-byte CRT header."""
        header = bytearray(64)

        # Signature: "C64 CARTRIDGE   " (16 bytes, space-padded)
        signature = b"C64 CARTRIDGE   "
        header[0:16] = signature

        # Header length (32-bit big-endian) - 64 bytes
        header[16:20] = struct.pack(">I", 64)

        # CRT version (16-bit big-endian) - 1.0
        header[20:22] = struct.pack(">H", 0x0100)

        # Hardware type (16-bit big-endian)
        header[22:24] = struct.pack(">H", self.hardware_type)

        # EXROM line (8-bit)
        header[24] = self.exrom

        # GAME line (8-bit)
        header[25] = self.game

        # Reserved (6 bytes) - already zero

        # Name (32 bytes, null-padded)
        name = self.description.encode("ascii", errors="replace")[:32]
        header[32:32 + len(name)] = name

        return bytes(header)

    def _build_chip_packet(self, bank: int, load_addr: int, data: bytes) -> bytes:
        """Build CHIP packet with header + ROM data."""
        # CHIP signature (4 bytes)
        packet = bytearray(b"CHIP")

        # Total packet length (32-bit big-endian) = 16 + ROM size
        packet_length = 16 + len(data)
        packet.extend(struct.pack(">I", packet_length))

        # Chip type (16-bit big-endian) - 0 = ROM
        packet.extend(struct.pack(">H", 0))

        # Bank number (16-bit big-endian)
        packet.extend(struct.pack(">H", bank))

        # Load address (16-bit big-endian)
        packet.extend(struct.pack(">H", load_addr))

        # ROM size (16-bit big-endian)
        packet.extend(struct.pack(">H", len(data)))

        # ROM data
        packet.extend(data)

        return bytes(packet)

    def _build_chips(self) -> bytes:
        """Build all CHIP packets based on rom_data structure."""
        chips = b""

        if "roml" in self.rom_data:
            if self.extra.get("single_chip") and "romh" in self.rom_data:
                # Combined ROML+ROMH as single 16KB chip
                combined = self.rom_data["roml"] + self.rom_data["romh"]
                chips += self._build_chip_packet(
                    bank=0, load_addr=ROML_START, data=combined
                )
            else:
                # ROML as separate chip
                chips += self._build_chip_packet(
                    bank=0, load_addr=ROML_START, data=self.rom_data["roml"]
                )
                if "romh" in self.rom_data:
                    # ROMH as separate chip (16KB mode at $A000)
                    chips += self._build_chip_packet(
                        bank=0, load_addr=ROMH_START, data=self.rom_data["romh"]
                    )
                if "ultimax_romh" in self.rom_data:
                    # Ultimax ROMH as separate chip at $E000 (with ROML present)
                    chips += self._build_chip_packet(
                        bank=0, load_addr=ULTIMAX_ROMH_START, data=self.rom_data["ultimax_romh"]
                    )
        elif "romh" in self.rom_data:
            # ROMH alone (Ultimax mode - loads at $E000)
            # Use extra["ultimax_romh_addr"] if specified, else ULTIMAX_ROMH_START
            romh_addr = self.extra.get("ultimax_romh_addr", ULTIMAX_ROMH_START)
            chips += self._build_chip_packet(
                bank=0, load_addr=romh_addr, data=self.rom_data["romh"]
            )
        elif "ultimax_romh" in self.rom_data:
            # Ultimax ROMH alone at $E000
            chips += self._build_chip_packet(
                bank=0, load_addr=ULTIMAX_ROMH_START, data=self.rom_data["ultimax_romh"]
            )

        if "banks" in self.rom_data:
            for i, bank_data in enumerate(self.rom_data["banks"]):
                chips += self._build_chip_packet(
                    bank=i, load_addr=ROML_START, data=bank_data
                )

        return chips


# Mapper requirements for each hardware type
# This defines what each mapper type needs to function
MAPPER_REQUIREMENTS: dict[int | CartridgeType, MapperRequirements] = {
    # Type 0: Static ROM - simplest type, no banking
    CartridgeType.NORMAL: MapperRequirements(
        uses_roml=True,
        uses_romh=True,  # 16KB mode
        uses_ultimax_romh=True,  # Ultimax mode
        num_banks=1,
    ),
    # Type 1: Action Replay - freezer with bank switching
    CartridgeType.ACTION_REPLAY: MapperRequirements(
        uses_roml=True,
        uses_romh=True,
        num_banks=4,
        uses_io1=True,
        uses_io2=True,
        has_ram=True,
        ram_size=0x2000,  # 8KB RAM
        control_registers=[
            ("$DE00", "Control Reg"),
        ],
    ),
    # Type 2: KCS Power Cartridge
    CartridgeType.KCS_POWER: MapperRequirements(
        uses_roml=True,
        uses_romh=True,
        num_banks=1,
        uses_io1=True,
        uses_io2=True,
        control_registers=[
            ("$DE00", "Config"),
            ("$DF00", "Freeze"),
        ],
    ),
    # Type 3: Final Cartridge III
    CartridgeType.FINAL_CARTRIDGE_III: MapperRequirements(
        uses_roml=True,
        uses_romh=True,
        num_banks=4,
        uses_io1=True,
        uses_io2=True,
        control_registers=[
            ("$DFFF", "Control"),
        ],
    ),
    # Type 4: Simons' BASIC
    CartridgeType.SIMONS_BASIC: MapperRequirements(
        uses_roml=True,
        uses_romh=True,
        num_banks=1,
        uses_io1=True,
        uses_io2=True,
        control_registers=[
            ("$DE00", "Enable ROMH"),
            ("$DF00", "Disable ROMH"),
        ],
    ),
    # Type 5: Ocean type 1
    CartridgeType.OCEAN_TYPE_1: MapperRequirements(
        uses_roml=True,
        uses_romh=True,
        num_banks=64,  # Up to 512KB
        uses_io1=True,
        control_registers=[
            ("$DE00", "Bank Select"),
        ],
    ),
    # Type 10: Epyx FastLoad
    CartridgeType.EPYX_FASTLOAD: MapperRequirements(
        uses_roml=True,
        num_banks=1,
        uses_io1=True,  # Reading IO1 enables cartridge
        uses_io2=True,  # IO2 shows last 256 bytes of ROM (always visible)
        control_registers=[
            ("$DE00", "Enable (read)"),
            ("$DF00", "ROM stub"),
        ],
    ),
    # Type 13: Final Cartridge I
    CartridgeType.FINAL_CARTRIDGE_I: MapperRequirements(
        uses_roml=True,
        uses_romh=True,
        num_banks=1,
        uses_io1=True,  # Any IO1 access disables cartridge
        uses_io2=True,  # Any IO2 access enables cartridge
        control_registers=[
            ("$DE00", "Disable (any access)"),
            ("$DF00", "Enable (any access)"),
        ],
    ),
    # Type 15: C64 Game System / System 3
    CartridgeType.C64_GAME_SYSTEM: MapperRequirements(
        uses_roml=True,
        num_banks=64,  # Up to 512KB (64 x 8KB banks)
        uses_io1=True,
        control_registers=[
            ("$DE00", "Bank Select (read disables)"),
        ],
    ),
    # Type 17: Dinamic
    CartridgeType.DINAMIC: MapperRequirements(
        uses_roml=True,
        num_banks=16,  # 128KB typical
        uses_io1=True,
        control_registers=[
            ("$DE00", "Bank Select"),
        ],
    ),
    # Type 19: Magic Desk / Domark / HES Australia
    CartridgeType.MAGIC_DESK: MapperRequirements(
        uses_roml=True,
        num_banks=64,  # Up to 512KB (64 x 8KB banks)
        uses_io1=True,
        control_registers=[
            ("$DE00", "Bank/Disable"),
        ],
    ),
}


def generate_mapper_tests(hw_type: int) -> list[MapperTest]:
    """Generate the list of tests for a mapper type.

    This is the single source of truth for both:
    - Test cart generation (create_test_carts.py)
    - Error cart display (to_display_lines)

    Args:
        hw_type: CRT hardware type number

    Returns:
        List of MapperTest objects, all defaulting to FAIL
    """
    reqs = MAPPER_REQUIREMENTS.get(hw_type)
    if reqs is None:
        return []

    tests = []
    bank_size = reqs.bank_size

    # Generate bank tests
    if reqs.num_banks > 1:
        for bank_num in range(reqs.num_banks):
            bank_offset = bank_num * bank_size
            tests.append(MapperTest(
                name=f"Bank {bank_num} ${bank_offset:04X}",
                test_id=f"bank_{bank_num}",
            ))
    else:
        # Single bank - just test ROML/ROMH presence
        if reqs.uses_roml:
            tests.append(MapperTest(name="ROML $8000", test_id="roml"))
        if reqs.uses_romh:
            tests.append(MapperTest(name="ROMH $A000", test_id="romh"))
        if reqs.uses_ultimax_romh:
            tests.append(MapperTest(name="ROMH $E000", test_id="ultimax_romh"))

    # Generate I/O and control register tests
    ctrl_addr_set = {a for a, _ in reqs.control_registers}

    if reqs.uses_io1 and "$DE00" not in ctrl_addr_set:
        tests.append(MapperTest(name="IO1 $DE00-$DEFF", test_id="io1"))
    if reqs.uses_io2 and "$DF00" not in ctrl_addr_set:
        if reqs.has_ram:
            tests.append(MapperTest(name="IO2 $DF00 RAM", test_id="io2_ram"))
        else:
            tests.append(MapperTest(name="IO2 $DF00-$DFFF", test_id="io2"))

    # Control registers
    for reg_addr, name in reqs.control_registers:
        safe_id = reg_addr.replace("$", "").lower()
        tests.append(MapperTest(name=f"{reg_addr} {name}", test_id=f"reg_{safe_id}"))

    return tests


@dataclass
class CartridgeTestResults:
    """Test results for cartridge loading - starts with all FAILs.

    Each field represents a test that can be performed during cartridge loading.
    All fields default to False (FAIL). As parsing/validation succeeds,
    fields are set to True (PASS). If we crash or bail early, anything
    not yet set remains FAIL.
    """
    # Basic CRT format validation
    signature_valid: bool = False       # "C64 CARTRIDGE   " signature found
    header_size_valid: bool = False     # Header length is valid
    version_valid: bool = False         # CRT version is recognized

    # Hardware type info (captured, not pass/fail)
    hardware_type: int = -1             # Detected hardware type
    hardware_name: str = "Unknown"      # Hardware type name

    # EXROM/GAME line configuration
    exrom_line: int = -1                # EXROM line value
    game_line: int = -1                 # GAME line value

    # Cartridge name
    cart_name: str = ""                 # Name from CRT header

    # CHIP packet validation
    chip_packets_found: bool = False    # At least one valid CHIP packet
    chip_count: int = 0                 # Number of CHIP packets parsed

    # ROM region validation (depends on cart type)
    roml_valid: bool = False            # ROML region ($8000-$9FFF) loaded
    romh_valid: bool = False            # ROMH region ($A000-$BFFF) loaded
    ultimax_romh_valid: bool = False    # Ultimax ROMH region ($E000-$FFFF) loaded

    # Mapper-specific validation
    mapper_supported: bool = False      # Hardware type is supported

    # Individual mapper address validation (for partial implementation tracking)
    # Keys are addresses like "$DE00", values are (name, pass/fail)
    mapper_addresses: dict = None       # Initialized in __post_init__

    # Overall status
    fully_loaded: bool = False          # Cart loaded and attached successfully

    def __post_init__(self):
        if self.mapper_addresses is None:
            self.mapper_addresses = {}

    def to_display_lines(self) -> list[str]:
        """Convert results to display lines for error cartridge.

        Uses generate_mapper_tests() as the single source of truth for
        which tests to display - same as test cartridge generation.

        Color markup codes (parsed by create_error_cartridge_rom):
        - {g}text{/} = green (for PASS)
        - {r}text{/} = red (for FAIL)
        - {c}text{/} = cyan (for addresses)
        - {y}text{/} = yellow (for labels)
        """
        def status(val: bool) -> str:
            return "{g}PASS{/}" if val else "{r}FAIL{/}"

        def colorize_test_name(name: str) -> str:
            """Add cyan color to address portions of test name."""
            # Look for $XXXX patterns and colorize them
            return re.sub(r'(\$[0-9A-Fa-f-]+)', r'{c}\1{/}', name)

        # Header section
        lines = [
            "",
            "  UNSUPPORTED CARTRIDGE TYPE",
            "",
            f"  Type: {self.hardware_type}",
            f"  Name: {self.hardware_name}",
            "",
            f"  Cart: {self.cart_name[:24]}",
            "",
        ]

        # Show pass/fail for format checks
        lines.extend([
            "  CRT FORMAT:",
            f"    Signature:  {status(self.signature_valid)}",
            f"    Header:     {status(self.header_size_valid)}",
            f"    CHIP pkts:  {status(self.chip_packets_found)} ({self.chip_count})",
        ])

        # Get mapper requirements if defined
        mapper_reqs = MAPPER_REQUIREMENTS.get(self.hardware_type)

        if self.mapper_supported:
            # For supported mappers, use generate_mapper_tests() with actual results
            lines.append("")
            lines.append("  MAPPER TESTS:")

            tests = generate_mapper_tests(self.hardware_type)
            display_count = 0
            for test in tests:
                # Get pass/fail status from mapper_addresses or specific fields
                passed = False
                if test.test_id.startswith("bank_"):
                    bank_key = f"Bank {test.test_id.split('_')[1]}"
                    passed = self.mapper_addresses.get(bank_key, (None, False))[1]
                elif test.test_id == "roml":
                    passed = self.roml_valid
                elif test.test_id == "romh":
                    passed = self.romh_valid
                elif test.test_id == "ultimax_romh":
                    passed = self.ultimax_romh_valid
                elif test.test_id == "io1":
                    passed = self.mapper_addresses.get("$DE00", (None, False))[1]
                elif test.test_id in ("io2", "io2_ram"):
                    passed = self.mapper_addresses.get("$DF00", (None, False))[1]
                elif test.test_id.startswith("reg_"):
                    reg_addr = "$" + test.test_id[4:].upper()
                    passed = self.mapper_addresses.get(reg_addr, (None, False))[1]

                # Limit display to first 4 banks for many-bank carts
                if test.test_id.startswith("bank_"):
                    bank_num = int(test.test_id.split('_')[1])
                    if bank_num >= 4:
                        if bank_num == 4 and mapper_reqs and mapper_reqs.num_banks > 4:
                            lines.append(f"    ... ({mapper_reqs.num_banks} banks)")
                        continue

                lines.append(f"    {colorize_test_name(test.name)}: {status(passed)}")
                display_count += 1
        else:
            lines.append("")
            lines.append("  MAPPER: {r}NOT IMPLEMENTED{/}")

            # For unsupported mappers, use generate_mapper_tests() with all FAILs
            tests = generate_mapper_tests(self.hardware_type)
            if tests:
                lines.append("")
                lines.append("  REQUIRED TESTS:")

                # For many banks, show compact summary instead of individual tests
                if mapper_reqs and mapper_reqs.num_banks > 4:
                    bank_size = mapper_reqs.bank_size
                    size_kb = bank_size // 1024
                    total_size = mapper_reqs.num_banks * bank_size
                    end_addr = total_size - 1
                    if end_addr > 0xFFFF:
                        lines.append(f"    {mapper_reqs.num_banks}x{size_kb}KB Banks " + "{c}" + f"$00000-${end_addr:05X}" + "{/}: {r}FAIL{/}")
                    else:
                        lines.append(f"    {mapper_reqs.num_banks}x{size_kb}KB Banks " + "{c}" + f"$0000-${end_addr:04X}" + "{/}: {r}FAIL{/}")

                    # Show non-bank tests
                    for test in tests:
                        if not test.test_id.startswith("bank_"):
                            lines.append(f"    {colorize_test_name(test.name)}: " + "{r}FAIL{/}")
                else:
                    # Show all tests for few-bank carts
                    for test in tests:
                        lines.append(f"    {colorize_test_name(test.name)}: " + "{r}FAIL{/}")

        return lines


def parse_color_markup(text: str) -> list[tuple[str, int]]:
    """Parse color markup in text and return list of (char, color) tuples.

    Color markup codes:
    - {g}text{/} = green (0x05) - for PASS
    - {r}text{/} = red (0x02) - for FAIL
    - {c}text{/} = cyan (0x03) - for addresses
    - {y}text{/} = yellow (0x07) - for labels

    Args:
        text: Text with optional color markup

    Returns:
        List of (character, c64_color) tuples
    """
    # C64 color codes
    # Note: 'r' uses light red (0x0A) instead of red (0x02) so it's visible
    # on the red background of error carts
    COLOR_MAP = {
        'g': 0x05,  # Green
        'r': 0x0A,  # Light red (visible on dark red background)
        'c': 0x03,  # Cyan
        'y': 0x07,  # Yellow
    }
    DEFAULT_COLOR = 0x01  # White

    result = []
    current_color = DEFAULT_COLOR
    i = 0

    while i < len(text):
        # Check for color start tag {x}
        if text[i] == '{' and i + 2 < len(text) and text[i + 2] == '}':
            tag = text[i + 1]
            if tag in COLOR_MAP:
                current_color = COLOR_MAP[tag]
                i += 3
                continue
            elif tag == '/':
                # End tag {/} - reset to white
                current_color = DEFAULT_COLOR
                i += 3
                continue

        # Regular character
        result.append((text[i], current_color))
        i += 1

    return result


def create_error_cartridge_rom(error_lines: list[str], border_color: int = 0x02) -> bytes:
    """Create an 8KB cartridge ROM that displays an error/info message.

    This is the single source of truth for error cartridge generation,
    used both at runtime (when loading unsupported carts) and by the
    test cartridge generation script.

    Supports color markup in text:
    - {g}text{/} = green (for PASS)
    - {r}text{/} = red (for FAIL)
    - {c}text{/} = cyan (for addresses)
    - {y}text{/} = yellow (for labels)

    Arguments:
        error_lines: List of text lines to display (max ~38 chars each, max 20 lines)
        border_color: VIC-II color for border (default 0x02 = red), background stays black

    Returns:
        8KB cartridge ROM data
    """
    cart = bytearray(ROML_SIZE)

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
    code = []

    # SEI, set up stack
    code.extend([0x78, 0xA2, 0xFF, 0x9A])  # SEI; LDX #$FF; TXS

    # Clear screen with spaces
    code.extend([0xA9, 0x20, 0xA2, 0x00])  # LDA #$20; LDX #$00
    # clear_loop:
    code.extend([
        0x9D, 0x00, 0x04,  # STA $0400,X
        0x9D, 0x00, 0x05,  # STA $0500,X
        0x9D, 0x00, 0x06,  # STA $0600,X
        0x9D, 0x00, 0x07,  # STA $0700,X
        0xE8,              # INX
        0xD0, 0xF1,        # BNE clear_loop
    ])

    # Set border color (keep background black for text visibility)
    code.extend([
        0xA9, border_color,  # LDA #color
        0x8D, 0x20, 0xD0,    # STA $D020 (border)
        0xA9, 0x00,          # LDA #$00 (black)
        0x8D, 0x21, 0xD0,    # STA $D021 (background)
    ])

    # Display each error line
    for line_num, text in enumerate(error_lines[:20]):  # Max 20 lines
        # Parse color markup and get (char, color) pairs
        char_colors = parse_color_markup(text)

        # Limit to 38 visible characters
        char_colors = char_colors[:38]

        screen_addr = 0x0400 + (line_num * 40) + 1  # +1 for margin
        color_addr = 0xD800 + (line_num * 40) + 1

        for i, (ch, color) in enumerate(char_colors):
            # Convert ASCII to screen code
            if 'A' <= ch <= 'Z':
                sc = ord(ch) - ord('A') + 1
            elif 'a' <= ch <= 'z':
                sc = ord(ch) - ord('a') + 1
            elif '0' <= ch <= '9':
                sc = ord(ch) - ord('0') + 0x30
            elif ch == ' ':
                sc = 0x20
            elif ch == ':':
                sc = 0x3A
            elif ch == '-':
                sc = 0x2D
            elif ch == ',':
                sc = 0x2C
            elif ch == '.':
                sc = 0x2E
            elif ch == '!':
                sc = 0x21
            elif ch == '?':
                sc = 0x3F
            elif ch == '(':
                sc = 0x28
            elif ch == ')':
                sc = 0x29
            elif ch == '/':
                sc = 0x2F
            elif ch == '_':
                sc = 0x64
            elif ch == '$':
                sc = 0x24
            elif ch == '#':
                sc = 0x23
            elif ch == '+':
                sc = 0x2B
            elif ch == '=':
                sc = 0x3D
            elif ch == 'x':
                sc = 0x18  # 'x' screen code
            else:
                sc = 0x20  # Unknown -> space

            # LDA #sc; STA screen_addr+i
            code.extend([
                0xA9, sc,
                0x8D, (screen_addr + i) & 0xFF, (screen_addr + i) >> 8,
            ])
            # LDA #color; STA color_addr+i
            code.extend([
                0xA9, color,
                0x8D, (color_addr + i) & 0xFF, (color_addr + i) >> 8,
            ])

    # Infinite loop
    loop_addr = ROML_START + 0x0009 + len(code)
    code.extend([0x4C, loop_addr & 0xFF, (loop_addr >> 8) & 0xFF])

    # Copy code into cartridge
    for i, byte in enumerate(code):
        if 0x0009 + i < len(cart):
            cart[0x0009 + i] = byte

    return bytes(cart)


class Cartridge(ABC):
    """Base class for cartridge hardware emulation.

    Subclasses implement specific cartridge types with their own
    banking logic and I/O behavior.
    """

    # CRT hardware type ID (set by subclasses)
    HARDWARE_TYPE: int = -1

    def __init__(self, rom_data: bytes, name: str = "", description: str = ""):
        """Initialize cartridge with ROM data.

        Args:
            rom_data: Raw ROM data (may contain multiple banks)
            name: Cartridge name (from CRT header or filename)
            description: Human-readable description (e.g., "Ocean Type 1 test cart")
        """
        self.rom_data = rom_data
        self.name = name
        self._description = description
        self._exrom = True   # Default: inactive (no cartridge)
        self._game = True    # Default: inactive (no cartridge)

    @property
    def description(self) -> str:
        """Human-readable description of this cartridge.

        Returns _description if set, otherwise falls back to name.
        This property satisfies the CartridgeInterface protocol.
        """
        return self._description if self._description else self.name

    @property
    def exrom(self) -> bool:
        """EXROM line state (directly controls PLA memory mapping).

        True = inactive (active-low), False = active
        """
        return self._exrom

    @property
    def game(self) -> bool:
        """GAME line state.

        True = inactive (active-low), False = active
        """
        return self._game

    @abstractmethod
    def read_roml(self, addr: int) -> int:
        """Read from ROML region ($8000-$9FFF).

        Args:
            addr: Address in range $8000-$9FFF

        Returns:
            Byte value at address
        """
        pass

    def read_romh(self, addr: int) -> int:
        """Read from ROMH region ($A000-$BFFF).

        Args:
            addr: Address in range $A000-$BFFF

        Returns:
            Byte value at address, or 0xFF if not mapped
        """
        return 0xFF  # Default: not mapped

    def write_roml(self, addr: int, data: int) -> bool:
        """Write to ROML region ($8000-$9FFF).

        Some cartridges (like Action Replay) have RAM in the ROML region
        that can be written to. Override this method to handle writes.

        Args:
            addr: Address in range $8000-$9FFF
            data: Byte value to write

        Returns:
            True if write was handled by cartridge, False to write to C64 RAM
        """
        return False  # Default: not handled, write goes to C64 RAM

    def read_ultimax_romh(self, addr: int) -> int:
        """Read from Ultimax ROMH region ($E000-$FFFF).

        In Ultimax mode (EXROM=1, GAME=0), ROMH appears at $E000-$FFFF
        instead of $A000-$BFFF, replacing the KERNAL ROM.

        Args:
            addr: Address in range $E000-$FFFF

        Returns:
            Byte value at address, or 0xFF if not mapped
        """
        return 0xFF  # Default: not mapped

    def read_io1(self, addr: int) -> int:
        """Read from IO1 region ($DE00-$DEFF).

        Args:
            addr: Address in range $DE00-$DEFF

        Returns:
            Byte value at address, or 0xFF if not mapped
        """
        return 0xFF  # Default: open bus

    def read_io2(self, addr: int) -> int:
        """Read from IO2 region ($DF00-$DFFF).

        Args:
            addr: Address in range $DF00-$DFFF

        Returns:
            Byte value at address, or 0xFF if not mapped
        """
        return 0xFF  # Default: open bus

    def write_io1(self, addr: int, data: int) -> None:
        """Write to IO1 region ($DE00-$DEFF).

        This is typically where bank switching registers are located.

        Args:
            addr: Address in range $DE00-$DEFF
            data: Byte value to write
        """
        pass  # Default: ignore writes

    def write_io2(self, addr: int, data: int) -> None:
        """Write to IO2 region ($DF00-$DFFF).

        Args:
            addr: Address in range $DF00-$DFFF
            data: Byte value to write
        """
        pass  # Default: ignore writes

    def reset(self) -> None:
        """Reset cartridge to initial state.

        Called on C64 reset. Subclasses should reset bank registers etc.
        """
        pass  # Default: no state to reset

    # --- Test cartridge generation ---

    @classmethod
    def get_cartridge_variants(cls) -> list[CartridgeVariant]:
        """Return all valid configuration variants for this cartridge type.

        Each variant represents a different mode or configuration that should
        be tested. For example, Type 0 has 8k, 16k, and ultimax variants.

        Subclasses should override this method to return their specific variants.
        The default implementation returns an empty list, indicating no test
        cartridge generation is available yet.

        Returns:
            List of CartridgeVariant specifications
        """
        return []

    @classmethod
    def create_test_cartridge(cls, variant: CartridgeVariant) -> CartridgeImage:
        """Create test cartridge image for the given variant.

        Builds ROM data with test code that verifies the cartridge type works
        correctly (bank switching, memory mapping, etc.).

        Subclasses should override this method to implement test cart generation.
        The default implementation raises NotImplementedError.

        Args:
            variant: The configuration variant to generate

        Returns:
            CartridgeImage with ROM data ready for serialization

        Raises:
            NotImplementedError: If the subclass hasn't implemented this method
        """
        raise NotImplementedError(
            f"{cls.__name__}.create_test_cartridge() not implemented"
        )

    @classmethod
    def create_error_cartridge(
        cls, variant: CartridgeVariant, results: CartridgeTestResults
    ) -> CartridgeImage:
        """Create error cartridge image for error_cartridges/ directory.

        Generates a simple 8KB cartridge that displays the error information
        on screen. Used as a fallback when cart loading fails.

        Args:
            variant: The configuration variant this error cart represents
            results: Test results showing what failed

        Returns:
            CartridgeImage for a Type 0 8KB error display cart
        """
        lines = results.to_display_lines()
        rom_bytes = create_error_cartridge_rom(lines, border_color=0x02)  # Red border
        return CartridgeImage(
            description=variant.description,
            exrom=0,
            game=1,
            extra=variant.extra,
            rom_data={"roml": rom_bytes},
            hardware_type=0,  # Type 0 for simplest compatibility
        )
