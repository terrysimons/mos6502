"""Cartridge hardware emulation for C64.

This module provides classes that emulate the hardware behavior of various
C64 cartridge types. Each cartridge type has different banking logic that
is implemented in external hardware on the cartridge PCB.

The CRT file format encodes the cartridge type in the header, which tells
emulators which banking logic to use. Raw .bin files don't have this
information, so they're assumed to be standard (type 0) cartridges.

Memory regions controlled by cartridges:
    ROML: $8000-$9FFF (8KB) - Active when EXROM=0
    ROMH: $A000-$BFFF (8KB) - Active when EXROM=0 and GAME=0
    IO1:  $DE00-$DEFF - Cartridge I/O area 1 (optional, used for bank switching)
    IO2:  $DF00-$DFFF - Cartridge I/O area 2 (optional)

EXROM and GAME are active-low signals from the cartridge that control
the C64's PLA memory mapping:
    EXROM=1, GAME=1: No cartridge (default)
    EXROM=0, GAME=1: 8KB mode (ROML visible)
    EXROM=0, GAME=0: 16KB mode (ROML and ROMH visible)
    EXROM=1, GAME=0: Ultimax mode (ROMH at $E000, replaces KERNAL)

References:
    CRT file format and hardware type IDs:
        - VICE CRT format specification: https://vice-emu.sourceforge.io/vice_17.html#SEC391
        - CRT ID list: http://rr.c64.org/wiki/CRT_ID

    The hardware type list (0-85) comes from the VICE emulator specification,
    which is the de facto standard for C64 cartridge emulation.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

log = logging.getLogger("c64.cartridge")


# Memory region constants
ROML_START = 0x8000
ROML_END = 0x9FFF
ROML_SIZE = 0x2000  # 8KB

ROMH_START = 0xA000
ROMH_END = 0xBFFF
ROMH_SIZE = 0x2000  # 8KB

IO1_START = 0xDE00
IO1_END = 0xDEFF

IO2_START = 0xDF00
IO2_END = 0xDFFF


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
        """EXROM line state (directly accent controls PLA memory mapping).

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


class StaticROMCartridge(Cartridge):
    """Type 0: Static ROM cartridge with no bank switching.

    CRT hardware type 0 (called "Normal cartridge" in VICE/CCS64 spec).
    The simplest cartridge type where ROM is directly mapped to fixed
    addresses with no banking hardware:

    - 8KB mode: ROML at $8000-$9FFF (EXROM=0, GAME=1)
    - 16KB mode: ROML at $8000-$9FFF, ROMH at $A000-$BFFF (EXROM=0, GAME=0)

    The entire ROM content is visible at once - no registers, no
    bank switching, no I/O handlers. Just ROM chips wired directly
    to the address bus.

    Examples: Q*bert, Gorf, Jupiter Lander, diagnostic cartridges,
    simple auto-start utility cartridges.
    """

    HARDWARE_TYPE = 0

    def __init__(self, roml_data: bytes, romh_data: Optional[bytes] = None, name: str = ""):
        """Initialize static ROM cartridge.

        Args:
            roml_data: 8KB ROM data for ROML region ($8000-$9FFF)
            romh_data: Optional 8KB ROM data for ROMH region ($A000-$BFFF)
            name: Cartridge name
        """
        # Combine ROM data for base class
        if romh_data:
            super().__init__(roml_data + romh_data, name)
        else:
            super().__init__(roml_data, name)

        self.roml_data = roml_data
        self.romh_data = romh_data

        # Set EXROM/GAME based on cartridge size
        self._exrom = False  # Active (cartridge present)
        self._game = romh_data is None  # True for 8KB, False for 16KB

        cart_type = "16KB" if romh_data else "8KB"
        log.debug(f"StaticROMCartridge: {cart_type}, EXROM={0 if not self._exrom else 1}, GAME={0 if not self._game else 1}")

    def read_roml(self, addr: int) -> int:
        """Read from ROML region ($8000-$9FFF)."""
        offset = addr - ROML_START
        if offset < len(self.roml_data):
            return self.roml_data[offset]
        return 0xFF

    def read_romh(self, addr: int) -> int:
        """Read from ROMH region ($A000-$BFFF)."""
        if self.romh_data is None:
            return 0xFF
        offset = addr - ROMH_START
        if offset < len(self.romh_data):
            return self.romh_data[offset]
        return 0xFF


class ErrorCartridge(StaticROMCartridge):
    """Special cartridge that displays an error message.

    Used when an unsupported cartridge type is loaded. Displays
    the cartridge type and name on screen with a red background.
    """

    HARDWARE_TYPE = -1  # Not a real hardware type

    def __init__(self, roml_data: bytes, original_type: int, original_name: str):
        """Initialize error cartridge.

        Args:
            roml_data: Pre-generated error display ROM
            original_type: The unsupported hardware type that was attempted
            original_name: Name of the original cartridge
        """
        super().__init__(roml_data, romh_data=None, name=f"Error: {original_name}")
        self.original_type = original_type
        self.original_name = original_name


# Registry of cartridge classes by hardware type
CARTRIDGE_TYPES: dict[int, type[Cartridge]] = {
    0: StaticROMCartridge,
}


def create_cartridge(
    hardware_type: int,
    roml_data: bytes,
    romh_data: Optional[bytes] = None,
    name: str = "",
) -> Cartridge:
    """Factory function to create appropriate cartridge instance.

    Args:
        hardware_type: CRT hardware type ID
        roml_data: ROM data for ROML region
        romh_data: Optional ROM data for ROMH region
        name: Cartridge name

    Returns:
        Cartridge instance of appropriate type

    Raises:
        ValueError: If hardware type is not supported
    """
    if hardware_type not in CARTRIDGE_TYPES:
        raise ValueError(f"Unsupported cartridge hardware type: {hardware_type}")

    cart_class = CARTRIDGE_TYPES[hardware_type]

    if cart_class == StaticROMCartridge:
        return StaticROMCartridge(roml_data, romh_data, name)
    else:
        # Future: other cartridge types may have different constructors
        raise ValueError(f"Cartridge type {hardware_type} not yet implemented")
