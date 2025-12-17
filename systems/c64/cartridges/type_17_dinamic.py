"""Type 17: Dinamic cartridge with bank switching.

CRT hardware type 17. Dinamic cartridges are functionally similar to
Ocean Type 1 cartridges but with a 4-bit bank select (max 16 banks).
"""


from mos6502.compat import logging

from .base import CartridgeVariant, CartridgeImage, ROML_START, ROML_SIZE
from .rom_builder import TestROMBuilder
from .type_05_ocean import OceanType1Cartridge
from c64.colors import COLOR_BLUE, COLOR_YELLOW, COLOR_WHITE
from mos6502.compat import List

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

    # --- Test cartridge generation ---

    # Bank select register and signature location
    BANK_SELECT_ADDR = 0xDE00
    SIGNATURE_ADDR = 0x9FF5  # Each bank has its bank number here

    @classmethod
    def get_cartridge_variants(cls) -> List[CartridgeVariant]:
        """Return all valid configuration variants for Type 17."""
        return [
            CartridgeVariant("128k", exrom=0, game=1, extra={"bank_count": 16}),
        ]

    @classmethod
    def create_test_cartridge(cls, variant: CartridgeVariant) -> CartridgeImage:
        """Create test cartridge image for Dinamic.

        Uses a RAM-based bank switch routine because we can't switch banks
        while executing from the ROM being switched.
        """
        bank_count = variant.extra.get("bank_count", 16)

        # Bank 0: Main test code
        builder = TestROMBuilder(base_address=ROML_START)

        builder.emit_screen_init()
        builder.emit_set_border_and_background(COLOR_BLUE)
        builder.emit_display_text("TYPE 17 DINAMIC", line=0, color=COLOR_WHITE)
        builder.emit_display_text(f"EXROM=0 GAME=1 {bank_count}x8K", line=1, color=COLOR_YELLOW)
        builder.current_line = 3

        # Install the bank-switch routine in RAM at $C000
        builder.emit_install_bank_switch_routine(
            bank_select_addr=cls.BANK_SELECT_ADDR,
            signature_addr=cls.SIGNATURE_ADDR,
        )

        # Test each bank by calling the RAM routine
        test_banks = [0, 1, 8, bank_count - 1]
        for test_bank in test_banks:
            test_id = builder.start_test(f"BANK {test_bank} SIGNATURE")
            builder.emit_call_bank_switch(test_bank)
            builder.emit_check_a_equals(test_bank, f"{test_id}_fail")
            builder.emit_pass_result(test_id)
            builder.emit_fail_result(test_id)

        builder.emit_final_status(hardware_type=17, type_name="DINAMIC")

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
