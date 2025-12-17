"""Type 0: Static ROM cartridge with no bank switching.

CRT hardware type 0 (called "Normal cartridge" in VICE/CCS64 spec).
The simplest cartridge type where ROM is directly mapped to fixed
addresses with no banking hardware.
"""


from mos6502.compat import logging
from mos6502.compat import Optional, List

from .base import (
    Cartridge,
    CartridgeVariant,
    CartridgeImage,
    CartridgeType,
    ROML_START,
    ROML_SIZE,
    ROMH_START,
    ROMH_SIZE,
    ULTIMAX_ROMH_START,
    ULTIMAX_ROMH_SIZE,
)
from .rom_builder import TestROMBuilder
from c64.colors import COLOR_BLUE, COLOR_YELLOW, COLOR_WHITE

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

    # --- Test cartridge generation ---

    @classmethod
    def get_cartridge_variants(cls) -> List[CartridgeVariant]:
        """Return all valid configuration variants for Type 0."""
        return [
            CartridgeVariant("8k", exrom=0, game=1),
            CartridgeVariant("16k", exrom=0, game=0),
            CartridgeVariant("16k_single_chip", exrom=0, game=0, extra={"single_chip": True}),
            CartridgeVariant("ultimax", exrom=1, game=0),
            CartridgeVariant("ultimax_with_roml", exrom=1, game=0, extra={"include_roml": True}),
        ]

    @classmethod
    def create_test_cartridge(cls, variant: CartridgeVariant) -> CartridgeImage:
        """Create test cartridge image for the given variant."""
        if variant.description == "8k":
            return cls._create_8k_test_cartridge(variant)
        elif variant.description in ("16k", "16k_single_chip"):
            return cls._create_16k_test_cartridge(variant)
        elif variant.description == "ultimax":
            return cls._create_ultimax_test_cartridge(variant, include_roml=False)
        elif variant.description == "ultimax_with_roml":
            return cls._create_ultimax_test_cartridge(variant, include_roml=True)
        else:
            raise ValueError(f"Unknown variant: {variant.description}")

    @classmethod
    def _create_8k_test_cartridge(cls, variant: CartridgeVariant) -> CartridgeImage:
        """Create 8KB mode test cartridge.

        8KB mode: EXROM=0, GAME=1 - ROML only at $8000-$9FFF
        """
        builder = TestROMBuilder(base_address=ROML_START)

        builder.emit_screen_init()
        builder.emit_set_border_and_background(COLOR_BLUE)
        builder.emit_display_text("TYPE 0 8K TEST", line=0, color=COLOR_WHITE)
        builder.emit_display_text("EXROM=0 GAME=1", line=1, color=COLOR_YELLOW)
        builder.current_line = 3

        # Test 1: ROML readable at $8000 (check CBM80 signature)
        test1 = builder.start_test("ROML START $8000")
        builder.emit_check_byte(0x8004, 0xC3, f"{test1}_fail")  # 'C'
        builder.emit_check_byte(0x8005, 0xC2, f"{test1}_fail")  # 'B'
        builder.emit_pass_result(test1)
        builder.emit_fail_result(test1)

        # Test 2: ROML end at $9FFF (check signature)
        test2 = builder.start_test("ROML END $9FFF")
        builder.emit_check_byte(0x9FF0, ord('R'), f"{test2}_fail")
        builder.emit_check_byte(0x9FF1, ord('O'), f"{test2}_fail")
        builder.emit_pass_result(test2)
        builder.emit_fail_result(test2)

        # Test 3: ROMH should NOT be visible
        test3 = builder.start_test("NO ROMH AT $A000")
        # If ROMH were mapped, we'd see our signature - check it's NOT there
        builder.emit_check_byte_not_equal(0xBFF0, ord('R'), f"{test3}_fail")
        builder.emit_pass_result(test3)
        builder.emit_fail_result(test3)

        builder.emit_final_status(hardware_type=0, type_name="8K")

        # Build ROM and add signature at end
        roml = bytearray(builder.build_rom())
        # Add "ROML-OK!" signature at $9FF0
        signature = b"ROML-OK!"
        roml[0x1FF0:0x1FF0 + len(signature)] = signature

        return CartridgeImage(
            description=variant.description,
            exrom=variant.exrom,
            game=variant.game,
            extra=variant.extra,
            rom_data={"roml": bytes(roml)},
            hardware_type=cls.HARDWARE_TYPE,
        )

    @classmethod
    def _create_16k_test_cartridge(cls, variant: CartridgeVariant) -> CartridgeImage:
        """Create 16KB mode test cartridge.

        16KB mode: EXROM=0, GAME=0 - ROML at $8000-$9FFF, ROMH at $A000-$BFFF
        """
        builder = TestROMBuilder(base_address=ROML_START)

        builder.emit_screen_init()
        builder.emit_set_border_and_background(COLOR_BLUE)
        builder.emit_display_text("TYPE 0 16K TEST", line=0, color=COLOR_WHITE)
        builder.emit_display_text("EXROM=0 GAME=0", line=1, color=COLOR_YELLOW)
        builder.current_line = 3

        # Test 1: ROML readable at $8000
        test1 = builder.start_test("ROML START $8000")
        builder.emit_check_byte(0x8004, 0xC3, f"{test1}_fail")
        builder.emit_check_byte(0x8005, 0xC2, f"{test1}_fail")
        builder.emit_pass_result(test1)
        builder.emit_fail_result(test1)

        # Test 2: ROML end signature
        test2 = builder.start_test("ROML END $9FFF")
        builder.emit_check_byte(0x9FF0, ord('R'), f"{test2}_fail")
        builder.emit_check_byte(0x9FF1, ord('O'), f"{test2}_fail")
        builder.emit_pass_result(test2)
        builder.emit_fail_result(test2)

        # Test 3: ROMH visible at $A000
        test3 = builder.start_test("ROMH START $A000")
        builder.emit_check_byte(0xA000, ord('R'), f"{test3}_fail")
        builder.emit_check_byte(0xA001, ord('H'), f"{test3}_fail")
        builder.emit_pass_result(test3)
        builder.emit_fail_result(test3)

        # Test 4: ROMH end signature
        test4 = builder.start_test("ROMH END $BFFF")
        builder.emit_check_byte(0xBFF0, ord('R'), f"{test4}_fail")
        builder.emit_check_byte(0xBFF1, ord('H'), f"{test4}_fail")
        builder.emit_pass_result(test4)
        builder.emit_fail_result(test4)

        builder.emit_final_status(hardware_type=0, type_name="16K")

        # Build ROML and add signature
        roml = bytearray(builder.build_rom())
        roml[0x1FF0:0x1FF8] = b"ROML-OK!"

        # Build ROMH with signatures
        romh = bytearray(ROMH_SIZE)
        romh[0x0000:0x0008] = b"RH-START"  # At $A000
        romh[0x1FF0:0x1FF8] = b"RH-END!!"  # At $BFF0

        return CartridgeImage(
            description=variant.description,
            exrom=variant.exrom,
            game=variant.game,
            extra=variant.extra,
            rom_data={"roml": bytes(roml), "romh": bytes(romh)},
            hardware_type=cls.HARDWARE_TYPE,
        )

    @classmethod
    def _create_ultimax_test_cartridge(
        cls, variant: CartridgeVariant, include_roml: bool = False
    ) -> CartridgeImage:
        """Create Ultimax mode test cartridge.

        Ultimax mode: EXROM=1, GAME=0 - ROMH at $E000-$FFFF (optional ROML at $8000-$9FFF)
        """
        # In Ultimax mode, we need code at $E000 since that's where reset vector points
        builder = TestROMBuilder(base_address=ULTIMAX_ROMH_START)

        builder.emit_screen_init()
        builder.emit_set_border_and_background(COLOR_BLUE)
        title = "TYPE 0 ULTIMAX+ROML" if include_roml else "TYPE 0 ULTIMAX TEST"
        builder.emit_display_text(title, line=0, color=COLOR_WHITE)
        builder.emit_display_text("EXROM=1 GAME=0", line=1, color=COLOR_YELLOW)
        builder.current_line = 3

        # Test 1: ROMH visible at $E000 (check CBM80 equivalent signature)
        test1 = builder.start_test("ROMH START $E000")
        builder.emit_check_byte(0xE004, 0xC3, f"{test1}_fail")  # 'C' from CBM80
        builder.emit_check_byte(0xE005, 0xC2, f"{test1}_fail")  # 'B' from CBM80
        builder.emit_pass_result(test1)
        builder.emit_fail_result(test1)

        # Test 2: ROMH end at $FFFF area
        test2 = builder.start_test("ROMH END $FFF0")
        builder.emit_check_byte(0xFFF0, ord('U'), f"{test2}_fail")
        builder.emit_check_byte(0xFFF1, ord('L'), f"{test2}_fail")
        builder.emit_pass_result(test2)
        builder.emit_fail_result(test2)

        if include_roml:
            # Test 3: ROML also visible at $8000
            test3 = builder.start_test("ROML AT $8000")
            builder.emit_check_byte(0x8000, ord('R'), f"{test3}_fail")
            builder.emit_check_byte(0x8001, ord('L'), f"{test3}_fail")
            builder.emit_pass_result(test3)
            builder.emit_fail_result(test3)

        builder.emit_final_status(hardware_type=0, type_name="ULTIMAX")

        # Build ROMH (at $E000-$FFFF in Ultimax mode)
        ultimax_romh = bytearray(builder.build_rom())
        # The reset vector at $FFFC-$FFFD needs to point to our code
        ultimax_romh[0x1FFC] = 0x09  # Reset vector low byte -> $E009
        ultimax_romh[0x1FFD] = 0xE0  # Reset vector high byte
        # Add signature before vectors
        ultimax_romh[0x1FF0:0x1FF8] = b"ULTIMAX!"

        rom_data = {"ultimax_romh": bytes(ultimax_romh)}

        if include_roml:
            # Create ROML with signature
            roml = bytearray(ROML_SIZE)
            roml[0x0000:0x0008] = b"RL-START"  # "RL" at start
            roml[0x1FF0:0x1FF8] = b"ROML-OK!"
            rom_data["roml"] = bytes(roml)

        return CartridgeImage(
            description=variant.description,
            exrom=variant.exrom,
            game=variant.game,
            extra=variant.extra,
            rom_data=rom_data,
            hardware_type=cls.HARDWARE_TYPE,
        )
