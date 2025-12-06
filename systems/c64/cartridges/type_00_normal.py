"""Type 0: Static ROM cartridge with no bank switching.

CRT hardware type 0 (called "Normal cartridge" in VICE/CCS64 spec).
The simplest cartridge type where ROM is directly mapped to fixed
addresses with no banking hardware.
"""

from __future__ import annotations

import logging
from typing import Optional

from .base import (
    Cartridge,
    ROML_START,
    ROML_SIZE,
    ROMH_START,
    ULTIMAX_ROMH_START,
)

log = logging.getLogger("c64.cartridge")


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
