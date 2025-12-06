"""Type 17: Dinamic cartridge with bank switching.

CRT hardware type 17. Dinamic cartridges are functionally similar to
Ocean Type 1 cartridges but with a 4-bit bank select (max 16 banks).
"""

from __future__ import annotations

import logging

from .type_05_ocean import OceanType1Cartridge

log = logging.getLogger("c64.cartridge")


class DinamicCartridge(OceanType1Cartridge):
    """Type 17: Dinamic cartridge with bank switching.

    CRT hardware type 17. Dinamic cartridges are functionally identical to
    Ocean Type 1 cartridges. They typically use 128KB ROM organized as
    16 x 8KB banks with bank selection via $DE00.

    Control register at $DE00 (write only):
        Bits 0-3: Bank number (0-15 for 128KB)
        Bits 4-7: Unused

    Memory mapping:
        - ROML ($8000-$9FFF): Selected 8KB bank

    Initial state: 8KB mode with bank 0 (EXROM=0, GAME=1)

    Games using this format:
        - Narco Police, Mega Phoenix, etc.

    References:
        - VICE dinamic.c
        - https://vice-emu.sourceforge.io/vice_17.html
    """

    HARDWARE_TYPE = 17

    def write_io1(self, addr: int, data: int) -> None:
        """Write to IO1 region ($DE00-$DEFF) - bank select register.

        Any write to $DE00-$DEFF selects a bank. Bits 0-3 select
        the bank number (0-15). The bank is masked to the actual
        number of banks available.
        """
        # Bits 0-3 select bank for Dinamic (max 16 banks = 128KB)
        bank = data & 0x0F
        if self.num_banks > 0:
            self.current_bank = bank % self.num_banks
        else:
            self.current_bank = 0

        log.debug(f"Dinamic: Bank select ${data:02X} -> bank {self.current_bank}")
