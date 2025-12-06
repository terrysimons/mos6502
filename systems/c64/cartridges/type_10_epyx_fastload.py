"""Type 10: Epyx FastLoad cartridge.

CRT hardware type 10. The Epyx FastLoad is a disk speedup utility
cartridge that uses a capacitor-based enable/disable mechanism.
"""

from __future__ import annotations

import logging

from .base import Cartridge, ROML_START, ROML_SIZE, IO2_START

log = logging.getLogger("c64.cartridge")


class EpyxFastloadCartridge(Cartridge):
    """Type 10: Epyx FastLoad cartridge.

    CRT hardware type 10. The Epyx FastLoad is an 8KB utility cartridge
    that speeds up disk loading. It uses a clever capacitor-based
    enable/disable mechanism:

    - Reading from ROML or IO1 "discharges" the capacitor, enabling the cart
    - After ~512 cycles without ROML/IO1 access, the cart disables
    - IO2 ($DF00-$DFFF) ALWAYS shows the last 256 bytes of ROM

    The IO2 region contains stub code that re-enables the main ROM by
    accessing IO1, then jumps to the main routines in ROML.

    Memory mapping:
        - ROML ($8000-$9FFF): 8KB ROM when enabled
        - IO2 ($DF00-$DFFF): Last 256 bytes of ROM (always visible)

    Control mechanism:
        - Read from ROML: Enables cartridge, resets timeout
        - Read from IO1: Enables cartridge, resets timeout
        - Timeout (~512 cycles): Disables cartridge

    When enabled: EXROM=0, GAME=1 (8KB mode)
    When disabled: EXROM=1, GAME=1 (IO2 still visible)

    References:
        - VICE epyxfastload.c
        - https://rr.c64.org/wiki/Epyx_FastLoad
    """

    HARDWARE_TYPE = 10
    BANK_SIZE = ROML_SIZE  # 8KB ROM

    # Timeout in CPU cycles before cartridge disables
    # Real hardware uses ~10ms capacitor, we use a shorter cycle count
    # VICE uses 512 cycles
    TIMEOUT_CYCLES = 512

    def __init__(self, rom_data: bytes, name: str = ""):
        """Initialize Epyx FastLoad cartridge.

        Args:
            rom_data: 8KB ROM data
            name: Cartridge name
        """
        super().__init__(rom_data, name)

        self.rom_data = rom_data
        self._cycles_since_access = 0
        self._enabled = True

        # Start in 8KB mode (enabled)
        self._exrom = False  # Active (low)
        self._game = True    # Inactive (high) = 8KB mode

        log.debug(
            f"EpyxFastloadCartridge: {len(rom_data)} bytes, "
            f"EXROM={1 if self._exrom else 0}, GAME={1 if self._game else 0}"
        )

    def reset(self) -> None:
        """Reset cartridge to initial state."""
        self._cycles_since_access = 0
        self._enabled = True
        self._exrom = False
        self._game = True

    def _enable_cartridge(self) -> None:
        """Enable the cartridge (discharge capacitor)."""
        if not self._enabled:
            log.debug("EpyxFastload: Cartridge enabled")
        self._enabled = True
        self._exrom = False  # 8KB mode
        self._cycles_since_access = 0

    def _disable_cartridge(self) -> None:
        """Disable the cartridge (capacitor charged)."""
        if self._enabled:
            log.debug("EpyxFastload: Cartridge disabled (timeout)")
        self._enabled = False
        self._exrom = True  # Cartridge invisible (except IO2)

    def tick(self, cycles: int = 1) -> None:
        """Called each CPU cycle to handle timeout.

        Args:
            cycles: Number of cycles elapsed
        """
        if self._enabled:
            self._cycles_since_access += cycles
            if self._cycles_since_access >= self.TIMEOUT_CYCLES:
                self._disable_cartridge()

    def read_roml(self, addr: int) -> int:
        """Read from ROML region ($8000-$9FFF).

        Reading from ROML enables the cartridge (discharges capacitor).
        """
        # Reading ROML enables the cartridge
        self._enable_cartridge()

        if not self._enabled:
            return 0xFF

        offset = addr - ROML_START
        if offset < len(self.rom_data):
            return self.rom_data[offset]
        return 0xFF

    def read_io1(self, addr: int) -> int:
        """Read from IO1 region ($DE00-$DEFF).

        Reading from IO1 enables the cartridge (discharges capacitor).
        Returns open bus (no actual register here).
        """
        # Reading IO1 enables the cartridge
        self._enable_cartridge()
        return 0xFF  # Open bus

    def read_io2(self, addr: int) -> int:
        """Read from IO2 region ($DF00-$DFFF).

        IO2 ALWAYS shows the last 256 bytes of ROM, regardless of
        whether the cartridge is enabled or disabled. This is the
        clever trick that allows the stub code to re-enable the
        main ROM.
        """
        # IO2 maps to last 256 bytes of ROM ($1F00-$1FFF)
        # This is ALWAYS visible, even when cartridge is disabled
        rom_offset = 0x1F00 + (addr - IO2_START)
        if rom_offset < len(self.rom_data):
            return self.rom_data[rom_offset]
        return 0xFF
