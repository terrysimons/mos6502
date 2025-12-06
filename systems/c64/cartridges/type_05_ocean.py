"""Type 5: Ocean Type 1 cartridge with bank switching.

CRT hardware type 5. Ocean Type 1 cartridges support up to 512KB ROM
organized as up to 64 x 8KB banks.
"""

from __future__ import annotations

import logging

from .base import Cartridge, ROML_START, ROML_SIZE, ROMH_START

log = logging.getLogger("c64.cartridge")


class OceanType1Cartridge(Cartridge):
    """Type 5: Ocean Type 1 cartridge with bank switching.

    CRT hardware type 5. Ocean Type 1 cartridges support up to 512KB ROM
    organized as up to 64 x 8KB banks. Bank selection is via $DE00.

    Control register at $DE00 (write only):
        Bits 0-5: Bank number (0-63)
        Bits 6-7: Unused

    Memory mapping:
        - ROML ($8000-$9FFF): Selected 8KB bank
        - ROMH ($A000-$BFFF): Same bank (in 16KB mode, for larger games)

    The actual number of banks depends on the ROM size:
        - 128KB = 16 banks
        - 256KB = 32 banks
        - 512KB = 64 banks

    Initial state: 8KB mode with bank 0 (EXROM=0, GAME=1)
    Some 256KB+ games use 16KB mode (EXROM=0, GAME=0)

    Games using this format:
        - Batman The Movie, Double Dragon, Navy SEALs, Pang,
        - Robocop 2, Robocop 3, Shadow of the Beast, Space Gun, etc.

    References:
        - VICE ocean.c
        - https://vice-emu.sourceforge.io/vice_17.html#SEC406
    """

    HARDWARE_TYPE = 5
    BANK_SIZE = ROML_SIZE  # 8KB banks

    def __init__(self, banks: list[bytes], name: str = "", use_16kb_mode: bool = False):
        """Initialize Ocean Type 1 cartridge.

        Args:
            banks: List of 8KB ROM banks (16, 32, or 64 banks typical)
            name: Cartridge name
            use_16kb_mode: If True, use 16KB mode (GAME=0) for ROMH access
        """
        # Combine all banks for base class
        all_rom = b"".join(banks)
        super().__init__(all_rom, name)

        self.banks = banks
        self.num_banks = len(banks)
        self.current_bank = 0

        # Ocean typically uses 8KB mode (EXROM=0, GAME=1)
        # Larger games may use 16KB mode (EXROM=0, GAME=0)
        self._exrom = False  # Active (low)
        self._game = not use_16kb_mode  # True for 8KB, False for 16KB

        log.debug(
            f"OceanType1Cartridge: {self.num_banks} banks ({self.num_banks * 8}KB), "
            f"EXROM={1 if self._exrom else 0}, GAME={1 if self._game else 0}"
        )

    def reset(self) -> None:
        """Reset cartridge to initial state."""
        self.current_bank = 0

    def read_roml(self, addr: int) -> int:
        """Read from ROML region ($8000-$9FFF)."""
        offset = addr - ROML_START

        if self.current_bank < self.num_banks:
            bank_data = self.banks[self.current_bank]
            if offset < len(bank_data):
                return bank_data[offset]
        return 0xFF

    def read_romh(self, addr: int) -> int:
        """Read from ROMH region ($A000-$BFFF).

        In 16KB mode, ROMH shows the same bank as ROML.
        """
        if self._game:  # 8KB mode - no ROMH
            return 0xFF

        # 16KB mode - ROMH mirrors current bank
        offset = addr - ROMH_START

        if self.current_bank < self.num_banks:
            bank_data = self.banks[self.current_bank]
            if offset < len(bank_data):
                return bank_data[offset]
        return 0xFF

    def write_io1(self, addr: int, data: int) -> None:
        """Write to IO1 region ($DE00-$DEFF) - bank select register.

        Any write to $DE00-$DEFF selects a bank. Bits 0-5 select
        the bank number (0-63). The bank is masked to the actual
        number of banks available.
        """
        # Bits 0-5 select bank (mask to actual bank count)
        bank = data & 0x3F
        if self.num_banks > 0:
            self.current_bank = bank % self.num_banks
        else:
            self.current_bank = 0

        log.debug(f"Ocean: Bank select ${data:02X} -> bank {self.current_bank}")
