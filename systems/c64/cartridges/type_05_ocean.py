"""Type 5: Ocean Type 1 cartridge with bank switching.

CRT hardware type 5. Ocean Type 1 cartridges support up to 512KB ROM
organized as up to 64 x 8KB banks.
"""


from mos6502.compat import logging

from .base import Cartridge, CartridgeVariant, CartridgeImage, ROML_START, ROML_SIZE, ROMH_START
# Test ROM builder - optional for MicroPython/Pico
try:
    from .rom_builder import TestROMBuilder
except ImportError:
    TestROMBuilder = None
from c64.colors import COLOR_BLUE, COLOR_YELLOW, COLOR_WHITE
from mos6502.compat import List

log = logging.getLogger("c64.cartridge")


class OceanType1Cartridge(Cartridge):
    """Type 5: Ocean Type 1 cartridge with bank switching.

    CRT hardware type 5. Ocean Type 1 cartridges support up to 512KB ROM
    organized as up to 64 x 8KB banks. Bank selection is via $DE00.

    Control register at $DE00 (write only):
        Bits 0-5: Bank number (0-63)
        Bits 6-7: Unused

    Memory mapping:
        - ROML ($8000-$9FFF): Selected 8KB bank
        - ROMH ($A000-$BFFF): Same bank (in 16KB mode, for larger games)

    The actual number of banks depends on the ROM size:
        - 128KB = 16 banks
        - 256KB = 32 banks
        - 512KB = 64 banks

    Initial state: 8KB mode with bank 0 (EXROM=0, GAME=1)
    Some 256KB+ games use 16KB mode (EXROM=0, GAME=0)

    Games using this format:
        - Batman The Movie, Double Dragon, Navy SEALs, Pang,
        - Robocop 2, Robocop 3, Shadow of the Beast, Space Gun, etc.

    References:
        - VICE ocean.c
        - https://vice-emu.sourceforge.io/vice_17.html#SEC406
    """

    HARDWARE_TYPE = 5
    BANK_SIZE = ROML_SIZE  # 8KB banks

    def __init__(self, banks: List[bytes], name: str = "", use_16kb_mode: bool = False):
        """Initialize Ocean Type 1 cartridge.

        Args:
            banks: List of 8KB ROM banks (16, 32, or 64 banks typical)
            name: Cartridge name
            use_16kb_mode: If True, use 16KB mode (GAME=0) for ROMH access
        """
        # Combine all banks for base class
        all_rom = b"".join(banks)
        super().__init__(all_rom, name)

        self.banks = banks
        self.num_banks = len(banks)
        self.current_bank = 0

        # Ocean typically uses 8KB mode (EXROM=0, GAME=1)
        # Larger games may use 16KB mode (EXROM=0, GAME=0)
        self._exrom = False  # Active (low)
        self._game = not use_16kb_mode  # True for 8KB, False for 16KB

        log.debug(
            f"OceanType1Cartridge: {self.num_banks} banks ({self.num_banks * 8}KB), "
            f"EXROM={1 if self._exrom else 0}, GAME={1 if self._game else 0}"
        )

    def reset(self) -> None:
        """Reset cartridge to initial state."""
        self.current_bank = 0

    def read_roml(self, addr: int) -> int:
        """Read from ROML region ($8000-$9FFF)."""
        offset = addr - ROML_START

        if self.current_bank < self.num_banks:
            bank_data = self.banks[self.current_bank]
            if offset < len(bank_data):
                return bank_data[offset]
        return 0xFF

    def read_romh(self, addr: int) -> int:
        """Read from ROMH region ($A000-$BFFF).

        In 16KB mode, ROMH shows the same bank as ROML.
        """
        if self._game:  # 8KB mode - no ROMH
            return 0xFF

        # 16KB mode - ROMH mirrors current bank
        offset = addr - ROMH_START

        if self.current_bank < self.num_banks:
            bank_data = self.banks[self.current_bank]
            if offset < len(bank_data):
                return bank_data[offset]
        return 0xFF

    def write_io1(self, addr: int, data: int) -> None:
        """Write to IO1 region ($DE00-$DEFF) - bank select register.

        Any write to $DE00-$DEFF selects a bank. Bits 0-5 select
        the bank number (0-63). The bank is masked to the actual
        number of banks available.
        """
        # Bits 0-5 select bank (mask to actual bank count)
        bank = data & 0x3F
        if self.num_banks > 0:
            self.current_bank = bank % self.num_banks
        else:
            self.current_bank = 0

        log.debug(f"Ocean: Bank select ${data:02X} -> bank {self.current_bank}")

    # --- Test cartridge generation ---

    @classmethod
    def get_cartridge_variants(cls) -> List[CartridgeVariant]:
        """Return all valid configuration variants for Type 5."""
        return [
            CartridgeVariant("128k", exrom=0, game=1, extra={"bank_count": 16}),
            CartridgeVariant("256k", exrom=0, game=1, extra={"bank_count": 32}),
            CartridgeVariant("512k", exrom=0, game=1, extra={"bank_count": 64}),
        ]

    # Bank select register and signature location
    BANK_SELECT_ADDR = 0xDE00
    SIGNATURE_ADDR = 0x9FF5  # Each bank has its bank number here

    @classmethod
    def create_test_cartridge(cls, variant: CartridgeVariant) -> CartridgeImage:
        """Create test cartridge image for Ocean Type 1.

        Uses a RAM-based bank switch routine because we can't switch banks
        while executing from the ROM being switched.
        """
        bank_count = variant.extra.get("bank_count", 16)

        # Bank 0: Main test code
        builder = TestROMBuilder(base_address=ROML_START)

        builder.emit_screen_init()
        builder.emit_set_border_and_background(COLOR_BLUE)
        builder.emit_display_text("TYPE 5 OCEAN TYPE 1", line=0, color=COLOR_WHITE)
        builder.emit_display_text(f"EXROM=0 GAME=1 {bank_count}x8K", line=1, color=COLOR_YELLOW)
        builder.current_line = 3

        # Install the bank-switch routine in RAM at $C000
        # This routine: switches bank, reads signature at $9FF5, switches back to bank 0
        builder.emit_install_bank_switch_routine(
            bank_select_addr=cls.BANK_SELECT_ADDR,
            signature_addr=cls.SIGNATURE_ADDR,
        )

        # Test each bank by calling the RAM routine and checking the signature
        # We test banks 0, 1, 2, and the last bank
        test_banks = [0, 1, 2, bank_count - 1]
        for test_bank in test_banks:
            test_id = builder.start_test(f"BANK {test_bank} SIGNATURE")
            builder.emit_call_bank_switch(test_bank)
            builder.emit_check_a_equals(test_bank, f"{test_id}_fail")
            builder.emit_pass_result(test_id)
            builder.emit_fail_result(test_id)

        builder.emit_final_status(hardware_type=5, type_name="OCEAN TYPE 1")

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
