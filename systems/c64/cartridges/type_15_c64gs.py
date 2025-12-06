"""Type 15: C64 Game System / System 3 cartridge.

CRT hardware type 15. C64GS cartridges support up to 512KB ROM
organized as up to 64 x 8KB banks.
"""

from __future__ import annotations

import logging

from .base import Cartridge, CartridgeVariant, CartridgeImage, ROML_START, ROML_SIZE
from .rom_builder import TestROMBuilder
from c64.colors import COLOR_BLUE, COLOR_YELLOW, COLOR_WHITE

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

    # --- Test cartridge generation ---

    # Bank select register and signature location
    BANK_SELECT_ADDR = 0xDE00
    SIGNATURE_ADDR = 0x9FF5  # Each bank has its bank number here

    @classmethod
    def get_cartridge_variants(cls) -> list[CartridgeVariant]:
        """Return all valid configuration variants for Type 15."""
        return [
            CartridgeVariant("64k", exrom=0, game=1, extra={"bank_count": 8}),
            CartridgeVariant("128k", exrom=0, game=1, extra={"bank_count": 16}),
            CartridgeVariant("512k", exrom=0, game=1, extra={"bank_count": 64}),
        ]

    @classmethod
    def create_test_cartridge(cls, variant: CartridgeVariant) -> CartridgeImage:
        """Create test cartridge image for C64 Game System.

        Uses a RAM-based bank switch routine because we can't switch banks
        while executing from the ROM being switched.
        """
        bank_count = variant.extra.get("bank_count", 8)

        # Bank 0: Main test code
        builder = TestROMBuilder(base_address=ROML_START)

        builder.emit_screen_init()
        builder.emit_set_border_and_background(COLOR_BLUE)
        builder.emit_display_text("TYPE 15 C64GS", line=0, color=COLOR_WHITE)
        builder.emit_display_text(f"EXROM=0 GAME=1 {bank_count}x8K", line=1, color=COLOR_YELLOW)
        builder.current_line = 3

        # Install the bank-switch routine in RAM at $C000
        builder.emit_install_bank_switch_routine(
            bank_select_addr=cls.BANK_SELECT_ADDR,
            signature_addr=cls.SIGNATURE_ADDR,
        )

        # Test each bank by calling the RAM routine
        test_banks = [0, 1, 2, bank_count - 1]
        for test_bank in test_banks:
            test_id = builder.start_test(f"BANK {test_bank} SIGNATURE")
            builder.emit_call_bank_switch(test_bank)
            builder.emit_check_a_equals(test_bank, f"{test_id}_fail")
            builder.emit_pass_result(test_id)
            builder.emit_fail_result(test_id)

        builder.emit_final_status(hardware_type=15, type_name="C64GS")

        # Build banks
        banks = []

        # Bank 0: Test code with signature
        bank0 = bytearray(builder.build_rom())
        bank0[0x1FF5] = 0  # Bank 0 signature
        banks.append(bytes(bank0))

        # Banks 1 through bank_count-1: Each has its bank number at $9FF5
        for i in range(1, bank_count):
            bank = bytearray(ROML_SIZE)
            bank[0x1FF5] = i  # Bank number as signature
            banks.append(bytes(bank))

        return CartridgeImage(
            description=variant.description,
            exrom=variant.exrom,
            game=variant.game,
            extra=variant.extra,
            rom_data={"banks": banks},
            hardware_type=cls.HARDWARE_TYPE,
        )
