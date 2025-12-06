#!/usr/bin/env python3
"""Tests for C64 cartridge type handling.

Tests that:
- Type 0 (Normal cartridge) loads correctly
- Unsupported types (1-85) are correctly identified
- CRT header parsing correctly identifies hardware types
- EXROM/GAME lines are set correctly for each cartridge type
- Error and mapper test cartridge files exist and are valid
"""

from pathlib import Path
from typing import NamedTuple

import pytest

from c64 import C64
from c64.cartridges import (
    CARTRIDGE_TYPES,
    UNIMPLEMENTED_CARTRIDGE_TYPES,
    CartridgeType,
    CartridgeVariant,
    Cartridge,
    ErrorCartridge,
    StaticROMCartridge,
    create_cartridge,
    ROML_START,
    ROMH_START,
    ROML_SIZE,
    ROMH_SIZE,
    ULTIMAX_ROMH_START,
    ULTIMAX_ROMH_SIZE,
    IO1_START,
    IO2_START,
)

from .conftest import CARTRIDGE_TYPES_DIR, C64_ROMS_DIR, requires_c64_roms


# --- Parameterized test helpers ---

class CartridgeTestCase(NamedTuple):
    """Test case for a cartridge variant."""
    cart_type: CartridgeType
    variant: CartridgeVariant
    crt_path: Path


def _get_safe_name(hw_type: int) -> str:
    """Get safe filename component from hardware type."""
    type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, f"unknown_{hw_type}")
    return (
        type_name.lower()
        .replace(" ", "_")
        .replace(",", "")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
        .replace(".", "")
    )


def _build_crt_test_cases() -> list[CartridgeTestCase]:
    """Build list of all CRT test cases from registered cartridge types."""
    cases = []
    for cart_type_key, cart_class in CARTRIDGE_TYPES.items():
        # Get the CartridgeType enum
        if isinstance(cart_type_key, CartridgeType):
            cart_type = cart_type_key
        else:
            cart_type = CartridgeType(cart_type_key)

        hw_type = cart_type.value
        safe_name = _get_safe_name(hw_type)
        base = f"test_cart_type_{hw_type:02d}_{safe_name}"

        for variant in cart_class.get_cartridge_variants():
            if variant.description:
                filename = f"{base}_{variant.description}.crt"
            else:
                filename = f"{base}.crt"
            crt_path = CARTRIDGE_TYPES_DIR / filename
            cases.append(CartridgeTestCase(cart_type, variant, crt_path))

    return cases


def _make_test_id(case: CartridgeTestCase) -> str:
    """Generate test ID like 'NORMAL-8k' or 'ACTION_REPLAY'."""
    if case.variant.description:
        return f"{case.cart_type.name}-{case.variant.description}"
    return case.cart_type.name


# Build test cases at module load time
CRT_TEST_CASES = _build_crt_test_cases()
CRT_TEST_IDS = [_make_test_id(case) for case in CRT_TEST_CASES]


class BinTestCase(NamedTuple):
    """Test case for a raw .bin cartridge file (Type 0 only)."""
    variant: CartridgeVariant
    bin_path: Path
    # Expected values after auto-detection (may differ from variant when
    # raw .bin loading can't distinguish certain modes)
    expected_cart_type: str
    expected_exrom: int
    expected_game: int


def _build_bin_test_cases() -> list[BinTestCase]:
    """Build list of .bin test cases from Type 0 variants.

    Only Type 0 (Normal cartridge) supports raw .bin loading since
    other types require CRT metadata for bank configuration.
    """
    cases = []
    cart_class = CARTRIDGE_TYPES.get(CartridgeType.NORMAL)
    if cart_class is None:
        return cases

    hw_type = CartridgeType.NORMAL.value
    safe_name = _get_safe_name(hw_type)
    base = f"test_cart_type_{hw_type:02d}_{safe_name}"

    # Map variant descriptions to cart_type strings for raw .bin detection.
    # Most variants use their own cart_type name, but some are detected differently.
    CART_TYPE_DETECTION = {
        "8k": "8k",
        "16k": "16k",
        "16k_single_chip": "16k",
        "ultimax": "ultimax",
        # ultimax_with_roml is 16KB so auto-detection sees it as 16k mode -
        # raw .bin files have no metadata to indicate ultimax mode with ROML.
        "ultimax_with_roml": "16k",
    }

    for variant in cart_class.get_cartridge_variants():
        if variant.description:
            filename = f"{base}_{variant.description}.bin"
        else:
            filename = f"{base}.bin"
        bin_path = CARTRIDGE_TYPES_DIR / filename

        detected_type = CART_TYPE_DETECTION.get(variant.description, "8k")

        # Use variant's EXROM/GAME unless detection differs from variant
        if detected_type == variant.description or detected_type == variant.description.replace("_single_chip", ""):
            # Detection matches variant - use variant's values
            exrom, game = variant.exrom, variant.game
        else:
            # Detection differs - look up the target variant's EXROM/GAME
            # (e.g., ultimax_with_roml detected as 16k uses 16k's EXROM/GAME)
            target_variant = next(
                (v for v in cart_class.get_cartridge_variants() if v.description == detected_type),
                None
            )
            if target_variant:
                exrom, game = target_variant.exrom, target_variant.game
            else:
                # Fallback to variant's own values
                exrom, game = variant.exrom, variant.game

        cases.append(BinTestCase(variant, bin_path, detected_type, exrom, game))

    return cases


# Build .bin test cases at module load time
BIN_TEST_CASES = _build_bin_test_cases()
BIN_TEST_IDS = [f"NORMAL-{case.variant.description}" for case in BIN_TEST_CASES]


class UnimplementedTestCase(NamedTuple):
    """Test case for an unimplemented cartridge type."""
    hw_type: int
    variant: CartridgeVariant
    crt_path: Path


def _build_unimplemented_test_cases() -> list[UnimplementedTestCase]:
    """Build list of test cases for unimplemented cartridge types.

    These cartridges have test .crt files but should load as ErrorCartridge
    since the mapper is not yet implemented.
    """
    cases = []

    for hw_type, cart_class in sorted(UNIMPLEMENTED_CARTRIDGE_TYPES.items()):
        safe_name = _get_safe_name(hw_type)
        base = f"test_cart_type_{hw_type:02d}_{safe_name}"

        for variant in cart_class.get_cartridge_variants():
            if variant.description:
                filename = f"{base}_{variant.description}.crt"
            else:
                filename = f"{base}.crt"
            crt_path = CARTRIDGE_TYPES_DIR / filename
            cases.append(UnimplementedTestCase(hw_type, variant, crt_path))

    return cases


def _make_unimplemented_test_id(case: UnimplementedTestCase) -> str:
    """Generate test ID for unimplemented cartridge test case."""
    name = C64.CRT_HARDWARE_TYPES.get(case.hw_type, f"TYPE_{case.hw_type}")
    safe_name = name.upper().replace(" ", "_").replace(",", "").replace("/", "_").replace("-", "_")
    if case.variant.description:
        return f"{safe_name}-{case.variant.description}"
    return safe_name


# Build unimplemented test cases at module load time
UNIMPLEMENTED_TEST_CASES = _build_unimplemented_test_cases()
UNIMPLEMENTED_TEST_IDS = [_make_unimplemented_test_id(case) for case in UNIMPLEMENTED_TEST_CASES]


def cart_type_id(hw_type: int) -> str:
    """Generate a readable test ID for a cartridge hardware type."""
    # Try to get enum name first (for implemented types)
    try:
        return CartridgeType(hw_type).name
    except ValueError:
        pass
    # Fall back to CRT_HARDWARE_TYPES name
    name = C64.CRT_HARDWARE_TYPES.get(hw_type, f"TYPE_{hw_type}")
    # Convert to TEST_ID format: "Ocean type 1" -> "OCEAN_TYPE_1"
    return name.upper().replace(" ", "_").replace(",", "").replace("/", "_").replace("-", "_")


class TestCartridgeModule:
    """Tests for the cartridge module classes and functions."""

    @requires_c64_roms
    def test_cartridge_types_registry_contains_type_0(self):
        """Type 0 (Normal cartridge) should be in the registry."""
        assert StaticROMCartridge.HARDWARE_TYPE in CARTRIDGE_TYPES
        assert CARTRIDGE_TYPES[StaticROMCartridge.HARDWARE_TYPE] == StaticROMCartridge

    @requires_c64_roms
    def test_cartridge_types_registry_contains_type_1(self):
        """Type 1 (Action Replay) should be in the registry."""
        action_replay_class = CARTRIDGE_TYPES[1]
        assert action_replay_class.HARDWARE_TYPE in CARTRIDGE_TYPES
        assert CARTRIDGE_TYPES[action_replay_class.HARDWARE_TYPE] == action_replay_class

    @requires_c64_roms
    def test_action_replay_cartridge_hardware_type(self):
        """ActionReplayCartridge should have hardware type 1."""
        action_replay_class = CARTRIDGE_TYPES[1]
        assert action_replay_class.HARDWARE_TYPE == 1

    @requires_c64_roms
    def test_static_rom_cartridge_hardware_type(self):
        """StaticROMCartridge should have hardware type 0."""
        assert StaticROMCartridge.HARDWARE_TYPE == 0

    @requires_c64_roms
    def test_error_cartridge_hardware_type(self):
        """ErrorCartridge should have hardware type -1 (not a real type)."""
        assert ErrorCartridge.HARDWARE_TYPE == -1

    @requires_c64_roms
    @pytest.mark.parametrize("cart_type", list(CARTRIDGE_TYPES.keys()))
    def test_registered_cartridge_hardware_type_matches_key(self, cart_type):
        """Each registered cartridge class should have HARDWARE_TYPE matching its registry key."""
        cart_class = CARTRIDGE_TYPES[cart_type]
        assert cart_class.HARDWARE_TYPE == cart_type, (
            f"{cart_class.__name__}.HARDWARE_TYPE ({cart_class.HARDWARE_TYPE}) "
            f"doesn't match registry key ({cart_type})"
        )


@requires_c64_roms
class TestMagicDeskCartridge:
    """Tests for MagicDeskCartridge (Type 19).

    Ref: https://www.hackup.net/2019/07/bank-switching-cartridges/
    """

    # Get class from registry to avoid direct import
    CartClass = CARTRIDGE_TYPES[19]

    def test_initial_state_8kb_mode(self):
        """Magic Desk should start in 8KB mode (EXROM=0, GAME=1)."""
        banks = [bytes(ROML_SIZE) for _ in range(4)]
        cart = self.CartClass(banks, name="Test Magic Desk")

        assert cart.exrom is False, "Magic Desk should have EXROM active (False)"
        assert cart.game is True, "Magic Desk should have GAME inactive (True) = 8KB mode"
        assert cart.current_bank == 0
        assert cart.cartridge_disabled is False

    def test_bank_switching(self):
        """Writing to $DE00 should switch banks."""
        # Create 4 banks with different data
        banks = []
        for i in range(4):
            bank = bytearray(ROML_SIZE)
            bank[0] = 0x10 + i  # Each bank starts with different byte
            banks.append(bytes(bank))

        cart = self.CartClass(banks, name="Test Magic Desk")

        # Initial state: bank 0
        assert cart.read_roml(ROML_START) == 0x10

        # Switch to bank 1
        cart.write_io1(0xDE00, 0x01)
        assert cart.current_bank == 1
        assert cart.read_roml(ROML_START) == 0x11

        # Switch to bank 2
        cart.write_io1(0xDE00, 0x02)
        assert cart.current_bank == 2
        assert cart.read_roml(ROML_START) == 0x12

        # Switch to bank 3
        cart.write_io1(0xDE00, 0x03)
        assert cart.current_bank == 3
        assert cart.read_roml(ROML_START) == 0x13

    def test_bank_wrapping(self):
        """Bank number should wrap to actual number of banks."""
        banks = [bytes(ROML_SIZE) for _ in range(4)]
        cart = self.CartClass(banks, name="Test Magic Desk")

        # Try to select bank 5 (should wrap to 1 with 4 banks)
        cart.write_io1(0xDE00, 0x05)
        assert cart.current_bank == 1  # 5 % 4 = 1

        # Try to select bank 8 (should wrap to 0)
        cart.write_io1(0xDE00, 0x08)
        assert cart.current_bank == 0  # 8 % 4 = 0

    def test_disable_cartridge(self):
        """Writing with bit 7 set should disable cartridge."""
        banks = [bytes(ROML_SIZE) for _ in range(4)]
        cart = self.CartClass(banks, name="Test Magic Desk")

        # Cartridge starts enabled
        assert cart.cartridge_disabled is False
        assert cart.exrom is False

        # Disable cartridge by writing $80 to $DE00
        cart.write_io1(0xDE00, 0x80)

        assert cart.cartridge_disabled is True
        assert cart.exrom is True, "EXROM should go high when disabled"

        # ROML should return $FF when disabled
        assert cart.read_roml(ROML_START) == 0xFF

    def test_disabled_cartridge_ignores_writes(self):
        """Once disabled, writes to $DE00 should be ignored until reset."""
        banks = []
        for i in range(4):
            bank = bytearray(ROML_SIZE)
            bank[0] = 0x10 + i
            banks.append(bytes(bank))

        cart = self.CartClass(banks, name="Test Magic Desk")

        # Disable cartridge
        cart.write_io1(0xDE00, 0x80)
        assert cart.cartridge_disabled is True

        # Try to switch bank - should be ignored
        cart.write_io1(0xDE00, 0x02)
        assert cart.cartridge_disabled is True  # Still disabled
        assert cart.read_roml(ROML_START) == 0xFF  # Still returns $FF

    def test_reset_re_enables_cartridge(self):
        """Reset should re-enable disabled cartridge."""
        banks = []
        for i in range(4):
            bank = bytearray(ROML_SIZE)
            bank[0] = 0x10 + i
            banks.append(bytes(bank))

        cart = self.CartClass(banks, name="Test Magic Desk")

        # Disable cartridge
        cart.write_io1(0xDE00, 0x80)
        assert cart.cartridge_disabled is True

        # Reset
        cart.reset()

        assert cart.cartridge_disabled is False
        assert cart.exrom is False
        assert cart.game is True
        assert cart.current_bank == 0
        assert cart.read_roml(ROML_START) == 0x10

    def test_64_banks_512kb(self):
        """Should support up to 64 banks (512KB)."""
        banks = []
        for i in range(64):
            bank = bytearray(ROML_SIZE)
            bank[0] = i  # Each bank starts with its number
            banks.append(bytes(bank))

        cart = self.CartClass(banks, name="Test 512KB")

        assert cart.num_banks == 64

        # Test several banks
        for bank_num in [0, 15, 31, 63]:
            cart.write_io1(0xDE00, bank_num)
            assert cart.current_bank == bank_num
            assert cart.read_roml(ROML_START) == bank_num

    def test_io_region_addresses(self):
        """Bank switching should work from any IO1 address ($DE00-$DEFF)."""
        banks = []
        for i in range(4):
            bank = bytearray(ROML_SIZE)
            bank[0] = 0x10 + i
            banks.append(bytes(bank))

        cart = self.CartClass(banks, name="Test Magic Desk")

        # Write to various IO1 addresses
        cart.write_io1(0xDE00, 0x01)
        assert cart.current_bank == 1

        cart.write_io1(0xDE42, 0x02)
        assert cart.current_bank == 2

        cart.write_io1(0xDEFF, 0x03)
        assert cart.current_bank == 3


@requires_c64_roms
class TestC64GSCartridge:
    """Tests for C64GSCartridge (Type 15).

    C64 Game System cartridges are similar to Magic Desk but disable
    via IO1 READ instead of writing bit 7.
    """

    # Get class from registry to avoid direct import
    CartClass = CARTRIDGE_TYPES[15]

    def test_hardware_type(self):
        """C64GSCartridge should have hardware type 15."""
        assert self.CartClass.HARDWARE_TYPE == 15

    def test_initial_state_8kb_mode(self):
        """C64GS should start in 8KB mode (EXROM=0, GAME=1)."""
        banks = [bytes(ROML_SIZE) for _ in range(4)]
        cart = self.CartClass(banks, name="Test C64GS")

        assert cart.exrom is False, "C64GS should have EXROM active (False)"
        assert cart.game is True, "C64GS should have GAME inactive (True) = 8KB mode"
        assert cart.current_bank == 0
        assert cart.cartridge_disabled is False

    def test_bank_switching(self):
        """Writing to $DE00 should switch banks."""
        # Create 4 banks with different data
        banks = []
        for i in range(4):
            bank = bytearray(ROML_SIZE)
            bank[0] = 0x10 + i  # Each bank starts with different byte
            banks.append(bytes(bank))

        cart = self.CartClass(banks, name="Test C64GS")

        # Initial state: bank 0
        assert cart.read_roml(ROML_START) == 0x10

        # Switch to bank 1
        cart.write_io1(0xDE00, 0x01)
        assert cart.current_bank == 1
        assert cart.read_roml(ROML_START) == 0x11

        # Switch to bank 2
        cart.write_io1(0xDE00, 0x02)
        assert cart.current_bank == 2
        assert cart.read_roml(ROML_START) == 0x12

        # Switch to bank 3
        cart.write_io1(0xDE00, 0x03)
        assert cart.current_bank == 3
        assert cart.read_roml(ROML_START) == 0x13

    def test_bank_wrapping(self):
        """Bank number should wrap to actual number of banks."""
        banks = [bytes(ROML_SIZE) for _ in range(4)]
        cart = self.CartClass(banks, name="Test C64GS")

        # Try to select bank 5 (should wrap to 1 with 4 banks)
        cart.write_io1(0xDE00, 0x05)
        assert cart.current_bank == 1  # 5 % 4 = 1

        # Try to select bank 8 (should wrap to 0)
        cart.write_io1(0xDE00, 0x08)
        assert cart.current_bank == 0  # 8 % 4 = 0

    def test_io1_read_disables_cartridge(self):
        """Reading from IO1 ($DE00-$DEFF) should disable cartridge."""
        banks = [bytes(ROML_SIZE) for _ in range(4)]
        cart = self.CartClass(banks, name="Test C64GS")

        # Cartridge starts enabled
        assert cart.cartridge_disabled is False
        assert cart.exrom is False

        # Read from IO1 - this should disable the cartridge
        result = cart.read_io1(0xDE00)

        assert result == 0xFF
        assert cart.cartridge_disabled is True
        assert cart.exrom is True, "EXROM should go high when disabled"

        # ROML should return $FF when disabled
        assert cart.read_roml(ROML_START) == 0xFF

    def test_any_io1_address_disables(self):
        """Reading from any IO1 address ($DE00-$DEFF) should disable."""
        banks = [bytes(ROML_SIZE) for _ in range(4)]
        cart = self.CartClass(banks, name="Test C64GS")

        # Read from $DE42 (not $DE00)
        cart.read_io1(0xDE42)
        assert cart.cartridge_disabled is True

        cart.reset()
        assert cart.cartridge_disabled is False

        # Read from $DEFF
        cart.read_io1(0xDEFF)
        assert cart.cartridge_disabled is True

    def test_disabled_cartridge_ignores_writes(self):
        """Once disabled, writes to $DE00 should be ignored until reset."""
        banks = []
        for i in range(4):
            bank = bytearray(ROML_SIZE)
            bank[0] = 0x10 + i
            banks.append(bytes(bank))

        cart = self.CartClass(banks, name="Test C64GS")

        # Disable cartridge by reading IO1
        cart.read_io1(0xDE00)
        assert cart.cartridge_disabled is True

        # Try to switch bank - should be ignored
        cart.write_io1(0xDE00, 0x02)
        assert cart.cartridge_disabled is True  # Still disabled
        assert cart.read_roml(ROML_START) == 0xFF  # Still returns $FF

    def test_reset_re_enables_cartridge(self):
        """Reset should re-enable disabled cartridge."""
        banks = []
        for i in range(4):
            bank = bytearray(ROML_SIZE)
            bank[0] = 0x10 + i
            banks.append(bytes(bank))

        cart = self.CartClass(banks, name="Test C64GS")

        # Disable cartridge
        cart.read_io1(0xDE00)
        assert cart.cartridge_disabled is True

        # Reset
        cart.reset()

        assert cart.cartridge_disabled is False
        assert cart.exrom is False
        assert cart.game is True
        assert cart.current_bank == 0
        assert cart.read_roml(ROML_START) == 0x10

    def test_64_banks_512kb(self):
        """Should support up to 64 banks (512KB)."""
        banks = []
        for i in range(64):
            bank = bytearray(ROML_SIZE)
            bank[0] = i  # Each bank starts with its number
            banks.append(bytes(bank))

        cart = self.CartClass(banks, name="Test 512KB")

        assert cart.num_banks == 64

        # Test several banks
        for bank_num in [0, 15, 31, 63]:
            cart.write_io1(0xDE00, bank_num)
            assert cart.current_bank == bank_num
            assert cart.read_roml(ROML_START) == bank_num


class TestFinalCartridgeIIICartridge:
    """Tests for FinalCartridgeIIICartridge (Type 3).

    Final Cartridge III is a freezer/utility cartridge with:
    - 64KB ROM organized as 4 x 16KB banks
    - Single control register at $DFFF
    - NMI generation capability
    - IO1/IO2 mirror last 2 pages of current ROM bank

    Ref: https://rr.c64.org/wiki/Final_Cartridge_III
    """

    # Get class from registry to avoid direct import
    CartClass = CARTRIDGE_TYPES[3]

    def _make_banks(self, num_banks: int = 4) -> list[bytes]:
        """Create test banks with unique signatures."""
        banks = []
        for i in range(num_banks):
            bank = bytearray(ROML_SIZE + ROMH_SIZE)  # 16KB per bank
            # Put bank number at start of ROML
            bank[0] = 0x30 + i
            # Put bank number at start of ROMH (offset 0x2000)
            bank[ROML_SIZE] = 0x40 + i
            # Put signature at IO1 offset ($1E00)
            bank[0x1E00] = 0x50 + i
            # Put signature at IO2 offset ($1F00)
            bank[0x1F00] = 0x60 + i
            banks.append(bytes(bank))
        return banks

    def test_hardware_type(self):
        """FinalCartridgeIIICartridge should have hardware type 3."""
        assert self.CartClass.HARDWARE_TYPE == 3

    def test_initial_state_16kb_mode(self):
        """FC3 should start in 16KB mode (EXROM=0, GAME=0)."""
        banks = self._make_banks()
        cart = self.CartClass(banks, name="Test FC3")

        assert cart.exrom is False, "FC3 should have EXROM active (False)"
        assert cart.game is False, "FC3 should have GAME active (False) = 16KB mode"
        assert cart._current_bank == 0
        assert cart._register_hidden is False

    def test_bank_switching(self):
        """Writing bank bits to $DFFF should switch banks."""
        banks = self._make_banks()
        cart = self.CartClass(banks, name="Test FC3")

        # Initial state: bank 0
        assert cart.read_roml(ROML_START) == 0x30  # Bank 0 ROML

        # Switch to bank 1 (bits 0-1 = 01, keep EXROM/GAME active)
        cart.write_io2(0xDFFF, 0x01)
        assert cart._current_bank == 1
        assert cart.read_roml(ROML_START) == 0x31

        # Switch to bank 2
        cart.write_io2(0xDFFF, 0x02)
        assert cart._current_bank == 2
        assert cart.read_roml(ROML_START) == 0x32

        # Switch to bank 3
        cart.write_io2(0xDFFF, 0x03)
        assert cart._current_bank == 3
        assert cart.read_roml(ROML_START) == 0x33

    def test_romh_access(self):
        """ROMH should be accessible in 16KB mode."""
        banks = self._make_banks()
        cart = self.CartClass(banks, name="Test FC3")

        # ROMH starts at offset 0x2000 in the 16KB bank
        assert cart.read_romh(ROMH_START) == 0x40  # Bank 0 ROMH

        # Switch to bank 2 and check ROMH
        cart.write_io2(0xDFFF, 0x02)
        assert cart.read_romh(ROMH_START) == 0x42

    def test_io1_mirrors_rom(self):
        """IO1 should mirror ROM offset $1E00-$1EFF of current bank."""
        banks = self._make_banks()
        cart = self.CartClass(banks, name="Test FC3")

        # IO1 mirrors $1E00-$1EFF
        assert cart.read_io1(IO1_START) == 0x50  # Bank 0

        cart.write_io2(0xDFFF, 0x02)  # Switch to bank 2
        assert cart.read_io1(IO1_START) == 0x52

    def test_io2_mirrors_rom(self):
        """IO2 should mirror ROM offset $1F00-$1FFF of current bank."""
        banks = self._make_banks()
        cart = self.CartClass(banks, name="Test FC3")

        # IO2 mirrors $1F00-$1FFF (reading, not the control register address)
        assert cart.read_io2(IO2_START) == 0x60  # Bank 0

        cart.write_io2(0xDFFF, 0x03)  # Switch to bank 3
        assert cart.read_io2(IO2_START) == 0x63

    def test_control_register_only_at_dfff(self):
        """Only writes to $DFFF should affect the control register."""
        banks = self._make_banks()
        cart = self.CartClass(banks, name="Test FC3")

        # Write to $DF00 should not change bank
        cart.write_io2(0xDF00, 0x03)
        assert cart._current_bank == 0

        # Write to $DFFF should change bank
        cart.write_io2(0xDFFF, 0x03)
        assert cart._current_bank == 3

    def test_hide_register(self):
        """Setting bit 7 should hide the control register until reset."""
        banks = self._make_banks()
        cart = self.CartClass(banks, name="Test FC3")

        # Switch to bank 1
        cart.write_io2(0xDFFF, 0x01)
        assert cart._current_bank == 1

        # Hide register (bit 7 set)
        cart.write_io2(0xDFFF, 0x82)  # 0x80 | 0x02
        assert cart._register_hidden is True
        assert cart._current_bank == 2  # Bank changed before hiding

        # Further writes should be ignored
        cart.write_io2(0xDFFF, 0x03)
        assert cart._current_bank == 2  # Still bank 2

    def test_reset_unhides_register(self):
        """Reset should unhide the control register."""
        banks = self._make_banks()
        cart = self.CartClass(banks, name="Test FC3")

        # Hide register
        cart.write_io2(0xDFFF, 0x82)
        assert cart._register_hidden is True

        # Reset
        cart.reset()

        assert cart._register_hidden is False
        assert cart._current_bank == 0
        assert cart.exrom is False
        assert cart.game is False

    def test_exrom_game_control(self):
        """Bits 4-5 should directly control EXROM and GAME."""
        banks = self._make_banks()
        cart = self.CartClass(banks, name="Test FC3")

        # Initial: 16KB mode (EXROM=0, GAME=0)
        assert cart.exrom is False
        assert cart.game is False

        # Set GAME high (bit 5 = 1) -> 8KB mode
        cart.write_io2(0xDFFF, 0x20)
        assert cart.exrom is False
        assert cart.game is True

        # Set EXROM high (bit 4 = 1) -> cartridge invisible
        cart.write_io2(0xDFFF, 0x30)
        assert cart.exrom is True
        assert cart.game is True

        # Both active (EXROM=0, GAME=0) -> back to 16KB
        cart.write_io2(0xDFFF, 0x00)
        assert cart.exrom is False
        assert cart.game is False

    def test_nmi_line(self):
        """Bit 6 controls NMI line (0 = active/trigger NMI)."""
        banks = self._make_banks()
        cart = self.CartClass(banks, name="Test FC3")

        # Initially NMI line is high (inactive)
        assert cart._nmi_line is True
        assert cart.nmi_pending is False

        # Set NMI line low (bit 6 = 0)
        cart.write_io2(0xDFFF, 0x00)
        assert cart._nmi_line is False
        assert cart.nmi_pending is True

        # Set NMI line high (bit 6 = 1)
        cart.write_io2(0xDFFF, 0x40)
        assert cart._nmi_line is True
        assert cart.nmi_pending is False


class TestFinalCartridgeICartridge:
    """Tests for FinalCartridgeICartridge (Type 13).

    Final Cartridge I is a simple 16KB utility cartridge with:
    - IO1 access ($DE00-$DEFF) disables cartridge
    - IO2 access ($DF00-$DFFF) enables cartridge

    Ref: https://rr.pokefinder.org/wiki/Final_Cartridge
    """

    # Get class from registry to avoid direct import
    CartClass = CARTRIDGE_TYPES[13]

    def test_hardware_type(self):
        """FinalCartridgeICartridge should have hardware type 13."""
        assert self.CartClass.HARDWARE_TYPE == 13

    def test_initial_state_8kb_mode(self):
        """FC1 with only ROML should start in 8KB mode (EXROM=0, GAME=1)."""
        roml = bytes(ROML_SIZE)
        cart = self.CartClass(roml, name="Test FC1 8KB")

        assert cart.exrom is False, "FC1 should have EXROM active (False)"
        assert cart.game is True, "FC1 8KB should have GAME inactive (True) = 8KB mode"
        assert cart._enabled is True

    def test_initial_state_16kb_mode(self):
        """FC1 with ROML + ROMH should start in 16KB mode (EXROM=0, GAME=0)."""
        roml = bytes(ROML_SIZE)
        romh = bytes(ROMH_SIZE)
        cart = self.CartClass(roml, romh, name="Test FC1 16KB")

        assert cart.exrom is False, "FC1 should have EXROM active (False)"
        assert cart.game is False, "FC1 16KB should have GAME active (False) = 16KB mode"
        assert cart._enabled is True

    def test_io1_access_disables_cartridge(self):
        """Any access to IO1 should disable the cartridge."""
        roml = bytearray(ROML_SIZE)
        roml[0] = 0x42
        cart = self.CartClass(bytes(roml), name="Test FC1")

        # Initially enabled
        assert cart._enabled is True
        assert cart.read_roml(ROML_START) == 0x42

        # Read from IO1 disables
        cart.read_io1(IO1_START)
        assert cart._enabled is False
        assert cart.exrom is True
        assert cart.game is True
        assert cart.read_roml(ROML_START) == 0xFF  # ROM invisible

    def test_io1_write_disables_cartridge(self):
        """Write to IO1 should also disable the cartridge."""
        roml = bytes(ROML_SIZE)
        cart = self.CartClass(roml, name="Test FC1")

        assert cart._enabled is True

        cart.write_io1(IO1_START, 0x00)
        assert cart._enabled is False
        assert cart.exrom is True

    def test_io2_access_enables_cartridge(self):
        """Any access to IO2 should enable the cartridge."""
        roml = bytearray(ROML_SIZE)
        roml[0] = 0x42
        cart = self.CartClass(bytes(roml), name="Test FC1")

        # Disable first
        cart.read_io1(IO1_START)
        assert cart._enabled is False

        # Read from IO2 enables
        cart.read_io2(IO2_START)
        assert cart._enabled is True
        assert cart.exrom is False
        assert cart.read_roml(ROML_START) == 0x42

    def test_io2_write_enables_cartridge(self):
        """Write to IO2 should also enable the cartridge."""
        roml = bytes(ROML_SIZE)
        cart = self.CartClass(roml, name="Test FC1")

        # Disable first
        cart.write_io1(IO1_START, 0x00)
        assert cart._enabled is False

        # Write to IO2 enables
        cart.write_io2(IO2_START, 0x00)
        assert cart._enabled is True
        assert cart.exrom is False

    def test_roml_read_returns_data(self):
        """ROML should return ROM data when enabled."""
        roml = bytearray(ROML_SIZE)
        roml[0] = 0x11
        roml[0x1FFF] = 0x22
        cart = self.CartClass(bytes(roml), name="Test FC1")

        assert cart.read_roml(ROML_START) == 0x11
        assert cart.read_roml(ROML_START + 0x1FFF) == 0x22

    def test_romh_read_returns_data(self):
        """ROMH should return ROM data when enabled (16KB mode)."""
        roml = bytes(ROML_SIZE)
        romh = bytearray(ROMH_SIZE)
        romh[0] = 0x33
        romh[0x1FFF] = 0x44
        cart = self.CartClass(roml, bytes(romh), name="Test FC1 16KB")

        assert cart.read_romh(ROMH_START) == 0x33
        assert cart.read_romh(ROMH_START + 0x1FFF) == 0x44

    def test_romh_returns_ff_when_not_present(self):
        """ROMH should return $FF when cart only has ROML."""
        roml = bytes(ROML_SIZE)
        cart = self.CartClass(roml, name="Test FC1 8KB")

        assert cart.read_romh(ROMH_START) == 0xFF

    def test_reset_re_enables_cartridge(self):
        """Reset should re-enable the cartridge."""
        roml = bytearray(ROML_SIZE)
        roml[0] = 0x42
        cart = self.CartClass(bytes(roml), name="Test FC1")

        # Disable
        cart.read_io1(IO1_START)
        assert cart._enabled is False

        # Reset
        cart.reset()

        assert cart._enabled is True
        assert cart.exrom is False
        assert cart.read_roml(ROML_START) == 0x42

    def test_toggle_enable_disable(self):
        """Should be able to toggle enable/disable repeatedly."""
        roml = bytearray(ROML_SIZE)
        roml[0] = 0x42
        cart = self.CartClass(bytes(roml), name="Test FC1")

        # Toggle several times
        for _ in range(3):
            cart.read_io1(IO1_START)  # Disable
            assert cart._enabled is False
            assert cart.read_roml(ROML_START) == 0xFF

            cart.read_io2(IO2_START)  # Enable
            assert cart._enabled is True
            assert cart.read_roml(ROML_START) == 0x42


@requires_c64_roms
class TestEpyxFastloadCartridge:
    """Tests for EpyxFastloadCartridge (Type 10).

    Epyx FastLoad cartridges use a capacitor-based enable/disable mechanism:
    - Reading ROML or IO1 enables the cartridge
    - After ~512 cycles without access, cartridge disables
    - IO2 ($DF00-$DFFF) always shows last 256 bytes of ROM
    """

    # Get class from registry to avoid direct import
    CartClass = CARTRIDGE_TYPES[10]

    def test_hardware_type(self):
        """EpyxFastloadCartridge should have hardware type 10."""
        assert self.CartClass.HARDWARE_TYPE == 10

    def test_initial_state_8kb_mode(self):
        """Epyx FastLoad should start in 8KB mode (EXROM=0, GAME=1)."""
        rom = bytes(ROML_SIZE)
        cart = self.CartClass(rom, name="Test Epyx")

        assert cart.exrom is False, "Should have EXROM active (False)"
        assert cart.game is True, "Should have GAME inactive (True) = 8KB mode"
        assert cart._enabled is True

    def test_roml_read_enables_cartridge(self):
        """Reading from ROML should enable the cartridge."""
        rom = bytearray(ROML_SIZE)
        rom[0] = 0x42
        cart = self.CartClass(bytes(rom), name="Test Epyx")

        # Manually disable
        cart._enabled = False
        cart._exrom = True

        # Reading ROML should enable
        value = cart.read_roml(ROML_START)
        assert cart._enabled is True
        assert cart.exrom is False
        assert value == 0x42

    def test_io1_read_enables_cartridge(self):
        """Reading from IO1 should enable the cartridge."""
        rom = bytes(ROML_SIZE)
        cart = self.CartClass(rom, name="Test Epyx")

        # Manually disable
        cart._enabled = False
        cart._exrom = True

        # Reading IO1 should enable
        cart.read_io1(0xDE00)
        assert cart._enabled is True
        assert cart.exrom is False

    def test_io2_always_visible(self):
        """IO2 should always show last 256 bytes of ROM, even when disabled."""
        rom = bytearray(ROML_SIZE)
        # Put signature in last 256 bytes
        rom[0x1F00] = 0xAA  # First byte of IO2 region
        rom[0x1FFF] = 0xBB  # Last byte of IO2 region
        cart = self.CartClass(bytes(rom), name="Test Epyx")

        # IO2 visible when enabled
        assert cart.read_io2(0xDF00) == 0xAA
        assert cart.read_io2(0xDFFF) == 0xBB

        # Manually disable cartridge
        cart._enabled = False
        cart._exrom = True

        # IO2 should STILL be visible
        assert cart.read_io2(0xDF00) == 0xAA
        assert cart.read_io2(0xDFFF) == 0xBB

    def test_timeout_disables_cartridge(self):
        """Cartridge should disable after timeout cycles."""
        rom = bytes(ROML_SIZE)
        cart = self.CartClass(rom, name="Test Epyx")

        assert cart._enabled is True

        # Simulate timeout
        cart.tick(cart.TIMEOUT_CYCLES)

        assert cart._enabled is False
        assert cart.exrom is True

    def test_reset_re_enables_cartridge(self):
        """Reset should re-enable the cartridge."""
        rom = bytes(ROML_SIZE)
        cart = self.CartClass(rom, name="Test Epyx")

        # Disable via timeout
        cart.tick(cart.TIMEOUT_CYCLES)
        assert cart._enabled is False

        # Reset
        cart.reset()

        assert cart._enabled is True
        assert cart.exrom is False
        assert cart.game is True

    def test_access_resets_timeout(self):
        """Reading ROML/IO1 should reset the timeout counter."""
        rom = bytes(ROML_SIZE)
        cart = self.CartClass(rom, name="Test Epyx")

        # Advance partway through timeout
        cart.tick(cart.TIMEOUT_CYCLES - 10)
        assert cart._enabled is True

        # Read ROML - should reset counter
        cart.read_roml(ROML_START)
        assert cart._cycles_since_access == 0

        # Now timeout should take full count again
        cart.tick(cart.TIMEOUT_CYCLES - 1)
        assert cart._enabled is True  # Still enabled

        cart.tick(1)
        assert cart._enabled is False  # Now disabled


@requires_c64_roms
class TestStaticROMCartridge:
    """Tests for StaticROMCartridge (Type 0)."""

    def test_8k_cartridge_exrom_game(self):
        """8KB cartridge should have EXROM=0, GAME=1."""
        roml_data = bytes(ROML_SIZE)
        cart = StaticROMCartridge(roml_data, romh_data=None, name="Test 8K")

        # EXROM=False means active (0), GAME=True means inactive (1)
        assert cart.exrom is False, "8KB cart should have EXROM active (False)"
        assert cart.game is True, "8KB cart should have GAME inactive (True)"

    def test_16k_cartridge_exrom_game(self):
        """16KB cartridge should have EXROM=0, GAME=0."""
        roml_data = bytes(ROML_SIZE)
        romh_data = bytes(ROMH_SIZE)
        cart = StaticROMCartridge(roml_data, romh_data=romh_data, name="Test 16K")

        # Both EXROM and GAME should be active (False)
        assert cart.exrom is False, "16KB cart should have EXROM active (False)"
        assert cart.game is False, "16KB cart should have GAME active (False)"

    def test_ultimax_cartridge_exrom_game(self):
        """Ultimax cartridge should have EXROM=1, GAME=0."""
        ultimax_romh_data = bytes(ULTIMAX_ROMH_SIZE)
        cart = StaticROMCartridge(ultimax_romh_data=ultimax_romh_data, name="Test Ultimax")

        # EXROM=True (inactive), GAME=False (active) = Ultimax mode
        assert cart.exrom is True, "Ultimax cart should have EXROM inactive (True)"
        assert cart.game is False, "Ultimax cart should have GAME active (False)"

    def test_ultimax_with_roml_exrom_game(self):
        """Ultimax cartridge with optional ROML should have EXROM=1, GAME=0."""
        roml_data = bytes(ROML_SIZE)
        ultimax_romh_data = bytes(ULTIMAX_ROMH_SIZE)
        cart = StaticROMCartridge(
            roml_data=roml_data,
            ultimax_romh_data=ultimax_romh_data,
            name="Test Ultimax+ROML"
        )

        assert cart.exrom is True, "Ultimax cart should have EXROM inactive (True)"
        assert cart.game is False, "Ultimax cart should have GAME active (False)"

    def test_read_ultimax_romh_returns_data(self):
        """read_ultimax_romh should return correct byte from ROM."""
        ultimax_romh_data = bytearray(ULTIMAX_ROMH_SIZE)
        ultimax_romh_data[0] = 0x12
        ultimax_romh_data[0x100] = 0x34
        ultimax_romh_data[ULTIMAX_ROMH_SIZE - 1] = 0x56

        cart = StaticROMCartridge(ultimax_romh_data=bytes(ultimax_romh_data))

        assert cart.read_ultimax_romh(ULTIMAX_ROMH_START) == 0x12
        assert cart.read_ultimax_romh(ULTIMAX_ROMH_START + 0x100) == 0x34
        assert cart.read_ultimax_romh(ULTIMAX_ROMH_START + ULTIMAX_ROMH_SIZE - 1) == 0x56

    def test_read_ultimax_romh_returns_ff_when_not_present(self):
        """read_ultimax_romh should return 0xFF when no Ultimax ROM data."""
        roml_data = bytes(ROML_SIZE)
        cart = StaticROMCartridge(roml_data=roml_data)

        assert cart.read_ultimax_romh(ULTIMAX_ROMH_START) == 0xFF
        assert cart.read_ultimax_romh(ULTIMAX_ROMH_START + 0x100) == 0xFF

    def test_read_roml_returns_data(self):
        """read_roml should return the correct byte from ROM."""
        roml_data = bytearray(ROML_SIZE)
        roml_data[0] = 0xAB
        roml_data[0x100] = 0xCD
        roml_data[ROML_SIZE - 1] = 0xEF

        cart = StaticROMCartridge(bytes(roml_data))

        assert cart.read_roml(ROML_START) == 0xAB
        assert cart.read_roml(ROML_START + 0x100) == 0xCD
        assert cart.read_roml(ROML_START + ROML_SIZE - 1) == 0xEF

    def test_read_romh_returns_data_when_present(self):
        """read_romh should return data when ROMH is present."""
        roml_data = bytes(ROML_SIZE)
        romh_data = bytearray(ROMH_SIZE)
        romh_data[0] = 0x12
        romh_data[0x100] = 0x34
        romh_data[ROMH_SIZE - 1] = 0x56

        cart = StaticROMCartridge(roml_data, romh_data=bytes(romh_data))

        assert cart.read_romh(ROMH_START) == 0x12
        assert cart.read_romh(ROMH_START + 0x100) == 0x34
        assert cart.read_romh(ROMH_START + ROMH_SIZE - 1) == 0x56

    def test_read_romh_returns_ff_when_not_present(self):
        """read_romh should return 0xFF when no ROMH data."""
        roml_data = bytes(ROML_SIZE)
        cart = StaticROMCartridge(roml_data, romh_data=None)

        assert cart.read_romh(ROMH_START) == 0xFF
        assert cart.read_romh(ROMH_START + 0x100) == 0xFF

    def test_io_regions_return_ff(self):
        """I/O regions should return 0xFF (open bus) for static ROM cart."""
        cart = StaticROMCartridge(bytes(ROML_SIZE))

        assert cart.read_io1(0xDE00) == 0xFF
        assert cart.read_io1(0xDEFF) == 0xFF
        assert cart.read_io2(0xDF00) == 0xFF
        assert cart.read_io2(0xDFFF) == 0xFF


@requires_c64_roms
class TestErrorCartridge:
    """Tests for ErrorCartridge."""

    def test_error_cartridge_stores_original_type(self):
        """ErrorCartridge should store the original unsupported type."""
        roml_data = bytes(ROML_SIZE)
        cart = ErrorCartridge(roml_data, original_type=32, original_name="EasyFlash")

        assert cart.original_type == 32
        assert cart.original_name == "EasyFlash"

    def test_error_cartridge_name_prefix(self):
        """ErrorCartridge name should have 'Error:' prefix."""
        roml_data = bytes(ROML_SIZE)
        cart = ErrorCartridge(roml_data, original_type=5, original_name="Ocean")

        assert cart.name.startswith("Error:")


@requires_c64_roms
class TestCreateCartridgeFactory:
    """Tests for the create_cartridge factory function."""

    def test_create_type_0_returns_static_rom_cartridge(self):
        """create_cartridge with type 0 should return StaticROMCartridge."""
        roml_data = bytes(ROML_SIZE)
        cart = create_cartridge(StaticROMCartridge.HARDWARE_TYPE, roml_data, name="Test")

        assert isinstance(cart, StaticROMCartridge)

    def test_create_type_1_returns_action_replay_cartridge(self):
        """create_cartridge with type 1 should return ActionReplayCartridge."""
        action_replay_class = CARTRIDGE_TYPES[1]
        banks = [bytes(ROML_SIZE) for _ in range(4)]  # 4 x 8KB banks
        cart = create_cartridge(
            action_replay_class.HARDWARE_TYPE,
            banks=banks,
            name="Test Action Replay"
        )

        assert isinstance(cart, action_replay_class)
        assert cart.num_banks == 4

    def test_create_unsupported_type_raises_value_error(self):
        """create_cartridge with unsupported type should raise ValueError."""
        roml_data = bytes(ROML_SIZE)

        # Use raw numbers here since these types don't have classes yet
        with pytest.raises(ValueError, match="Unsupported cartridge hardware type"):
            create_cartridge(2, roml_data, name="Test")  # KCS Power - not yet implemented

        with pytest.raises(ValueError, match="Unsupported cartridge hardware type"):
            create_cartridge(32, roml_data, name="Test")  # EasyFlash - not yet implemented


@requires_c64_roms
class TestCartridgeExecution:
    """Parameterized tests for cartridge execution.

    Tests that each cartridge variant loads and executes correctly,
    running the embedded self-test code and verifying it passes.
    """

    # Fail counter protocol constants (must match scripts/create_test_carts.py)
    FAIL_COUNTER_ZP = 0x02
    TESTS_COMPLETE_BIT = 0x80
    FAIL_COUNT_MASK = 0x7F
    MAX_CYCLES = 5_000_000  # 5M cycles should be enough for any test cart

    @pytest.fixture
    def c64(self):
        """Create a C64 instance with ROMs loaded."""
        return C64(rom_dir=C64_ROMS_DIR, display_mode="headless")

    def _run_test_cartridge(self, c64, crt_path: Path) -> tuple[bool, int]:
        """Run a test cartridge and return (tests_complete, fail_count)."""
        from mos6502.errors import CPUCycleExhaustionError

        c64.load_cartridge(crt_path)
        c64.reset()

        CHUNK_SIZE = 100_000
        cycles_run = 0

        while cycles_run < self.MAX_CYCLES:
            try:
                c64.cpu.execute(cycles=CHUNK_SIZE)
            except CPUCycleExhaustionError:
                pass

            cycles_run += CHUNK_SIZE

            fail_counter = c64.memory.read(self.FAIL_COUNTER_ZP)
            if fail_counter & self.TESTS_COMPLETE_BIT:
                fail_count = fail_counter & self.FAIL_COUNT_MASK
                return True, fail_count

        fail_counter = c64.memory.read(self.FAIL_COUNTER_ZP)
        return False, fail_counter & self.FAIL_COUNT_MASK

    @pytest.mark.parametrize("test_case", CRT_TEST_CASES, ids=CRT_TEST_IDS)
    def test_cartridge_executes(self, c64, test_case: CartridgeTestCase):
        """Test that cartridge loads and executes, passing all self-tests."""
        if not test_case.crt_path.exists():
            pytest.skip(f"Test fixture not found: {test_case.crt_path.name}")

        tests_complete, fail_count = self._run_test_cartridge(c64, test_case.crt_path)

        assert tests_complete, (
            f"{test_case.cart_type.name} {test_case.variant.description or ''} "
            f"test cartridge did not complete within max cycles"
        )
        assert fail_count == 0, (
            f"{test_case.cart_type.name} {test_case.variant.description or ''} "
            f"test cartridge reported {fail_count} failures"
        )


@requires_c64_roms
class TestCartridgeLoading:
    """Parameterized tests for cartridge loading.

    Tests that each cartridge variant loads correctly from both:
    - CRT files (all cartridge types)
    - BIN files (Type 0 only, with auto-detection)
    """

    @pytest.fixture
    def c64_factory(self):
        """Factory to create fresh C64 instances for each test."""
        def _create():
            return C64(rom_dir=C64_ROMS_DIR, display_mode="headless")
        return _create

    @pytest.mark.parametrize("test_case", CRT_TEST_CASES, ids=CRT_TEST_IDS)
    def test_crt_cartridge_loads(self, c64_factory, test_case: CartridgeTestCase):
        """Test that cartridge CRT file loads correctly."""
        if not test_case.crt_path.exists():
            pytest.skip(f"Test fixture not found: {test_case.crt_path.name}")

        c64 = c64_factory()
        c64.load_cartridge(test_case.crt_path)

        # Verify cartridge loaded (not an error cartridge)
        assert c64.memory.cartridge is not None, (
            f"{test_case.cart_type.name} {test_case.variant.description or ''}: "
            f"no cartridge loaded"
        )
        assert not isinstance(c64.memory.cartridge, ErrorCartridge), (
            f"{test_case.cart_type.name} {test_case.variant.description or ''}: "
            f"loaded as ErrorCartridge"
        )
        assert c64.cartridge_type != "error", (
            f"{test_case.cart_type.name} {test_case.variant.description or ''}: "
            f"cartridge_type is 'error'"
        )

    @pytest.mark.parametrize("test_case", BIN_TEST_CASES, ids=BIN_TEST_IDS)
    def test_bin_cartridge_loads(self, c64_factory, test_case: BinTestCase):
        """Test that raw .bin cartridge loads with correct auto-detection.

        Only Type 0 (Normal) supports raw .bin loading since other types
        require CRT metadata for bank configuration.
        """
        if not test_case.bin_path.exists():
            pytest.skip(f"Test fixture not found: {test_case.bin_path.name}")

        c64 = c64_factory()
        c64.load_cartridge(test_case.bin_path)

        assert c64.cartridge_type == test_case.expected_cart_type
        assert c64.memory.cartridge is not None
        assert isinstance(c64.memory.cartridge, StaticROMCartridge)

        # Verify EXROM/GAME match expected detection values
        # (may differ from variant when raw .bin can't distinguish modes)
        expected_exrom = bool(test_case.expected_exrom)
        expected_game = bool(test_case.expected_game)
        assert c64.memory.cartridge.exrom is expected_exrom
        assert c64.memory.cartridge.game is expected_game


@requires_c64_roms
class TestUnimplementedCartridgeTypes:
    """Negative tests for unimplemented cartridge types.

    These tests verify that cartridge types which are not yet implemented
    correctly load as ErrorCartridge instances, displaying an error screen
    with the unsupported hardware type information.
    """

    @pytest.fixture
    def c64_factory(self):
        """Factory to create fresh C64 instances for each test."""
        def _create():
            return C64(rom_dir=C64_ROMS_DIR, display_mode="headless")
        return _create

    @pytest.mark.parametrize("test_case", UNIMPLEMENTED_TEST_CASES, ids=UNIMPLEMENTED_TEST_IDS)
    def test_unimplemented_cartridge_loads_as_error(self, c64_factory, test_case: UnimplementedTestCase):
        """Test that unimplemented cartridge type loads as ErrorCartridge."""
        if not test_case.crt_path.exists():
            pytest.skip(f"Test fixture not found: {test_case.crt_path.name}")

        c64 = c64_factory()
        c64.load_cartridge(test_case.crt_path)

        # Should load as ErrorCartridge since the mapper is not implemented
        assert c64.memory.cartridge is not None, (
            f"Type {test_case.hw_type}: no cartridge loaded"
        )
        assert isinstance(c64.memory.cartridge, ErrorCartridge), (
            f"Type {test_case.hw_type}: expected ErrorCartridge, "
            f"got {type(c64.memory.cartridge).__name__}"
        )
        assert c64.cartridge_type == "error", (
            f"Type {test_case.hw_type}: expected cartridge_type='error', "
            f"got '{c64.cartridge_type}'"
        )

        # Verify the ErrorCartridge captured the original hardware type
        assert c64.memory.cartridge.original_type == test_case.hw_type, (
            f"Type {test_case.hw_type}: ErrorCartridge.original_type mismatch"
        )


class TestCRTHeaderParsing:
    """Tests for CRT header parsing."""

    @requires_c64_roms
    def test_hardware_type_correctly_parsed(self):
        """Hardware type should be correctly extracted from CRT header."""
        for hw_type in [0, 1, 5, 32, 85]:
            crt_data = self._create_minimal_crt(hardware_type=hw_type)
            parsed_type = int.from_bytes(crt_data[0x16:0x18], "big")
            assert parsed_type == hw_type

    @requires_c64_roms
    def test_exrom_game_correctly_parsed(self):
        """EXROM and GAME lines should be correctly extracted from CRT header."""
        # Test various EXROM/GAME combinations
        for exrom, game in [(0, 0), (0, 1), (1, 0), (1, 1)]:
            crt_data = self._create_minimal_crt(exrom=exrom, game=game)
            assert crt_data[0x18] == exrom
            assert crt_data[0x19] == game

    @requires_c64_roms
    def test_cart_name_correctly_parsed(self):
        """Cartridge name should be correctly extracted from CRT header."""
        crt_data = self._create_minimal_crt(name="MY TEST CART")
        name_bytes = crt_data[0x20:0x40].rstrip(b"\x00")
        assert name_bytes == b"MY TEST CART"

    def _create_minimal_crt(
        self,
        hardware_type: int = 0,
        exrom: int = 0,
        game: int = 1,
        name: str = "TEST",
    ) -> bytes:
        """Create a minimal CRT file for testing header parsing."""
        header = bytearray(64)
        header[0:16] = b"C64 CARTRIDGE   "
        header[0x10:0x14] = (64).to_bytes(4, "big")  # Header length
        header[0x14] = 1  # Version hi
        header[0x15] = 0  # Version lo
        header[0x16:0x18] = hardware_type.to_bytes(2, "big")
        header[0x18] = exrom
        header[0x19] = game
        name_bytes = name.encode("ascii")[:32].ljust(32, b"\x00")
        header[0x20:0x40] = name_bytes

        # Add a minimal CHIP packet with 8KB ROM
        chip = bytearray(16)
        chip[0:4] = b"CHIP"
        chip[4:8] = (16 + ROML_SIZE).to_bytes(4, "big")  # Packet length
        chip[8:10] = (0).to_bytes(2, "big")  # Type (ROM)
        chip[10:12] = (0).to_bytes(2, "big")  # Bank
        chip[12:14] = ROML_START.to_bytes(2, "big")  # Load address
        chip[14:16] = ROML_SIZE.to_bytes(2, "big")  # ROM size

        rom_data = bytes(ROML_SIZE)

        return bytes(header) + bytes(chip) + rom_data


class TestErrorCartridgeFiles:
    """Tests for pre-generated error cartridge files."""

    ERROR_CART_DIR = (
        Path(__file__).parent.parent.parent
        / "systems"
        / "c64"
        / "cartridges"
        / "error_cartridges"
    )

    @requires_c64_roms
    @pytest.mark.parametrize("hw_type", range(1, 86), ids=cart_type_id)
    def test_error_cartridge_file_exists(self, hw_type):
        """Each unsupported type should have a pre-generated error cartridge."""
        safe_name = _get_safe_name(hw_type)
        filename = f"error_cart_type_{hw_type:02d}_{safe_name}.bin"
        path = self.ERROR_CART_DIR / filename

        assert path.exists(), f"Error cartridge missing for type {hw_type}: {filename}"

    @requires_c64_roms
    @pytest.mark.parametrize("hw_type", range(1, 86), ids=cart_type_id)
    def test_error_cartridge_file_size(self, hw_type):
        """Error cartridge files should be exactly 8KB."""
        safe_name = _get_safe_name(hw_type)
        filename = f"error_cart_type_{hw_type:02d}_{safe_name}.bin"
        path = self.ERROR_CART_DIR / filename

        if not path.exists():
            pytest.skip(f"Error cartridge not found: {filename}")

        size = path.stat().st_size
        assert size == ROML_SIZE, f"Error cart {filename} should be {ROML_SIZE} bytes, got {size}"

    @requires_c64_roms
    @pytest.mark.parametrize("hw_type", range(1, 86), ids=cart_type_id)
    def test_error_cartridge_has_cbm80_signature(self, hw_type):
        """Error cartridge ROMs should have valid CBM80 signature."""
        safe_name = _get_safe_name(hw_type)
        filename = f"error_cart_type_{hw_type:02d}_{safe_name}.bin"
        path = self.ERROR_CART_DIR / filename

        if not path.exists():
            pytest.skip(f"Error cartridge not found: {filename}")

        data = path.read_bytes()

        # CBM80 signature at offset 4-8 (values are PETSCII with high bit set)
        # 'C' = 0xC3, 'B' = 0xC2, 'M' = 0xCD, '8' = 0x38, '0' = 0x30
        expected_sig = bytes([0xC3, 0xC2, 0xCD, 0x38, 0x30])
        actual_sig = data[4:9]

        assert actual_sig == expected_sig, \
            f"Error cart {filename} missing CBM80 signature: got {actual_sig.hex()}"


class TestMapperTestCartridgeFiles:
    """Tests for mapper test cartridge CRT files."""

    # Types with multiple variants - map hw_type to list of variant filenames
    MULTI_VARIANT_TYPES = {
        0: [  # Normal cartridge: 8k, 16k, 16k_single_chip, ultimax, ultimax_with_roml
            "test_cart_type_00_normal_cartridge_8k.crt",
            "test_cart_type_00_normal_cartridge_16k.crt",
            "test_cart_type_00_normal_cartridge_16k_single_chip.crt",
            "test_cart_type_00_normal_cartridge_ultimax.crt",
            "test_cart_type_00_normal_cartridge_ultimax_with_roml.crt",
        ],
        5: [  # Ocean type 1: 128k, 256k, 512k
            "test_cart_type_05_ocean_type_1_128k.crt",
            "test_cart_type_05_ocean_type_1_256k.crt",
            "test_cart_type_05_ocean_type_1_512k.crt",
        ],
        15: [  # C64 Game System: 64k, 128k, 512k
            "test_cart_type_15_c64_game_system_system_3_64k.crt",
            "test_cart_type_15_c64_game_system_system_3_128k.crt",
            "test_cart_type_15_c64_game_system_system_3_512k.crt",
        ],
        17: [  # Dinamic: 128k only
            "test_cart_type_17_dinamic_128k.crt",
        ],
        19: [  # Magic Desk: 32k, 64k, 128k, 256k, 512k
            "test_cart_type_19_magic_desk_domark_hes_australia_32k.crt",
            "test_cart_type_19_magic_desk_domark_hes_australia_64k.crt",
            "test_cart_type_19_magic_desk_domark_hes_australia_128k.crt",
            "test_cart_type_19_magic_desk_domark_hes_australia_256k.crt",
            "test_cart_type_19_magic_desk_domark_hes_australia_512k.crt",
        ],
    }

    # Legacy alias for backward compatibility
    TYPE_0_VARIANTS = MULTI_VARIANT_TYPES[0]

    @requires_c64_roms
    @pytest.mark.parametrize("hw_type", range(0, 86), ids=cart_type_id)
    def test_mapper_test_cartridge_exists(self, hw_type):
        """Each hardware type should have a test CRT file."""
        if hw_type in self.MULTI_VARIANT_TYPES:
            # Types with multiple variants - check all variant files exist
            for variant in self.MULTI_VARIANT_TYPES[hw_type]:
                path = CARTRIDGE_TYPES_DIR / variant
                assert path.exists(), f"Type {hw_type} variant missing: {variant}"
            return

        type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, f"unknown_{hw_type}")
        safe_name = (
            type_name.lower()
            .replace(" ", "_")
            .replace(",", "")
            .replace("/", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
        )
        filename = f"test_cart_type_{hw_type:02d}_{safe_name}.crt"
        path = CARTRIDGE_TYPES_DIR / filename

        assert path.exists(), f"Mapper test CRT missing for type {hw_type}: {filename}"

    @requires_c64_roms
    @pytest.mark.parametrize("hw_type", range(0, 86), ids=cart_type_id)
    def test_mapper_test_cartridge_has_correct_hardware_type(self, hw_type):
        """Mapper test CRT files should have correct hardware type in header."""
        if hw_type in self.MULTI_VARIANT_TYPES:
            # Types with multiple variants - check all of them
            for variant in self.MULTI_VARIANT_TYPES[hw_type]:
                path = CARTRIDGE_TYPES_DIR / variant
                if not path.exists():
                    pytest.skip(f"Type {hw_type} variant not found: {variant}")

                data = path.read_bytes()
                assert data[:16] == b"C64 CARTRIDGE   ", f"Invalid CRT signature in {variant}"
                parsed_type = int.from_bytes(data[0x16:0x18], "big")
                assert parsed_type == hw_type, f"CRT {variant} has wrong hardware type: expected {hw_type}, got {parsed_type}"
            return

        type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, f"unknown_{hw_type}")
        safe_name = (
            type_name.lower()
            .replace(" ", "_")
            .replace(",", "")
            .replace("/", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(".", "")
        )
        filename = f"test_cart_type_{hw_type:02d}_{safe_name}.crt"
        path = CARTRIDGE_TYPES_DIR / filename

        if not path.exists():
            pytest.skip(f"Test CRT not found: {filename}")

        data = path.read_bytes()

        # Verify CRT signature
        assert data[:16] == b"C64 CARTRIDGE   ", f"Invalid CRT signature in {filename}"

        # Verify hardware type
        parsed_type = int.from_bytes(data[0x16:0x18], "big")
        assert parsed_type == hw_type, \
            f"CRT {filename} has wrong hardware type: expected {hw_type}, got {parsed_type}"
