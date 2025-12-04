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

# Ultimax mode: ROMH appears at $E000-$FFFF instead of $A000-$BFFF
ULTIMAX_ROMH_START = 0xE000
ULTIMAX_ROMH_END = 0xFFFF
ULTIMAX_ROMH_SIZE = 0x2000  # 8KB

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


class StaticROMCartridge(Cartridge):
    """Type 0: Static ROM cartridge with no bank switching.

    CRT hardware type 0 (called "Normal cartridge" in VICE/CCS64 spec).
    The simplest cartridge type where ROM is directly mapped to fixed
    addresses with no banking hardware:

    - 8KB mode: ROML at $8000-$9FFF (EXROM=0, GAME=1)
    - 16KB mode: ROML at $8000-$9FFF, ROMH at $A000-$BFFF (EXROM=0, GAME=0)
    - Ultimax mode: ROMH at $E000-$FFFF, optional ROML at $8000-$9FFF (EXROM=1, GAME=0)

    The entire ROM content is visible at once - no registers, no
    bank switching, no I/O handlers. Just ROM chips wired directly
    to the address bus.

    Examples: Q*bert, Gorf, Jupiter Lander, diagnostic cartridges,
    simple auto-start utility cartridges, Dead Test ROM (Ultimax).
    """

    HARDWARE_TYPE = 0

    def __init__(
        self,
        roml_data: Optional[bytes] = None,
        romh_data: Optional[bytes] = None,
        ultimax_romh_data: Optional[bytes] = None,
        name: str = "",
    ):
        """Initialize static ROM cartridge.

        Args:
            roml_data: 8KB ROM data for ROML region ($8000-$9FFF)
            romh_data: 8KB ROM data for ROMH region ($A000-$BFFF) - 16KB mode
            ultimax_romh_data: 8KB ROM data for Ultimax ROMH ($E000-$FFFF)
            name: Cartridge name

        Modes:
            - 8KB mode: roml_data only (EXROM=0, GAME=1)
            - 16KB mode: roml_data + romh_data (EXROM=0, GAME=0)
            - Ultimax mode: ultimax_romh_data, optional roml_data (EXROM=1, GAME=0)
        """
        # Combine ROM data for base class
        all_rom = b""
        if roml_data:
            all_rom += roml_data
        if romh_data:
            all_rom += romh_data
        if ultimax_romh_data:
            all_rom += ultimax_romh_data
        super().__init__(all_rom if all_rom else b"", name)

        self.roml_data = roml_data
        self.romh_data = romh_data
        self.ultimax_romh_data = ultimax_romh_data

        # Determine mode based on which ROM regions are populated
        if ultimax_romh_data is not None:
            # Ultimax mode: EXROM=1 (inactive), GAME=0 (active)
            self._exrom = True
            self._game = False
            cart_type = "Ultimax"
        elif romh_data is not None:
            # 16KB mode: EXROM=0 (active), GAME=0 (active)
            self._exrom = False
            self._game = False
            cart_type = "16KB"
        else:
            # 8KB mode: EXROM=0 (active), GAME=1 (inactive)
            self._exrom = False
            self._game = True
            cart_type = "8KB"

        log.debug(
            f"StaticROMCartridge: {cart_type}, "
            f"EXROM={1 if self._exrom else 0}, GAME={1 if self._game else 0}"
        )

    def read_roml(self, addr: int) -> int:
        """Read from ROML region ($8000-$9FFF)."""
        if self.roml_data is None:
            return 0xFF
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

    def read_ultimax_romh(self, addr: int) -> int:
        """Read from Ultimax ROMH region ($E000-$FFFF)."""
        if self.ultimax_romh_data is None:
            return 0xFF
        offset = addr - ULTIMAX_ROMH_START
        if offset < len(self.ultimax_romh_data):
            return self.ultimax_romh_data[offset]
        return 0xFF


class ActionReplayCartridge(Cartridge):
    """Type 1: Action Replay cartridge with bank switching.

    CRT hardware type 1. The Action Replay is a freezer cartridge with
    32KB ROM organized as 4 x 8KB banks, plus 8KB RAM.

    Control register at $DE00 (write only):
        Bit 0: 1 = /GAME low (active)
        Bit 1: 1 = /EXROM high (inactive)
        Bit 2: 1 = disable cartridge (turns off $DE00 register)
        Bit 3: ROM bank selector low (A13)
        Bit 4: ROM bank selector high (A14)
        Bit 5: 1 = enable RAM at ROML and IO2
        Bit 6: 1 = reset freeze mode
        Bit 7: extra ROM bank selector (unused)

    Memory mapping:
        - ROML ($8000-$9FFF): Bank 0-3 of ROM, or RAM if bit 5 set
        - ROMH ($A000-$BFFF): Bank 0-3 of ROM (mirrored in 16KB mode)
        - IO2 ($DF00-$DFFF): RAM if bit 5 set

    Initial state: 16KB mode with bank 0 (EXROM=0, GAME=0)

    References:
        - VICE actionreplay.c
        - https://rr.c64.org/wiki/Action_Replay
    """

    HARDWARE_TYPE = 1
    ACTIVE_BANK_SIZE = ROML_SIZE  # 8KB banks

    def __init__(self, banks: list[bytes], name: str = ""):
        """Initialize Action Replay cartridge.

        Args:
            banks: List of 8KB ROM banks (typically 4 banks = 32KB)
            name: Cartridge name
        """
        # Combine all banks for base class
        all_rom = b"".join(banks)
        super().__init__(all_rom, name)

        self.banks = banks
        self.num_banks = len(banks)

        # 8KB RAM for ROML/IO2 when enabled
        self.ram = bytearray(ROML_SIZE)

        # Control register state
        self.current_bank = 0
        self.ram_enabled = False
        self.cartridge_disabled = False

        # Initial state: 16KB mode (EXROM=0, GAME=0)
        self._exrom = False
        self._game = False

        log.debug(
            f"ActionReplayCartridge: {self.num_banks} banks, "
            f"EXROM={1 if self._exrom else 0}, GAME={1 if self._game else 0}"
        )

    def reset(self) -> None:
        """Reset cartridge to initial state."""
        self.current_bank = 0
        self.ram_enabled = False
        self.cartridge_disabled = False
        self._exrom = False
        self._game = False

    def read_roml(self, addr: int) -> int:
        """Read from ROML region ($8000-$9FFF)."""
        if self.cartridge_disabled:
            return 0xFF

        offset = addr - ROML_START

        if self.ram_enabled:
            return self.ram[offset]

        if self.current_bank < self.num_banks:
            bank_data = self.banks[self.current_bank]
            if offset < len(bank_data):
                return bank_data[offset]
        return 0xFF

    def read_romh(self, addr: int) -> int:
        """Read from ROMH region ($A000-$BFFF)."""
        if self.cartridge_disabled:
            return 0xFF

        # ROMH mirrors the current bank
        offset = addr - ROMH_START

        if self.current_bank < self.num_banks:
            bank_data = self.banks[self.current_bank]
            if offset < len(bank_data):
                return bank_data[offset]
        return 0xFF

    def read_io1(self, addr: int) -> int:
        """Read from IO1 region ($DE00-$DEFF).

        Note: On real hardware, reading IO1 can crash the C64.
        We return open bus (0xFF) like most emulators.
        """
        return 0xFF

    def read_io2(self, addr: int) -> int:
        """Read from IO2 region ($DF00-$DFFF)."""
        if self.cartridge_disabled:
            return 0xFF

        if self.ram_enabled:
            # IO2 maps to last 256 bytes of ROML RAM area
            # $DF00-$DFFF -> $9F00-$9FFF in RAM (offset = ROML_SIZE - 256 + io2_offset)
            io2_ram_base = ROML_SIZE - 0x100  # 0x1F00 - last 256 bytes
            offset = io2_ram_base + (addr - IO2_START)
            return self.ram[offset]
        return 0xFF

    def write_io1(self, addr: int, data: int) -> None:
        """Write to IO1 region ($DE00-$DEFF) - control register."""
        if self.cartridge_disabled:
            return

        # Bit 0: /GAME control (1 = GAME active/low)
        game_active = (data & 0x01) != 0
        self._game = not game_active  # Invert: bit=1 means GAME low (active)

        # Bit 1: /EXROM control (1 = EXROM high/inactive)
        exrom_inactive = (data & 0x02) != 0
        self._exrom = exrom_inactive

        # Bit 2: Disable cartridge
        if data & 0x04:
            self.cartridge_disabled = True
            self._exrom = True
            self._game = True

        # Bits 3-4: Bank selection
        self.current_bank = (data >> 3) & 0x03

        # Bit 5: RAM enable
        self.ram_enabled = (data & 0x20) != 0

        log.debug(
            f"ActionReplay $DE00 write: ${data:02X} -> "
            f"bank={self.current_bank}, RAM={self.ram_enabled}, "
            f"disabled={self.cartridge_disabled}, "
            f"EXROM={1 if self._exrom else 0}, GAME={1 if self._game else 0}"
        )

    def write_io2(self, addr: int, data: int) -> None:
        """Write to IO2 region ($DF00-$DFFF)."""
        if self.cartridge_disabled:
            return

        if self.ram_enabled:
            # IO2 maps to last 256 bytes of ROML RAM area
            io2_ram_base = ROML_SIZE - 0x100  # 0x1F00 - last 256 bytes
            offset = io2_ram_base + (addr - IO2_START)
            self.ram[offset] = data


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
    1: ActionReplayCartridge,
}


def create_cartridge(
    hardware_type: int,
    roml_data: Optional[bytes] = None,
    romh_data: Optional[bytes] = None,
    ultimax_romh_data: Optional[bytes] = None,
    banks: Optional[list[bytes]] = None,
    name: str = "",
) -> Cartridge:
    """Factory function to create appropriate cartridge instance.

    Args:
        hardware_type: CRT hardware type ID
        roml_data: ROM data for ROML region ($8000-$9FFF) - for type 0
        romh_data: ROM data for ROMH region ($A000-$BFFF) - for type 0 16KB mode
        ultimax_romh_data: ROM data for Ultimax ROMH ($E000-$FFFF) - for type 0
        banks: List of ROM banks - for banked cartridges (type 1+)
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
        return StaticROMCartridge(roml_data, romh_data, ultimax_romh_data, name)
    elif cart_class == ActionReplayCartridge:
        if banks is None:
            raise ValueError("ActionReplayCartridge requires banks parameter")
        return ActionReplayCartridge(banks, name)
    else:
        raise ValueError(f"Cartridge type {hardware_type} not yet implemented")
