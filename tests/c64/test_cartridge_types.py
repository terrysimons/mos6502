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

import pytest

from c64 import C64
from c64.cartridges import (
    CARTRIDGE_TYPES,
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
)


# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
CARTRIDGE_TYPES_DIR = FIXTURES_DIR / "cartridge_types"
C64_ROMS_DIR = FIXTURES_DIR / "roms" / "c64"

# Check if C64 ROMs are available for integration tests
C64_ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
)

# Skip marker for tests requiring C64 ROMs
requires_c64_roms = pytest.mark.skipif(
    not C64_ROMS_AVAILABLE,
    reason=f"C64 ROMs not found in {C64_ROMS_DIR}"
)


class TestCartridgeModule:
    """Tests for the cartridge module classes and functions."""

    def test_cartridge_types_registry_contains_type_0(self):
        """Type 0 (Normal cartridge) should be in the registry."""
        assert 0 in CARTRIDGE_TYPES
        assert CARTRIDGE_TYPES[0] == StaticROMCartridge

    def test_static_rom_cartridge_hardware_type(self):
        """StaticROMCartridge should have hardware type 0."""
        assert StaticROMCartridge.HARDWARE_TYPE == 0

    def test_error_cartridge_hardware_type(self):
        """ErrorCartridge should have hardware type -1 (not a real type)."""
        assert ErrorCartridge.HARDWARE_TYPE == -1


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


class TestCreateCartridgeFactory:
    """Tests for the create_cartridge factory function."""

    def test_create_type_0_returns_static_rom_cartridge(self):
        """create_cartridge with type 0 should return StaticROMCartridge."""
        roml_data = bytes(ROML_SIZE)
        cart = create_cartridge(0, roml_data, name="Test")

        assert isinstance(cart, StaticROMCartridge)

    def test_create_unsupported_type_raises_value_error(self):
        """create_cartridge with unsupported type should raise ValueError."""
        roml_data = bytes(ROML_SIZE)

        with pytest.raises(ValueError, match="Unsupported cartridge hardware type"):
            create_cartridge(1, roml_data, name="Test")

        with pytest.raises(ValueError, match="Unsupported cartridge hardware type"):
            create_cartridge(32, roml_data, name="Test")


class TestC64CartridgeLoading:
    """Integration tests for loading cartridges through C64.

    These tests require C64 ROMs to be present in tests/fixtures/roms/c64/
    """

    @pytest.fixture
    def c64(self):
        """Create a C64 instance with ROMs loaded."""
        return C64(rom_dir=C64_ROMS_DIR, display_mode="headless")

    def _get_crt_path(self, hw_type: int) -> Path:
        """Get the path to a test CRT file for a given hardware type."""
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
        return CARTRIDGE_TYPES_DIR / f"type_{hw_type:02d}_{safe_name}.crt"

    def _test_load_cartridge_type(self, c64, hw_type: int):
        """Test that a cartridge type loads correctly (not as error cart)."""
        crt_path = self._get_crt_path(hw_type)
        if not crt_path.exists():
            pytest.skip(f"Test fixture not found: {crt_path}")

        c64.load_cartridge(crt_path)

        # The test FAILS if we get an error cartridge (mapper not implemented)
        assert c64.cartridge_type != "error", \
            f"Type {hw_type} ({C64.CRT_HARDWARE_TYPES.get(hw_type, 'unknown')}) not implemented"
        assert c64.memory.cartridge is not None
        assert not isinstance(c64.memory.cartridge, ErrorCartridge), \
            f"Type {hw_type} loaded as ErrorCartridge - mapper not implemented"

    @requires_c64_roms
    def test_load_type_00_normal_8kb_bin_cartridge(self, c64):
        """Type 0: Normal 8KB cartridge (raw .bin, EXROM=0, GAME=1)."""
        bin_path = FIXTURES_DIR / "test_cart_8k.bin"
        if not bin_path.exists():
            pytest.skip(f"Test fixture not found: {bin_path}")

        c64.load_cartridge(bin_path)

        assert c64.cartridge_type == "8k"
        assert c64.memory.cartridge is not None
        assert isinstance(c64.memory.cartridge, StaticROMCartridge)
        assert c64.memory.cartridge.exrom is False  # Active
        assert c64.memory.cartridge.game is True    # Inactive (8KB mode)

    @requires_c64_roms
    def test_load_type_00_normal_8kb_crt_cartridge(self, c64):
        """Type 0: Normal 8KB cartridge (.crt, EXROM=0, GAME=1)."""
        crt_path = FIXTURES_DIR / "test_cart_8k.crt"
        if not crt_path.exists():
            pytest.skip(f"Test fixture not found: {crt_path}")

        c64.load_cartridge(crt_path)

        assert c64.cartridge_type == "8k"
        assert c64.memory.cartridge is not None
        assert isinstance(c64.memory.cartridge, StaticROMCartridge)
        assert c64.memory.cartridge.exrom is False  # Active
        assert c64.memory.cartridge.game is True    # Inactive (8KB mode)
        assert c64.memory.cartridge.roml_data is not None

    @requires_c64_roms
    def test_load_type_00_normal_16kb_bin_cartridge(self, c64):
        """Type 0: Normal 16KB cartridge (raw .bin, EXROM=0, GAME=0)."""
        bin_path = FIXTURES_DIR / "test_cart_16k.bin"
        if not bin_path.exists():
            pytest.skip(f"Test fixture not found: {bin_path}")

        c64.load_cartridge(bin_path)

        assert c64.cartridge_type == "16k"
        assert c64.memory.cartridge is not None
        assert isinstance(c64.memory.cartridge, StaticROMCartridge)
        assert c64.memory.cartridge.exrom is False  # Active
        assert c64.memory.cartridge.game is False   # Active (16KB mode)

    @requires_c64_roms
    def test_load_type_00_normal_16kb_crt_1_chip_cartridge(self, c64):
        """Type 0: Normal 16KB cartridge (.crt with single CHIP, EXROM=0, GAME=0).

        CRT structure: One 16KB CHIP at $8000, split into ROML and ROMH.
        """
        crt_path = FIXTURES_DIR / "test_cart_16k_single_chip.crt"
        if not crt_path.exists():
            pytest.skip(f"Test fixture not found: {crt_path}")

        c64.load_cartridge(crt_path)

        assert c64.cartridge_type == "16k"
        assert c64.memory.cartridge is not None
        assert isinstance(c64.memory.cartridge, StaticROMCartridge)
        assert c64.memory.cartridge.exrom is False  # Active
        assert c64.memory.cartridge.game is False   # Active (16KB mode)
        assert c64.memory.cartridge.roml_data is not None
        assert c64.memory.cartridge.romh_data is not None

    @requires_c64_roms
    def test_load_type_00_normal_16kb_crt_2_chip_cartridge(self, c64):
        """Type 0: Normal 16KB cartridge (.crt with two CHIPs, EXROM=0, GAME=0).

        CRT structure: Two separate 8KB CHIPs at $8000 (ROML) and $A000 (ROMH).
        """
        crt_path = FIXTURES_DIR / "test_cart_16k.crt"
        if not crt_path.exists():
            pytest.skip(f"Test fixture not found: {crt_path}")

        c64.load_cartridge(crt_path)

        assert c64.cartridge_type == "16k"
        assert c64.memory.cartridge is not None
        assert isinstance(c64.memory.cartridge, StaticROMCartridge)
        assert c64.memory.cartridge.exrom is False  # Active
        assert c64.memory.cartridge.game is False   # Active (16KB mode)
        assert c64.memory.cartridge.roml_data is not None
        assert c64.memory.cartridge.romh_data is not None

    @requires_c64_roms
    def test_load_type_00_ultimax_bin_cartridge(self, c64):
        """Type 0: Ultimax cartridge (raw .bin, EXROM=1, GAME=0)."""
        bin_path = FIXTURES_DIR / "test_cart_ultimax.bin"
        if not bin_path.exists():
            pytest.skip(f"Test fixture not found: {bin_path}")

        c64.load_cartridge(bin_path, cart_type="ultimax")

        assert c64.cartridge_type == "ultimax"
        assert c64.memory.cartridge is not None
        assert isinstance(c64.memory.cartridge, StaticROMCartridge)
        assert c64.memory.cartridge.exrom is True   # Inactive (Ultimax)
        assert c64.memory.cartridge.game is False   # Active (Ultimax)
        assert c64.memory.cartridge.ultimax_romh_data is not None

    @requires_c64_roms
    def test_load_type_00_ultimax_crt_cartridge(self, c64):
        """Type 0: Ultimax cartridge (.crt, EXROM=1, GAME=0)."""
        crt_path = FIXTURES_DIR / "test_cart_ultimax.crt"
        if not crt_path.exists():
            pytest.skip(f"Test fixture not found: {crt_path}")

        c64.load_cartridge(crt_path)

        assert c64.cartridge_type == "ultimax"
        assert c64.memory.cartridge is not None
        assert isinstance(c64.memory.cartridge, StaticROMCartridge)
        assert c64.memory.cartridge.exrom is True   # Inactive (Ultimax)
        assert c64.memory.cartridge.game is False   # Active (Ultimax)
        assert c64.memory.cartridge.ultimax_romh_data is not None

    @requires_c64_roms
    def test_load_type_01_action_replay_cartridge(self, c64):
        """Type 1: Action Replay."""
        self._test_load_cartridge_type(c64, 1)

    @requires_c64_roms
    def test_load_type_02_kcs_power_cartridge(self, c64):
        """Type 2: KCS Power Cartridge."""
        self._test_load_cartridge_type(c64, 2)

    @requires_c64_roms
    def test_load_type_03_final_cartridge_iii_cartridge(self, c64):
        """Type 3: Final Cartridge III."""
        self._test_load_cartridge_type(c64, 3)

    @requires_c64_roms
    def test_load_type_04_simons_basic_cartridge(self, c64):
        """Type 4: Simons Basic."""
        self._test_load_cartridge_type(c64, 4)

    @requires_c64_roms
    def test_load_type_05_ocean_type_1_cartridge(self, c64):
        """Type 5: Ocean type 1."""
        self._test_load_cartridge_type(c64, 5)

    @requires_c64_roms
    def test_load_type_06_expert_cartridge(self, c64):
        """Type 6: Expert Cartridge."""
        self._test_load_cartridge_type(c64, 6)

    @requires_c64_roms
    def test_load_type_07_fun_play_power_play_cartridge(self, c64):
        """Type 7: Fun Play, Power Play."""
        self._test_load_cartridge_type(c64, 7)

    @requires_c64_roms
    def test_load_type_08_super_games_cartridge(self, c64):
        """Type 8: Super Games."""
        self._test_load_cartridge_type(c64, 8)

    @requires_c64_roms
    def test_load_type_09_atomic_power_cartridge(self, c64):
        """Type 9: Atomic Power."""
        self._test_load_cartridge_type(c64, 9)

    @requires_c64_roms
    def test_load_type_10_epyx_fastload_cartridge(self, c64):
        """Type 10: Epyx Fastload."""
        self._test_load_cartridge_type(c64, 10)

    @requires_c64_roms
    def test_load_type_11_westermann_learning_cartridge(self, c64):
        """Type 11: Westermann Learning."""
        self._test_load_cartridge_type(c64, 11)

    @requires_c64_roms
    def test_load_type_12_rex_utility_cartridge(self, c64):
        """Type 12: Rex Utility."""
        self._test_load_cartridge_type(c64, 12)

    @requires_c64_roms
    def test_load_type_13_final_cartridge_i_cartridge(self, c64):
        """Type 13: Final Cartridge I."""
        self._test_load_cartridge_type(c64, 13)

    @requires_c64_roms
    def test_load_type_14_magic_formel_cartridge(self, c64):
        """Type 14: Magic Formel."""
        self._test_load_cartridge_type(c64, 14)

    @requires_c64_roms
    def test_load_type_15_c64_game_system_cartridge(self, c64):
        """Type 15: C64 Game System, System 3."""
        self._test_load_cartridge_type(c64, 15)

    @requires_c64_roms
    def test_load_type_16_warpspeed_cartridge(self, c64):
        """Type 16: WarpSpeed."""
        self._test_load_cartridge_type(c64, 16)

    @requires_c64_roms
    def test_load_type_17_dinamic_cartridge(self, c64):
        """Type 17: Dinamic."""
        self._test_load_cartridge_type(c64, 17)

    @requires_c64_roms
    def test_load_type_18_zaxxon_sega_cartridge(self, c64):
        """Type 18: Zaxxon, Super Zaxxon (SEGA)."""
        self._test_load_cartridge_type(c64, 18)

    @requires_c64_roms
    def test_load_type_19_magic_desk_cartridge(self, c64):
        """Type 19: Magic Desk, Domark, HES Australia."""
        self._test_load_cartridge_type(c64, 19)

    @requires_c64_roms
    def test_load_type_20_super_snapshot_v5_cartridge(self, c64):
        """Type 20: Super Snapshot V5."""
        self._test_load_cartridge_type(c64, 20)

    @requires_c64_roms
    def test_load_type_21_comal_80_cartridge(self, c64):
        """Type 21: Comal-80."""
        self._test_load_cartridge_type(c64, 21)

    @requires_c64_roms
    def test_load_type_22_structured_basic_cartridge(self, c64):
        """Type 22: Structured Basic."""
        self._test_load_cartridge_type(c64, 22)

    @requires_c64_roms
    def test_load_type_23_ross_cartridge(self, c64):
        """Type 23: Ross."""
        self._test_load_cartridge_type(c64, 23)

    @requires_c64_roms
    def test_load_type_24_dela_ep64_cartridge(self, c64):
        """Type 24: Dela EP64."""
        self._test_load_cartridge_type(c64, 24)

    @requires_c64_roms
    def test_load_type_25_dela_ep7x8_cartridge(self, c64):
        """Type 25: Dela EP7x8."""
        self._test_load_cartridge_type(c64, 25)

    @requires_c64_roms
    def test_load_type_26_dela_ep256_cartridge(self, c64):
        """Type 26: Dela EP256."""
        self._test_load_cartridge_type(c64, 26)

    @requires_c64_roms
    def test_load_type_27_rex_ep256_cartridge(self, c64):
        """Type 27: Rex EP256."""
        self._test_load_cartridge_type(c64, 27)

    @requires_c64_roms
    def test_load_type_28_mikro_assembler_cartridge(self, c64):
        """Type 28: Mikro Assembler."""
        self._test_load_cartridge_type(c64, 28)

    @requires_c64_roms
    def test_load_type_29_final_cartridge_plus_cartridge(self, c64):
        """Type 29: Final Cartridge Plus."""
        self._test_load_cartridge_type(c64, 29)

    @requires_c64_roms
    def test_load_type_30_action_replay_4_cartridge(self, c64):
        """Type 30: Action Replay 4."""
        self._test_load_cartridge_type(c64, 30)

    @requires_c64_roms
    def test_load_type_31_stardos_cartridge(self, c64):
        """Type 31: StarDOS."""
        self._test_load_cartridge_type(c64, 31)

    @requires_c64_roms
    def test_load_type_32_easyflash_cartridge(self, c64):
        """Type 32: EasyFlash."""
        self._test_load_cartridge_type(c64, 32)

    @requires_c64_roms
    def test_load_type_33_easyflash_xbank_cartridge(self, c64):
        """Type 33: EasyFlash X-Bank."""
        self._test_load_cartridge_type(c64, 33)

    @requires_c64_roms
    def test_load_type_34_capture_cartridge(self, c64):
        """Type 34: Capture."""
        self._test_load_cartridge_type(c64, 34)

    @requires_c64_roms
    def test_load_type_35_action_replay_3_cartridge(self, c64):
        """Type 35: Action Replay 3."""
        self._test_load_cartridge_type(c64, 35)

    @requires_c64_roms
    def test_load_type_36_retro_replay_cartridge(self, c64):
        """Type 36: Retro Replay, Nordic Replay."""
        self._test_load_cartridge_type(c64, 36)

    @requires_c64_roms
    def test_load_type_37_mmc64_cartridge(self, c64):
        """Type 37: MMC64."""
        self._test_load_cartridge_type(c64, 37)

    @requires_c64_roms
    def test_load_type_38_mmc_replay_cartridge(self, c64):
        """Type 38: MMC Replay."""
        self._test_load_cartridge_type(c64, 38)

    @requires_c64_roms
    def test_load_type_39_ide64_cartridge(self, c64):
        """Type 39: IDE64."""
        self._test_load_cartridge_type(c64, 39)

    @requires_c64_roms
    def test_load_type_40_super_snapshot_v4_cartridge(self, c64):
        """Type 40: Super Snapshot V4."""
        self._test_load_cartridge_type(c64, 40)

    @requires_c64_roms
    def test_load_type_41_ieee488_cartridge(self, c64):
        """Type 41: IEEE488."""
        self._test_load_cartridge_type(c64, 41)

    @requires_c64_roms
    def test_load_type_42_game_killer_cartridge(self, c64):
        """Type 42: Game Killer."""
        self._test_load_cartridge_type(c64, 42)

    @requires_c64_roms
    def test_load_type_43_prophet_64_cartridge(self, c64):
        """Type 43: Prophet 64."""
        self._test_load_cartridge_type(c64, 43)

    @requires_c64_roms
    def test_load_type_44_exos_cartridge(self, c64):
        """Type 44: Exos."""
        self._test_load_cartridge_type(c64, 44)

    @requires_c64_roms
    def test_load_type_45_freeze_frame_cartridge(self, c64):
        """Type 45: Freeze Frame."""
        self._test_load_cartridge_type(c64, 45)

    @requires_c64_roms
    def test_load_type_46_freeze_machine_cartridge(self, c64):
        """Type 46: Freeze Machine."""
        self._test_load_cartridge_type(c64, 46)

    @requires_c64_roms
    def test_load_type_47_snapshot64_cartridge(self, c64):
        """Type 47: Snapshot64."""
        self._test_load_cartridge_type(c64, 47)

    @requires_c64_roms
    def test_load_type_48_super_explode_v5_cartridge(self, c64):
        """Type 48: Super Explode V5."""
        self._test_load_cartridge_type(c64, 48)

    @requires_c64_roms
    def test_load_type_49_magic_voice_cartridge(self, c64):
        """Type 49: Magic Voice."""
        self._test_load_cartridge_type(c64, 49)

    @requires_c64_roms
    def test_load_type_50_action_replay_2_cartridge(self, c64):
        """Type 50: Action Replay 2."""
        self._test_load_cartridge_type(c64, 50)

    @requires_c64_roms
    def test_load_type_51_mach_5_cartridge(self, c64):
        """Type 51: MACH 5."""
        self._test_load_cartridge_type(c64, 51)

    @requires_c64_roms
    def test_load_type_52_diashow_maker_cartridge(self, c64):
        """Type 52: Diashow Maker."""
        self._test_load_cartridge_type(c64, 52)

    @requires_c64_roms
    def test_load_type_53_pagefox_cartridge(self, c64):
        """Type 53: Pagefox."""
        self._test_load_cartridge_type(c64, 53)

    @requires_c64_roms
    def test_load_type_54_kingsoft_business_basic_cartridge(self, c64):
        """Type 54: Kingsoft Business Basic."""
        self._test_load_cartridge_type(c64, 54)

    @requires_c64_roms
    def test_load_type_55_silver_rock_128_cartridge(self, c64):
        """Type 55: Silver Rock 128."""
        self._test_load_cartridge_type(c64, 55)

    @requires_c64_roms
    def test_load_type_56_formel_64_cartridge(self, c64):
        """Type 56: Formel 64."""
        self._test_load_cartridge_type(c64, 56)

    @requires_c64_roms
    def test_load_type_57_rgcd_cartridge(self, c64):
        """Type 57: RGCD."""
        self._test_load_cartridge_type(c64, 57)

    @requires_c64_roms
    def test_load_type_58_rrnet_mk3_cartridge(self, c64):
        """Type 58: RR-Net MK3."""
        self._test_load_cartridge_type(c64, 58)

    @requires_c64_roms
    def test_load_type_59_easy_calc_result_cartridge(self, c64):
        """Type 59: Easy Calc Result."""
        self._test_load_cartridge_type(c64, 59)

    @requires_c64_roms
    def test_load_type_60_gmod2_cartridge(self, c64):
        """Type 60: GMod2."""
        self._test_load_cartridge_type(c64, 60)

    @requires_c64_roms
    def test_load_type_61_max_basic_cartridge(self, c64):
        """Type 61: MAX BASIC."""
        self._test_load_cartridge_type(c64, 61)

    @requires_c64_roms
    def test_load_type_62_gmod3_cartridge(self, c64):
        """Type 62: GMod3."""
        self._test_load_cartridge_type(c64, 62)

    @requires_c64_roms
    def test_load_type_63_zipp_code_48_cartridge(self, c64):
        """Type 63: ZIPP-CODE 48."""
        self._test_load_cartridge_type(c64, 63)

    @requires_c64_roms
    def test_load_type_64_blackbox_v8_cartridge(self, c64):
        """Type 64: Blackbox V8."""
        self._test_load_cartridge_type(c64, 64)

    @requires_c64_roms
    def test_load_type_65_blackbox_v3_cartridge(self, c64):
        """Type 65: Blackbox V3."""
        self._test_load_cartridge_type(c64, 65)

    @requires_c64_roms
    def test_load_type_66_blackbox_v4_cartridge(self, c64):
        """Type 66: Blackbox V4."""
        self._test_load_cartridge_type(c64, 66)

    @requires_c64_roms
    def test_load_type_67_rex_ram_floppy_cartridge(self, c64):
        """Type 67: REX RAM Floppy."""
        self._test_load_cartridge_type(c64, 67)

    @requires_c64_roms
    def test_load_type_68_bis_plus_cartridge(self, c64):
        """Type 68: BIS Plus."""
        self._test_load_cartridge_type(c64, 68)

    @requires_c64_roms
    def test_load_type_69_sd_box_cartridge(self, c64):
        """Type 69: SD Box."""
        self._test_load_cartridge_type(c64, 69)

    @requires_c64_roms
    def test_load_type_70_multimax_cartridge(self, c64):
        """Type 70: MultiMAX."""
        self._test_load_cartridge_type(c64, 70)

    @requires_c64_roms
    def test_load_type_71_blackbox_v9_cartridge(self, c64):
        """Type 71: Blackbox V9."""
        self._test_load_cartridge_type(c64, 71)

    @requires_c64_roms
    def test_load_type_72_lt_kernal_cartridge(self, c64):
        """Type 72: LT Kernal."""
        self._test_load_cartridge_type(c64, 72)

    @requires_c64_roms
    def test_load_type_73_cmd_ramlink_cartridge(self, c64):
        """Type 73: CMD RAMlink."""
        self._test_load_cartridge_type(c64, 73)

    @requires_c64_roms
    def test_load_type_74_drean_hero_bootleg_cartridge(self, c64):
        """Type 74: Drean (H.E.R.O. bootleg)."""
        self._test_load_cartridge_type(c64, 74)

    @requires_c64_roms
    def test_load_type_75_ieee_flash_64_cartridge(self, c64):
        """Type 75: IEEE Flash 64."""
        self._test_load_cartridge_type(c64, 75)

    @requires_c64_roms
    def test_load_type_76_turtle_graphics_ii_cartridge(self, c64):
        """Type 76: Turtle Graphics II."""
        self._test_load_cartridge_type(c64, 76)

    @requires_c64_roms
    def test_load_type_77_freeze_frame_mk2_cartridge(self, c64):
        """Type 77: Freeze Frame MK2."""
        self._test_load_cartridge_type(c64, 77)

    @requires_c64_roms
    def test_load_type_78_partner_64_cartridge(self, c64):
        """Type 78: Partner 64."""
        self._test_load_cartridge_type(c64, 78)

    @requires_c64_roms
    def test_load_type_79_hyper_basic_mk2_cartridge(self, c64):
        """Type 79: Hyper-BASIC MK2."""
        self._test_load_cartridge_type(c64, 79)

    @requires_c64_roms
    def test_load_type_80_universal_cartridge_1_cartridge(self, c64):
        """Type 80: Universal Cartridge 1."""
        self._test_load_cartridge_type(c64, 80)

    @requires_c64_roms
    def test_load_type_81_universal_cartridge_15_cartridge(self, c64):
        """Type 81: Universal Cartridge 1.5."""
        self._test_load_cartridge_type(c64, 81)

    @requires_c64_roms
    def test_load_type_82_universal_cartridge_2_cartridge(self, c64):
        """Type 82: Universal Cartridge 2."""
        self._test_load_cartridge_type(c64, 82)

    @requires_c64_roms
    def test_load_type_83_bmp_data_turbo_2000_cartridge(self, c64):
        """Type 83: BMP Data Turbo 2000."""
        self._test_load_cartridge_type(c64, 83)

    @requires_c64_roms
    def test_load_type_84_profi_dos_cartridge(self, c64):
        """Type 84: Profi-DOS."""
        self._test_load_cartridge_type(c64, 84)

    @requires_c64_roms
    def test_load_type_85_magic_desk_16_cartridge(self, c64):
        """Type 85: Magic Desk 16."""
        self._test_load_cartridge_type(c64, 85)


class TestCRTHeaderParsing:
    """Tests for CRT header parsing."""

    def test_hardware_type_correctly_parsed(self):
        """Hardware type should be correctly extracted from CRT header."""
        for hw_type in [0, 1, 5, 32, 85]:
            crt_data = self._create_minimal_crt(hardware_type=hw_type)
            parsed_type = int.from_bytes(crt_data[0x16:0x18], "big")
            assert parsed_type == hw_type

    def test_exrom_game_correctly_parsed(self):
        """EXROM and GAME lines should be correctly extracted from CRT header."""
        # Test various EXROM/GAME combinations
        for exrom, game in [(0, 0), (0, 1), (1, 0), (1, 1)]:
            crt_data = self._create_minimal_crt(exrom=exrom, game=game)
            assert crt_data[0x18] == exrom
            assert crt_data[0x19] == game

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

    @pytest.mark.parametrize("hw_type", range(1, 86))
    def test_error_cartridge_file_exists(self, hw_type):
        """Each unsupported type should have a pre-generated error cartridge."""
        type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, f"unknown_{hw_type}")
        safe_name = type_name.lower().replace(" ", "_").replace(",", "").replace("/", "_")
        filename = f"error_type_{hw_type:02d}_{safe_name}.bin"
        path = self.ERROR_CART_DIR / filename

        assert path.exists(), f"Error cartridge missing for type {hw_type}: {filename}"

    @pytest.mark.parametrize("hw_type", range(1, 86))
    def test_error_cartridge_file_size(self, hw_type):
        """Error cartridge files should be exactly 8KB."""
        type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, f"unknown_{hw_type}")
        safe_name = type_name.lower().replace(" ", "_").replace(",", "").replace("/", "_")
        filename = f"error_type_{hw_type:02d}_{safe_name}.bin"
        path = self.ERROR_CART_DIR / filename

        if not path.exists():
            pytest.skip(f"Error cartridge not found: {filename}")

        size = path.stat().st_size
        assert size == ROML_SIZE, f"Error cart {filename} should be {ROML_SIZE} bytes, got {size}"

    @pytest.mark.parametrize("hw_type", range(1, 86))
    def test_error_cartridge_has_cbm80_signature(self, hw_type):
        """Error cartridge ROMs should have valid CBM80 signature."""
        type_name = C64.CRT_HARDWARE_TYPES.get(hw_type, f"unknown_{hw_type}")
        safe_name = type_name.lower().replace(" ", "_").replace(",", "").replace("/", "_")
        filename = f"error_type_{hw_type:02d}_{safe_name}.bin"
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

    @pytest.mark.parametrize("hw_type", range(0, 86))
    def test_mapper_test_cartridge_exists(self, hw_type):
        """Each hardware type should have a test CRT file."""
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
        filename = f"type_{hw_type:02d}_{safe_name}.crt"
        path = CARTRIDGE_TYPES_DIR / filename

        assert path.exists(), f"Mapper test CRT missing for type {hw_type}: {filename}"

    @pytest.mark.parametrize("hw_type", range(0, 86))
    def test_mapper_test_cartridge_has_correct_hardware_type(self, hw_type):
        """Mapper test CRT files should have correct hardware type in header."""
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
        filename = f"type_{hw_type:02d}_{safe_name}.crt"
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
