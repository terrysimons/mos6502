"""Type 10: Epyx FastLoad cartridge.

CRT hardware type 10. The Epyx FastLoad is a disk speedup utility
cartridge that uses a capacitor-based enable/disable mechanism.
"""


from mos6502.compat import logging

from .base import Cartridge, CartridgeVariant, CartridgeImage, ROML_START, ROML_SIZE, IO2_START
# Test ROM builder - optional for MicroPython/Pico
try:
    from .rom_builder import TestROMBuilder
except ImportError:
    TestROMBuilder = None
from c64.colors import COLOR_BLUE, COLOR_YELLOW, COLOR_WHITE
from mos6502.compat import List

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

    # --- Test cartridge generation ---

    @classmethod
    def get_cartridge_variants(cls) -> List[CartridgeVariant]:
        """Return all valid configuration variants for Type 10."""
        return [
            CartridgeVariant("", 0, 1),  # 8KB mode
        ]

    @classmethod
    def create_test_cartridge(cls, variant: CartridgeVariant) -> CartridgeImage:
        """Create test cartridge image for Epyx FastLoad."""
        builder = TestROMBuilder(base_address=ROML_START)

        builder.emit_screen_init()
        builder.emit_set_border_and_background(COLOR_BLUE)
        builder.emit_display_text("TYPE 10 EPYX FASTLOAD", line=0, color=COLOR_WHITE)
        builder.emit_display_text("EXROM=0 GAME=1 8KB", line=1, color=COLOR_YELLOW)
        builder.current_line = 3

        # Test 1: ROML is visible at $8000 (check at $8FF0, not in IO2 mirror area)
        test1 = builder.start_test("ROML AT $8000")
        builder.emit_check_byte(0x8FF0, ord('R'), f"{test1}_fail")
        builder.emit_check_byte(0x8FF1, ord('L'), f"{test1}_fail")
        builder.emit_pass_result(test1)
        builder.emit_fail_result(test1)

        # Test 2: IO2 mirrors last 256 bytes of ROM ($1F00-$1FFF -> $DF00-$DFFF)
        test2 = builder.start_test("IO2 MIRRORS $1F00")
        builder.emit_check_byte(0xDFF0, ord('I'), f"{test2}_fail")
        builder.emit_check_byte(0xDFF1, ord('O'), f"{test2}_fail")
        builder.emit_pass_result(test2)
        builder.emit_fail_result(test2)

        # Test 3: IO1 read should keep cart enabled (tests enable mechanism)
        # Note: Can't easily test timeout without cycle-accurate simulation
        test3 = builder.start_test("IO1 READ $DE00")
        # Read IO1 (which keeps cart enabled), then verify ROML still works
        builder.emit_bytes([
            0xAD, 0x00, 0xDE,  # LDA $DE00 - read IO1 to keep cart enabled
        ])
        builder.emit_check_byte(0x8FF0, ord('R'), f"{test3}_fail")
        builder.emit_pass_result(test3)
        builder.emit_fail_result(test3)

        builder.emit_final_status(hardware_type=10, type_name="EPYX FASTLOAD")

        # Build ROM with signatures
        rom_data = bytearray(builder.build_rom())
        # ROML signature at $0FF0 (maps to $8FF0, outside IO2 mirror area)
        rom_data[0x0FF0:0x0FF8] = b"RL-SIGN!"
        # IO2 signature at $1FF0 (maps to $DFF0 via IO2 mirror)
        rom_data[0x1FF0:0x1FF8] = b"IO-SIGN!"

        # CartridgeImage field order: description, exrom, game, extra, rom_data, hardware_type
        return CartridgeImage(
            variant.description, variant.exrom, variant.game, variant.extra,
            {"roml": bytes(rom_data)}, cls.HARDWARE_TYPE
        )
