"""Type 13: Final Cartridge I.

CRT hardware type 13. The Final Cartridge I is a simple 16KB utility
cartridge with IO-based enable/disable mechanism.
"""

from __future__ import annotations

import logging

from .base import (
    Cartridge,
    ROML_START,
    ROML_SIZE,
    ROMH_START,
    ROMH_SIZE,
)

log = logging.getLogger("c64.cartridge")


class FinalCartridgeICartridge(Cartridge):
    """Type 13: Final Cartridge I.

    CRT hardware type 13. The FC1 is a simple 16KB utility cartridge
    that includes a fast loader, monitor, function key support, and
    DOS wedge.

    Control mechanism (very simple):
        - Any access to IO1 ($DE00-$DEFF) turns cartridge ROM OFF
        - Any access to IO2 ($DF00-$DFFF) turns cartridge ROM ON

    Memory mapping when enabled:
        ROML ($8000-$9FFF): First 8KB of ROM
        ROMH ($A000-$BFFF): Second 8KB of ROM (if present)

    Memory mapping when disabled:
        Cartridge ROM is invisible (EXROM=1, GAME=1)

    Hardware:
        - 16KB ROM (ROML + ROMH in 16KB mode)
        - Reset button
        - On/Off switch

    Initial state: Enabled (EXROM=0, GAME=0 for 16KB mode)

    Note: Some FC1 cartridges may only have 8KB ROM. In that case,
    the cart starts in 8KB mode (EXROM=0, GAME=1) and ROMH returns $FF.

    References:
        - VICE fc.c (covers FC1/FC2)
        - https://rr.pokefinder.org/wiki/Final_Cartridge
    """

    HARDWARE_TYPE = 13
    BANK_SIZE = ROML_SIZE + ROMH_SIZE  # Up to 16KB

    def __init__(
        self,
        roml_data: bytes,
        romh_data: bytes | None = None,
        name: str = "",
    ):
        """Initialize Final Cartridge I.

        Args:
            roml_data: 8KB ROM data for ROML region
            romh_data: Optional 8KB ROM data for ROMH region
            name: Cartridge name
        """
        # Combine ROM data for base class
        rom_data = roml_data
        if romh_data:
            rom_data = roml_data + romh_data

        super().__init__(rom_data, name)

        self.roml_data = roml_data
        self.romh_data = romh_data
        self._enabled = True

        # Determine mode based on ROM configuration
        if romh_data:
            # 16KB mode: EXROM=0, GAME=0
            self._exrom = False
            self._game = False
        else:
            # 8KB mode: EXROM=0, GAME=1
            self._exrom = False
            self._game = True

        log.debug(
            f"FinalCartridgeICartridge: ROML={len(roml_data)} bytes, "
            f"ROMH={len(romh_data) if romh_data else 0} bytes, "
            f"EXROM={1 if self._exrom else 0}, GAME={1 if self._game else 0}"
        )

    def reset(self) -> None:
        """Reset cartridge to initial state (enabled)."""
        self._enabled = True
        if self.romh_data:
            self._exrom = False
            self._game = False
        else:
            self._exrom = False
            self._game = True

    def _enable_cartridge(self) -> None:
        """Enable the cartridge ROM."""
        if not self._enabled:
            log.debug("FC1: Cartridge enabled")
        self._enabled = True
        self._exrom = False
        # Maintain original GAME state (8KB vs 16KB mode)
        if self.romh_data:
            self._game = False
        else:
            self._game = True

    def _disable_cartridge(self) -> None:
        """Disable the cartridge ROM."""
        if self._enabled:
            log.debug("FC1: Cartridge disabled")
        self._enabled = False
        self._exrom = True
        self._game = True  # Both high = no cartridge

    def read_roml(self, addr: int) -> int:
        """Read from ROML region ($8000-$9FFF)."""
        if not self._enabled:
            return 0xFF

        offset = addr - ROML_START
        if offset < len(self.roml_data):
            return self.roml_data[offset]
        return 0xFF

    def read_romh(self, addr: int) -> int:
        """Read from ROMH region ($A000-$BFFF)."""
        if not self._enabled:
            return 0xFF

        if self.romh_data is None:
            return 0xFF

        offset = addr - ROMH_START
        if offset < len(self.romh_data):
            return self.romh_data[offset]
        return 0xFF

    def read_io1(self, addr: int) -> int:
        """Read from IO1 region ($DE00-$DEFF).

        Any access to IO1 disables the cartridge ROM.
        """
        self._disable_cartridge()
        return 0xFF  # Open bus

    def write_io1(self, addr: int, data: int) -> None:
        """Write to IO1 region ($DE00-$DEFF).

        Any access to IO1 disables the cartridge ROM.
        """
        self._disable_cartridge()

    def read_io2(self, addr: int) -> int:
        """Read from IO2 region ($DF00-$DFFF).

        Any access to IO2 enables the cartridge ROM.
        """
        self._enable_cartridge()
        return 0xFF  # Open bus

    def write_io2(self, addr: int, data: int) -> None:
        """Write to IO2 region ($DF00-$DFFF).

        Any access to IO2 enables the cartridge ROM.
        """
        self._enable_cartridge()
