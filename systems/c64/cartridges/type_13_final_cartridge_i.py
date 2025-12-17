"""Type 13: Final Cartridge I.

CRT hardware type 13. The Final Cartridge I is a simple 16KB utility
cartridge with IO-based enable/disable mechanism.
"""


from mos6502.compat import logging

from .base import (
    Cartridge,
    CartridgeVariant,
    CartridgeImage,
    ROML_START,
    ROML_SIZE,
    ROMH_START,
    ROMH_SIZE,
)
from .rom_builder import TestROMBuilder
from c64.colors import COLOR_BLUE, COLOR_YELLOW, COLOR_WHITE
from mos6502.compat import List, Union

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
        romh_data: Union[bytes, None]= None,
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

    # --- Test cartridge generation ---

    @classmethod
    def get_cartridge_variants(cls) -> List[CartridgeVariant]:
        """Return all valid configuration variants for Type 13."""
        return [
            CartridgeVariant("", exrom=0, game=0),  # 16KB mode
        ]

    @classmethod
    def create_test_cartridge(cls, variant: CartridgeVariant) -> CartridgeImage:
        """Create test cartridge image for Final Cartridge I."""
        builder = TestROMBuilder(base_address=ROML_START)

        builder.emit_screen_init()
        builder.emit_set_border_and_background(COLOR_BLUE)
        builder.emit_display_text("TYPE 13 FINAL CART I", line=0, color=COLOR_WHITE)
        builder.emit_display_text("EXROM=0 GAME=0 16KB", line=1, color=COLOR_YELLOW)
        builder.current_line = 3

        # Test 1: ROML is visible at $8000
        test1 = builder.start_test("ROML AT $8000")
        builder.emit_check_byte(0x9FF0, ord('R'), f"{test1}_fail")
        builder.emit_check_byte(0x9FF1, ord('L'), f"{test1}_fail")
        builder.emit_pass_result(test1)
        builder.emit_fail_result(test1)

        # Test 2: ROMH is visible at $A000
        test2 = builder.start_test("ROMH AT $A000")
        builder.emit_check_byte(0xBFF0, ord('R'), f"{test2}_fail")
        builder.emit_check_byte(0xBFF1, ord('H'), f"{test2}_fail")
        builder.emit_pass_result(test2)
        builder.emit_fail_result(test2)

        # Test 3: IO1 access disables cart, IO2 re-enables
        test3 = builder.start_test("IO1/IO2 TOGGLE")
        # Write to IO2 to ensure cart is enabled
        builder.emit_write_byte(0xDF00, 0x00)
        builder.emit_check_byte(0x9FF0, ord('R'), f"{test3}_fail")
        # Note: Can't test disable easily since code is in ROM - if disabled,
        # code would crash. Just test that IO2 keeps it enabled.
        builder.emit_pass_result(test3)
        builder.emit_fail_result(test3)

        builder.emit_final_status(hardware_type=13, type_name="FINAL CART I")

        # Build ROMs
        roml_data = bytearray(builder.build_rom())
        roml_data[0x1FF0:0x1FF8] = b"RL-SIGN!"  # ROML signature

        romh_data = bytearray(ROMH_SIZE)
        romh_data[0x1FF0:0x1FF8] = b"RH-SIGN!"  # ROMH signature

        return CartridgeImage(
            description=variant.description,
            exrom=variant.exrom,
            game=variant.game,
            extra=variant.extra,
            rom_data={"roml": bytes(roml_data), "romh": bytes(romh_data)},
            hardware_type=cls.HARDWARE_TYPE,
        )
