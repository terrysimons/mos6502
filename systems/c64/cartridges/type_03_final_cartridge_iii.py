"""Type 3: Final Cartridge III.

CRT hardware type 3. The Final Cartridge III is a popular freezer/utility
cartridge with 64KB ROM organized as 4 x 16KB banks.
"""

from __future__ import annotations

import logging

from .base import (
    Cartridge,
    CartridgeVariant,
    CartridgeImage,
    ROML_START,
    ROML_SIZE,
    ROMH_START,
    ROMH_SIZE,
    IO1_START,
    IO2_START,
)
from .rom_builder import TestROMBuilder
from c64.colors import COLOR_BLUE, COLOR_YELLOW, COLOR_WHITE

log = logging.getLogger("c64.cartridge")


class FinalCartridgeIIICartridge(Cartridge):
    """Type 3: Final Cartridge III.

    CRT hardware type 3. The FC3 is a freezer/utility cartridge with:
    - 64KB ROM organized as 4 x 16KB banks
    - Single control register at $DFFF
    - NMI generation capability (freeze button)
    - IO1/IO2 mirror last 2 pages of current ROM bank

    Bank organization:
        Bank 0: BASIC, Monitor, Disk-Turbo
        Bank 1: Notepad, BASIC (Menu Bar)
        Bank 2: Desktop, Freezer/Print
        Bank 3: Freezer, Compression

    Control register at $DFFF (directly accent 8 bit accent accent):
        Bit 7: Hide register (1 = register writes ignored until reset)
        Bit 6: NMI line (0 = low = generate NMI)
        Bit 5: GAME line (directly controls accent, 0 = active/low)
        Bit 4: EXROM line (directly controls, 0 = active/low)
        Bits 2-3: Unused (FC3+ uses these for extended addressing)
        Bits 0-1: Bank selection (0-3)

    Memory mapping:
        ROML ($8000-$9FFF): First 8KB of current bank
        ROMH ($A000-$BFFF): Second 8KB of current bank
        IO1 ($DE00-$DEFF): Mirror of ROM $1E00-$1EFF (page -2 of bank)
        IO2 ($DF00-$DFFF): Mirror of ROM $1F00-$1FFF (last page of bank)

    Initial state: 16KB mode, bank 0, register visible
        EXROM=0 (active), GAME=0 (active) -> 16KB mode

    References:
        - VICE finaliii.c
        - https://rr.c64.org/wiki/Final_Cartridge_III
    """

    HARDWARE_TYPE = 3
    BANK_SIZE = ROML_SIZE + ROMH_SIZE  # 16KB per bank
    NUM_BANKS = 4

    def __init__(self, banks: list[bytes], name: str = ""):
        """Initialize Final Cartridge III.

        Args:
            banks: List of 4 x 16KB ROM banks
            name: Cartridge name
        """
        # Combine all banks into single ROM for base class
        rom_data = b"".join(banks)
        super().__init__(rom_data, name)

        self.banks = banks
        self._current_bank = 0
        self._register_hidden = False
        self._nmi_line = True  # True = high = inactive (active-low)

        # Initial state: 16KB mode (EXROM=0, GAME=0)
        self._exrom = False  # Active (low)
        self._game = False   # Active (low) = 16KB mode

        log.debug(
            f"FinalCartridgeIIICartridge: {len(banks)} banks x {len(banks[0]) if banks else 0} bytes, "
            f"EXROM={1 if self._exrom else 0}, GAME={1 if self._game else 0}"
        )

    def reset(self) -> None:
        """Reset cartridge to initial state."""
        self._current_bank = 0
        self._register_hidden = False
        self._nmi_line = True
        self._exrom = False  # 16KB mode
        self._game = False

    @property
    def nmi_pending(self) -> bool:
        """Check if NMI should be triggered.

        NMI is active when bit 6 of control register is 0.
        The freeze button also triggers NMI (not emulated here).
        """
        return not self._nmi_line

    def _get_bank_data(self, bank: int) -> bytes:
        """Get ROM data for specified bank.

        Args:
            bank: Bank number (0-3)

        Returns:
            16KB bank data
        """
        bank = bank % len(self.banks)
        return self.banks[bank]

    def read_roml(self, addr: int) -> int:
        """Read from ROML region ($8000-$9FFF).

        Returns data from first 8KB of current bank.
        """
        bank_data = self._get_bank_data(self._current_bank)
        offset = addr - ROML_START
        if offset < len(bank_data):
            return bank_data[offset]
        return 0xFF

    def read_romh(self, addr: int) -> int:
        """Read from ROMH region ($A000-$BFFF).

        Returns data from second 8KB of current bank.
        """
        bank_data = self._get_bank_data(self._current_bank)
        # ROMH is second 8KB of the 16KB bank
        offset = ROML_SIZE + (addr - ROMH_START)
        if offset < len(bank_data):
            return bank_data[offset]
        return 0xFF

    def read_io1(self, addr: int) -> int:
        """Read from IO1 region ($DE00-$DEFF).

        IO1 mirrors ROM offset $1E00-$1EFF of current bank
        (second-to-last page of the 16KB bank).
        """
        bank_data = self._get_bank_data(self._current_bank)
        # $1E00-$1EFF within the 16KB bank
        rom_offset = 0x1E00 + (addr - IO1_START)
        if rom_offset < len(bank_data):
            return bank_data[rom_offset]
        return 0xFF

    def read_io2(self, addr: int) -> int:
        """Read from IO2 region ($DF00-$DFFF).

        IO2 mirrors ROM offset $1F00-$1FFF of current bank
        (last page of the 16KB bank).
        """
        bank_data = self._get_bank_data(self._current_bank)
        # $1F00-$1FFF within the 16KB bank
        rom_offset = 0x1F00 + (addr - IO2_START)
        if rom_offset < len(bank_data):
            return bank_data[rom_offset]
        return 0xFF

    def write_io1(self, addr: int, data: int) -> None:
        """Write to IO1 region ($DE00-$DEFF).

        IO1 writes are ignored (read-only mirror).
        """
        pass

    def write_io2(self, addr: int, data: int) -> None:
        """Write to IO2 region ($DF00-$DFFF).

        Only $DFFF is the control register. Other addresses are ignored.

        Control register bits:
            Bit 7: Hide register (1 = hidden until reset)
            Bit 6: NMI line (0 = generate NMI)
            Bit 5: GAME line (0 = active/low)
            Bit 4: EXROM line (0 = active/low)
            Bits 0-1: Bank selection
        """
        if addr != 0xDFFF:
            return

        if self._register_hidden:
            return

        # Bit 7: Hide register
        if data & 0x80:
            self._register_hidden = True
            log.debug("FC3: Control register hidden")

        # Bit 6: NMI line (directly accent accent)
        self._nmi_line = bool(data & 0x40)

        # Bit 5: GAME line (directly control accent)
        self._game = bool(data & 0x20)

        # Bit 4: EXROM line
        self._exrom = bool(data & 0x10)

        # Bits 0-1: Bank selection
        new_bank = data & 0x03
        if new_bank != self._current_bank:
            log.debug(f"FC3: Bank switch {self._current_bank} -> {new_bank}")
            self._current_bank = new_bank

        log.debug(
            f"FC3: Control write ${data:02X} - "
            f"bank={self._current_bank}, EXROM={1 if self._exrom else 0}, "
            f"GAME={1 if self._game else 0}, NMI={'inactive' if self._nmi_line else 'ACTIVE'}, "
            f"hidden={self._register_hidden}"
        )

    # --- Test cartridge generation ---

    # Bank select register and signature location
    BANK_SELECT_ADDR = 0xDFFF  # FC3 uses $DFFF, not $DE00
    SIGNATURE_ADDR = 0x9FF5    # Each bank has its bank number here

    @classmethod
    def get_cartridge_variants(cls) -> list[CartridgeVariant]:
        """Return all valid configuration variants for Type 3."""
        return [
            CartridgeVariant("", exrom=0, game=0, extra={"bank_count": 4}),
        ]

    @classmethod
    def create_test_cartridge(cls, variant: CartridgeVariant) -> CartridgeImage:
        """Create test cartridge image for Final Cartridge III.

        Uses a RAM-based bank switch routine because we can't switch banks
        while executing from the ROM being switched.

        Note: FC3 uses $DFFF for control, bits 0-1 for bank selection.
        """
        bank_count = variant.extra.get("bank_count", 4)

        # Bank 0: Main test code
        builder = TestROMBuilder(base_address=ROML_START)

        builder.emit_screen_init()
        builder.emit_set_border_and_background(COLOR_BLUE)
        builder.emit_display_text("TYPE 3 FINAL CART III", line=0, color=COLOR_WHITE)
        builder.emit_display_text("EXROM=0 GAME=0 4x16K", line=1, color=COLOR_YELLOW)
        builder.current_line = 3

        # Install the bank-switch routine in RAM at $C000
        builder.emit_install_bank_switch_routine(
            bank_select_addr=cls.BANK_SELECT_ADDR,
            signature_addr=cls.SIGNATURE_ADDR,
        )

        # Test each bank by calling the RAM routine
        # FC3: control value = bank & 0x03 (bits 0-1)
        test_banks = [0, 1, 2, 3]
        for test_bank in test_banks:
            test_id = builder.start_test(f"BANK {test_bank} SIGNATURE")
            builder.emit_call_bank_switch(test_bank)  # Direct mapping for FC3
            builder.emit_check_a_equals(test_bank, f"{test_id}_fail")
            builder.emit_pass_result(test_id)
            builder.emit_fail_result(test_id)

        builder.emit_final_status(hardware_type=3, type_name="FINAL CART III")

        # Build banks (16KB each: 8KB ROML + 8KB ROMH)
        banks = []

        # Bank 0: Test code in ROML, empty ROMH
        roml0 = bytearray(builder.build_rom())
        roml0[0x1FF5] = 0  # Bank 0 signature
        romh0 = bytearray(ROMH_SIZE)
        banks.append(bytes(roml0) + bytes(romh0))

        # Banks 1-3: Each has its bank number at $9FF5
        for i in range(1, bank_count):
            roml = bytearray(ROML_SIZE)
            roml[0x1FF5] = i  # Bank number as signature
            romh = bytearray(ROMH_SIZE)
            banks.append(bytes(roml) + bytes(romh))

        return CartridgeImage(
            description=variant.description,
            exrom=variant.exrom,
            game=variant.game,
            extra=variant.extra,
            rom_data={"banks": banks},
            hardware_type=cls.HARDWARE_TYPE,
        )
