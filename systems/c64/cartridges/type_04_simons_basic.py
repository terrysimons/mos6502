"""Type 4: Simons' BASIC cartridge with ROMH toggle.

CRT hardware type 4. A simple 16KB cartridge that extends Commodore BASIC
with additional commands.
"""

from __future__ import annotations

import logging

from .base import Cartridge, ROML_START, ROMH_START

log = logging.getLogger("c64.cartridge")


class SimonsBasicCartridge(Cartridge):
    """Type 4: Simons' BASIC cartridge with ROMH toggle.

    CRT hardware type 4. A simple 16KB cartridge that extends Commodore BASIC
    with additional commands. The cartridge has ROML (always visible) and
    ROMH (toggled via I/O writes).

    Memory mapping:
        - ROML ($8000-$9FFF): 8KB ROM, always visible when cartridge active
        - ROMH ($A000-$BFFF): 8KB ROM, can be toggled on/off

    Control:
        - Write to $DE00: Enable ROMH (16KB mode, GAME=0)
        - Write to $DF00: Disable ROMH (8KB mode, GAME=1)

    Initial state: 8KB mode (ROMH disabled, EXROM=0, GAME=1)

    This allows the extended BASIC commands to switch between showing
    the ROMH extension and the normal C64 BASIC ROM at $A000-$BFFF.

    References:
        - VICE simon.c
        - https://vice-emu.sourceforge.io/vice_17.html#SEC391
    """

    HARDWARE_TYPE = 4

    def __init__(self, roml_data: bytes, romh_data: bytes, name: str = ""):
        """Initialize Simons' BASIC cartridge.

        Args:
            roml_data: 8KB ROM data for ROML region ($8000-$9FFF)
            romh_data: 8KB ROM data for ROMH region ($A000-$BFFF)
            name: Cartridge name
        """
        # Combine ROM data for base class
        all_rom = roml_data + romh_data
        super().__init__(all_rom, name)

        self.roml_data = roml_data
        self.romh_data = romh_data

        # Initial state: 8KB mode (ROMH disabled)
        self._exrom = False  # Active (low)
        self._game = True    # Inactive (high) = 8KB mode, ROMH hidden
        self._romh_enabled = False

        log.debug(
            f"SimonsBasicCartridge: ROML={len(roml_data)}B, ROMH={len(romh_data)}B, "
            f"EXROM={1 if self._exrom else 0}, GAME={1 if self._game else 0}"
        )

    def reset(self) -> None:
        """Reset cartridge to initial state (8KB mode)."""
        self._game = True
        self._romh_enabled = False

    def read_roml(self, addr: int) -> int:
        """Read from ROML region ($8000-$9FFF)."""
        offset = addr - ROML_START
        if offset < len(self.roml_data):
            return self.roml_data[offset]
        return 0xFF

    def read_romh(self, addr: int) -> int:
        """Read from ROMH region ($A000-$BFFF).

        Only returns data when ROMH is enabled (16KB mode).
        """
        if not self._romh_enabled:
            return 0xFF
        offset = addr - ROMH_START
        if offset < len(self.romh_data):
            return self.romh_data[offset]
        return 0xFF

    def write_io1(self, addr: int, data: int) -> None:
        """Write to IO1 region ($DE00-$DEFF).

        Any write to $DE00 enables ROMH (16KB mode).
        """
        # Enable ROMH - switch to 16KB mode
        self._game = False  # GAME=0 = 16KB mode
        self._romh_enabled = True
        log.debug("SimonsBasic: ROMH enabled (16KB mode)")

    def write_io2(self, addr: int, data: int) -> None:
        """Write to IO2 region ($DF00-$DFFF).

        Any write to $DF00 disables ROMH (8KB mode).
        """
        # Disable ROMH - switch to 8KB mode
        self._game = True  # GAME=1 = 8KB mode
        self._romh_enabled = False
        log.debug("SimonsBasic: ROMH disabled (8KB mode)")
