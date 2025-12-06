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
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum

log = logging.getLogger("c64.cartridge")


class CartridgeType(IntEnum):
    """CRT hardware type IDs from the VICE emulator specification.

    These are the standard cartridge type IDs used in CRT files.
    The list comes from: http://rr.c64.org/wiki/CRT_ID

    Only the most common/implemented types are named here.
    Use the integer value directly for unlisted types.
    """
    # Implemented types
    NORMAL = 0                  # Generic/normal cartridge (8K/16K/Ultimax)
    ACTION_REPLAY = 1           # Action Replay freezer cartridge
    FINAL_CARTRIDGE_III = 3     # Final Cartridge III freezer
    SIMONS_BASIC = 4            # Simons' BASIC extension
    OCEAN_TYPE_1 = 5            # Ocean Type 1 bank switching
    EPYX_FASTLOAD = 10          # Epyx FastLoad disk speedup
    C64_GAME_SYSTEM = 15        # C64 Game System / System 3
    DINAMIC = 17                # Dinamic bank switching
    MAGIC_DESK = 19             # Magic Desk / Domark / HES Australia

    # Not yet implemented but commonly seen
    KCS_POWER = 2               # KCS Power Cartridge
    FUN_PLAY = 7                # Fun Play / Power Play
    SUPER_GAMES = 8             # Super Games
    ATOMIC_POWER = 9            # Atomic Power
    WESTERMANN = 11             # Westermann Learning
    REX_UTILITY = 12            # Rex Utility
    FINAL_CARTRIDGE_I = 13      # Final Cartridge I
    MAGIC_FORMEL = 14           # Magic Formel
    WARPSPEED = 16              # WarpSpeed
    ZAXXON = 18                 # Zaxxon / Super Zaxxon
    SUPER_SNAPSHOT_5 = 20       # Super Snapshot 5
    COMAL_80 = 21               # COMAL 80
    EASYFLASH = 32              # EasyFlash

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

    def __init__(self, rom_data: bytes, name: str = ""):
        """Initialize cartridge with ROM data.

        Args:
            rom_data: Raw ROM data (may contain multiple banks)
            name: Cartridge name (from CRT header or filename)
        """
        self.rom_data = rom_data
        self.name = name
        self._exrom = True   # Default: inactive (no cartridge)
        self._game = True    # Default: inactive (no cartridge)

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
