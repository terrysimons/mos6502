"""Type 1: Action Replay cartridge with bank switching.

CRT hardware type 1. The Action Replay is a freezer cartridge with
32KB ROM organized as 4 x 8KB banks, plus 8KB RAM.
"""

from __future__ import annotations

import logging

from .base import (
    Cartridge,
    ROML_START,
    ROML_SIZE,
    ROMH_START,
    IO2_START,
)

log = logging.getLogger("c64.cartridge")


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

    def write_roml(self, addr: int, data: int) -> bool:
        """Write to ROML region ($8000-$9FFF).

        When RAM is enabled (bit 5 of control register), writes go to
        the cartridge's 8KB RAM instead of the C64's RAM.
        """
        if self.cartridge_disabled:
            return False

        if self.ram_enabled:
            offset = addr - ROML_START
            self.ram[offset] = data
            return True  # Write handled by cartridge

        return False  # Write goes to C64 RAM

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
