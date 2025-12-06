"""Type 15: C64 Game System / System 3 cartridge.

CRT hardware type 15. C64GS cartridges support up to 512KB ROM
organized as up to 64 x 8KB banks.
"""

from __future__ import annotations

import logging

from .base import Cartridge, ROML_START, ROML_SIZE

log = logging.getLogger("c64.cartridge")


class C64GSCartridge(Cartridge):
    """Type 15: C64 Game System / System 3 cartridge.

    CRT hardware type 15. C64GS cartridges support up to 512KB ROM
    organized as up to 64 x 8KB banks. Bank selection is controlled
    via writes to $DE00, and the cartridge is disabled by reads
    from the IO1 area ($DE00-$DEFF).

    Control mechanism:
        Write to $DE00: bits 0-5 select bank (0-63)
        Read from $DE00-$DEFF: Disables cartridge until reset

    Memory mapping:
        - ROML ($8000-$9FFF): Selected 8KB bank

    This is similar to Magic Desk, but the disable mechanism differs:
    - Magic Desk: Write with bit 7 set disables
    - C64GS: Any READ from IO1 disables

    Initial state: 8KB mode with bank 0 (EXROM=0, GAME=1)

    Games using this format:
        - C64 Game System titles (Last Ninja, Myth, etc.)
        - System 3 games

    References:
        - VICE c64gs.c
        - https://vice-emu.sourceforge.io/
    """

    HARDWARE_TYPE = 15
    BANK_SIZE = ROML_SIZE  # 8KB banks

    def __init__(self, banks: list[bytes], name: str = ""):
        """Initialize C64GS cartridge.

        Args:
            banks: List of 8KB ROM banks (up to 64 banks)
            name: Cartridge name
        """
        # Combine all banks for base class
        all_rom = b"".join(banks)
        super().__init__(all_rom, name)

        self.banks = banks
        self.num_banks = len(banks)
        self.current_bank = 0
        self.cartridge_disabled = False

        # C64GS uses 8KB mode (EXROM=0, GAME=1)
        self._exrom = False  # Active (low)
        self._game = True    # Inactive (high) = 8KB mode

        log.debug(
            f"C64GSCartridge: {self.num_banks} banks ({self.num_banks * 8}KB), "
            f"EXROM={1 if self._exrom else 0}, GAME={1 if self._game else 0}"
        )

    def reset(self) -> None:
        """Reset cartridge to initial state.

        Re-enables the cartridge if it was disabled.
        """
        self.current_bank = 0
        self.cartridge_disabled = False
        self._exrom = False
        self._game = True

    def read_roml(self, addr: int) -> int:
        """Read from ROML region ($8000-$9FFF)."""
        if self.cartridge_disabled:
            return 0xFF

        offset = addr - ROML_START

        if self.current_bank < self.num_banks:
            bank_data = self.banks[self.current_bank]
            if offset < len(bank_data):
                return bank_data[offset]
        return 0xFF

    def read_io1(self, addr: int) -> int:
        """Read from IO1 region ($DE00-$DEFF) - DISABLES the cartridge.

        Unlike Magic Desk which disables via a write with bit 7 set,
        C64GS disables when ANY read occurs in the IO1 range.
        Once disabled, the cartridge remains disabled until reset.
        """
        if not self.cartridge_disabled:
            self.cartridge_disabled = True
            self._exrom = True  # EXROM high = cartridge invisible
            log.debug("C64GS: Cartridge disabled by IO1 read")
        return 0xFF

    def write_io1(self, addr: int, data: int) -> None:
        """Write to IO1 region ($DE00-$DEFF) - bank select register.

        Bits 0-5: Select bank number (0-63)

        Once disabled, writes are ignored until reset.
        """
        # Once disabled, ignore all writes until reset
        if self.cartridge_disabled:
            return

        # Bits 0-5: Bank selection (mask to actual bank count)
        bank = data & 0x3F
        if self.num_banks > 0:
            self.current_bank = bank % self.num_banks
        else:
            self.current_bank = 0

        log.debug(f"C64GS: Bank select ${data:02X} -> bank {self.current_bank}")
