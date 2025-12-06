"""Type 19: Magic Desk / Domark / HES Australia cartridge.

CRT hardware type 19. Magic Desk cartridges support up to 512KB ROM
organized as up to 64 x 8KB banks.
"""

from __future__ import annotations

import logging

from .base import Cartridge, ROML_START, ROML_SIZE

log = logging.getLogger("c64.cartridge")


class MagicDeskCartridge(Cartridge):
    """Type 19: Magic Desk / Domark / HES Australia cartridge.

    CRT hardware type 19. Magic Desk cartridges support up to 512KB ROM
    organized as up to 64 x 8KB banks. Bank selection and cartridge
    disable are controlled via $DE00.

    Control register at $DE00 (write only):
        Bits 0-5: Bank number (0-63)
        Bit 6: Unused
        Bit 7: Disable cartridge (1 = disable until reset)

    Memory mapping:
        - ROML ($8000-$9FFF): Selected 8KB bank

    When bit 7 is set, the cartridge is disabled (EXROM goes high),
    making RAM visible at $8000-$9FFF. The cartridge remains disabled
    until a hardware reset.

    Common ROM sizes:
        - 32KB = 4 banks (original Magic Desk)
        - 64KB = 8 banks
        - 128KB = 16 banks
        - 256KB = 32 banks (uses 74LS174 6-bit register)
        - 512KB = 64 banks (extended Magic Desk)

    Initial state: 8KB mode with bank 0 (EXROM=0, GAME=1)

    Games/software using this format:
        - Magic Desk I, Ghosbusters, Badlands, Vindicators,
        - HES games, Domark games, many others

    References:
        - https://www.hackup.net/2019/07/bank-switching-cartridges/
        - https://github.com/msolajic/c64-magic-desk-512k
        - VICE magicdesk.c
    """

    HARDWARE_TYPE = 19
    BANK_SIZE = ROML_SIZE  # 8KB banks

    def __init__(self, banks: list[bytes], name: str = ""):
        """Initialize Magic Desk cartridge.

        Args:
            banks: List of 8KB ROM banks (4, 8, 16, 32, or 64 banks typical)
            name: Cartridge name
        """
        # Combine all banks for base class
        all_rom = b"".join(banks)
        super().__init__(all_rom, name)

        self.banks = banks
        self.num_banks = len(banks)
        self.current_bank = 0
        self.cartridge_disabled = False

        # Magic Desk uses 8KB mode (EXROM=0, GAME=1)
        self._exrom = False  # Active (low)
        self._game = True    # Inactive (high) = 8KB mode

        log.debug(
            f"MagicDeskCartridge: {self.num_banks} banks ({self.num_banks * 8}KB), "
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

    def write_io1(self, addr: int, data: int) -> None:
        """Write to IO1 region ($DE00-$DEFF) - bank select/disable register.

        Any write to $DE00-$DEFF controls the cartridge:
        - Bits 0-5: Select bank number (0-63)
        - Bit 7: Disable cartridge until reset

        Once disabled (bit 7 set), writes are ignored until reset.
        Ref: https://www.hackup.net/2019/07/bank-switching-cartridges/
        """
        # Once disabled, ignore all writes until reset
        if self.cartridge_disabled:
            return

        # Bit 7: Disable cartridge
        if data & 0x80:
            self.cartridge_disabled = True
            self._exrom = True  # EXROM high = cartridge invisible
            log.debug("MagicDesk: Cartridge disabled")
            return

        # Bits 0-5: Bank selection (mask to actual bank count)
        bank = data & 0x3F
        if self.num_banks > 0:
            self.current_bank = bank % self.num_banks
        else:
            self.current_bank = 0

        log.debug(f"MagicDesk: Bank select ${data:02X} -> bank {self.current_bank}")
