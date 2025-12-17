"""Type 19: Magic Desk / Domark / HES Australia cartridge.

CRT hardware type 19. Magic Desk cartridges support up to 512KB ROM
organized as up to 64 x 8KB banks.
"""


from mos6502.compat import logging

from .base import Cartridge, CartridgeVariant, CartridgeImage, ROML_START, ROML_SIZE
from .rom_builder import TestROMBuilder
from c64.colors import COLOR_BLUE, COLOR_YELLOW, COLOR_WHITE
from mos6502.compat import List

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

    def __init__(self, banks: List[bytes], name: str = ""):
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

    # --- Test cartridge generation ---

    # Bank select register and signature location
    BANK_SELECT_ADDR = 0xDE00
    SIGNATURE_ADDR = 0x9FF5  # Each bank has its bank number here

    @classmethod
    def get_cartridge_variants(cls) -> List[CartridgeVariant]:
        """Return all valid configuration variants for Type 19."""
        return [
            CartridgeVariant("32k", exrom=0, game=1, extra={"bank_count": 4}),
            CartridgeVariant("64k", exrom=0, game=1, extra={"bank_count": 8}),
            CartridgeVariant("128k", exrom=0, game=1, extra={"bank_count": 16}),
            CartridgeVariant("256k", exrom=0, game=1, extra={"bank_count": 32}),
            CartridgeVariant("512k", exrom=0, game=1, extra={"bank_count": 64}),
        ]

    @classmethod
    def create_test_cartridge(cls, variant: CartridgeVariant) -> CartridgeImage:
        """Create test cartridge image for Magic Desk.

        Uses a RAM-based bank switch routine because we can't switch banks
        while executing from the ROM being switched.
        """
        bank_count = variant.extra.get("bank_count", 4)

        # Bank 0: Main test code
        builder = TestROMBuilder(base_address=ROML_START)

        builder.emit_screen_init()
        builder.emit_set_border_and_background(COLOR_BLUE)
        builder.emit_display_text("TYPE 19 MAGIC DESK", line=0, color=COLOR_WHITE)
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

        builder.emit_final_status(hardware_type=19, type_name="MAGIC DESK")

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
