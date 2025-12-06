"""Tests for C64 memory banking logic.

These tests verify the CPU port ($01) bits correctly control memory visibility:
- LORAM (bit 0): Controls BASIC ROM visibility at $A000-$BFFF
- HIRAM (bit 1): Controls KERNAL ROM visibility at $E000-$FFFF
- CHAREN (bit 2): Controls I/O vs Character ROM at $D000-$DFFF

The banking logic is critical for diagnostic cartridges that need to test RAM
underneath ROM regions by setting LORAM=0 and HIRAM=0.
"""

import pytest
from systems.c64 import C64
from systems.c64.cartridges import StaticROMCartridge

from .conftest import C64_ROMS_DIR, requires_c64_roms


@requires_c64_roms
class TestROMLRegionBanking:
    """Test $8000-$9FFF region banking with cartridges."""

    @pytest.fixture
    def c64(self):
        """Create a C64 instance for testing."""
        return C64(rom_dir=C64_ROMS_DIR, display_mode='headless', video_chip='6569')

    def test_no_cartridge_always_returns_ram(self, c64):
        """Without a cartridge, $8000-$9FFF always returns RAM."""
        # Write test pattern to RAM
        c64.memory._write_ram_direct(0x8000, 0xAA)
        c64.memory._write_ram_direct(0x9FFF, 0xBB)

        # Should return RAM regardless of port settings
        for port in [0x37, 0x36, 0x35, 0x34, 0x33, 0x32, 0x31, 0x30]:
            c64.memory.port = port
            assert c64.memory.read(0x8000) == 0xAA, f"Failed with port ${port:02X}"
            assert c64.memory.read(0x9FFF) == 0xBB, f"Failed with port ${port:02X}"

    def test_8k_cartridge_loram_hiram_both_set_returns_roml(self, c64):
        """8K cartridge: ROML visible when LORAM=1 AND HIRAM=1."""
        # Create 8K cartridge with distinctive data
        roml_data = bytes([0x11] * 0x2000)  # $8000-$9FFF
        cartridge = StaticROMCartridge(
            roml_data=roml_data,
            name="Test8K",
        )
        c64.memory.cartridge = cartridge

        # Write different pattern to underlying RAM
        c64.memory._write_ram_direct(0x8000, 0xAA)
        c64.memory._write_ram_direct(0x9FFF, 0xBB)

        # LORAM=1, HIRAM=1: Should return ROML
        c64.memory.port = 0x37  # LORAM=1, HIRAM=1, CHAREN=1
        assert c64.memory.read(0x8000) == 0x11, "Should return ROML data"

        c64.memory.port = 0x34  # LORAM=0, HIRAM=0, CHAREN=1
        c64.memory.port = 0x37  # Back to LORAM=1, HIRAM=1
        assert c64.memory.read(0x8000) == 0x11, "Should return ROML data"

    def test_8k_cartridge_loram_clear_returns_ram(self, c64):
        """8K cartridge: Setting LORAM=0 exposes RAM under ROML."""
        # Create 8K cartridge
        roml_data = bytes([0x11] * 0x2000)
        cartridge = StaticROMCartridge(
            roml_data=roml_data,
            name="Test8K",
        )
        c64.memory.cartridge = cartridge

        # Write test pattern to RAM
        c64.memory._write_ram_direct(0x8000, 0xAA)
        c64.memory._write_ram_direct(0x9FFF, 0xBB)

        # LORAM=0, HIRAM=1: Should return RAM
        c64.memory.port = 0x36  # LORAM=0, HIRAM=1, CHAREN=1
        assert c64.memory.read(0x8000) == 0xAA, "LORAM=0 should expose RAM"
        assert c64.memory.read(0x9FFF) == 0xBB, "LORAM=0 should expose RAM"

    def test_8k_cartridge_hiram_clear_returns_ram(self, c64):
        """8K cartridge: Setting HIRAM=0 exposes RAM under ROML."""
        # Create 8K cartridge
        roml_data = bytes([0x11] * 0x2000)
        cartridge = StaticROMCartridge(
            roml_data=roml_data,
            name="Test8K",
        )
        c64.memory.cartridge = cartridge

        # Write test pattern to RAM
        c64.memory._write_ram_direct(0x8000, 0xCC)

        # LORAM=1, HIRAM=0: Should return RAM
        c64.memory.port = 0x35  # LORAM=1, HIRAM=0, CHAREN=1
        assert c64.memory.read(0x8000) == 0xCC, "HIRAM=0 should expose RAM"

    def test_8k_cartridge_both_loram_hiram_clear_returns_ram(self, c64):
        """8K cartridge: Setting both LORAM=0 AND HIRAM=0 exposes RAM."""
        # Create 8K cartridge
        roml_data = bytes([0x11] * 0x2000)
        cartridge = StaticROMCartridge(
            roml_data=roml_data,
            name="Test8K",
        )
        c64.memory.cartridge = cartridge

        # Write test pattern to RAM
        c64.memory._write_ram_direct(0x8000, 0xDD)
        c64.memory._write_ram_direct(0x9000, 0xEE)

        # LORAM=0, HIRAM=0: Should return RAM (diagnostic test mode)
        c64.memory.port = 0x30  # LORAM=0, HIRAM=0, CHAREN=0
        assert c64.memory.read(0x8000) == 0xDD, "Both LORAM=0,HIRAM=0 should expose RAM"
        assert c64.memory.read(0x9000) == 0xEE, "Both LORAM=0,HIRAM=0 should expose RAM"

    def test_ultimax_cartridge_always_returns_roml(self, c64):
        """Ultimax cartridge: ROML always visible regardless of CPU port."""
        # Create Ultimax cartridge (EXROM=1, GAME=0)
        # Ultimax requires ultimax_romh_data for $E000-$FFFF, optionally roml_data for $8000
        roml_data = bytes([0x22] * 0x2000)
        romh_data = bytes([0x33] * 0x2000)  # Required for Ultimax mode
        cartridge = StaticROMCartridge(
            roml_data=roml_data,
            ultimax_romh_data=romh_data,
            name="TestUltimax",
        )
        c64.memory.cartridge = cartridge

        # Write different pattern to RAM
        c64.memory._write_ram_direct(0x8000, 0xFF)

        # Ultimax mode: ROML always visible, ignoring LORAM/HIRAM
        for port in [0x37, 0x36, 0x35, 0x34, 0x33, 0x32, 0x31, 0x30]:
            c64.memory.port = port
            assert c64.memory.read(0x8000) == 0x22, f"Ultimax ROML should be visible with port ${port:02X}"


@requires_c64_roms
class TestROMHRegionBanking:
    """Test $A000-$BFFF region banking with 16K cartridges."""

    @pytest.fixture
    def c64(self):
        """Create a C64 instance for testing."""
        return C64(rom_dir=C64_ROMS_DIR, display_mode='headless', video_chip='6569')

    def test_16k_cartridge_romh_loram_hiram_both_set_returns_romh(self, c64):
        """16K cartridge: ROMH visible at $A000-$BFFF when LORAM=1 AND HIRAM=1."""
        # Create 16K cartridge with distinctive data
        roml_data = bytes([0x11] * 0x2000)  # $8000-$9FFF
        romh_data = bytes([0x22] * 0x2000)  # $A000-$BFFF
        cartridge = StaticROMCartridge(
            roml_data=roml_data,
            romh_data=romh_data,
            name="Test16K",
        )
        c64.memory.cartridge = cartridge

        # Write different pattern to underlying RAM
        c64.memory._write_ram_direct(0xA000, 0xAA)
        c64.memory._write_ram_direct(0xBFFF, 0xBB)

        # LORAM=1, HIRAM=1: Should return ROMH
        c64.memory.port = 0x37  # LORAM=1, HIRAM=1, CHAREN=1
        assert c64.memory.read(0xA000) == 0x22, "Should return ROMH data"
        assert c64.memory.read(0xBFFF) == 0x22, "Should return ROMH data"

    def test_16k_cartridge_romh_loram_clear_returns_ram(self, c64):
        """16K cartridge: Setting LORAM=0 exposes RAM under ROMH."""
        # Create 16K cartridge
        roml_data = bytes([0x11] * 0x2000)
        romh_data = bytes([0x22] * 0x2000)
        cartridge = StaticROMCartridge(
            roml_data=roml_data,
            romh_data=romh_data,
            name="Test16K",
        )
        c64.memory.cartridge = cartridge

        # Write test pattern to RAM
        c64.memory._write_ram_direct(0xA000, 0xAA)
        c64.memory._write_ram_direct(0xBFFF, 0xBB)

        # LORAM=0, HIRAM=1: Should return RAM, not ROMH
        c64.memory.port = 0x36  # LORAM=0, HIRAM=1, CHAREN=1
        assert c64.memory.read(0xA000) == 0xAA, "LORAM=0 should expose RAM under ROMH"
        assert c64.memory.read(0xBFFF) == 0xBB, "LORAM=0 should expose RAM under ROMH"

    def test_16k_cartridge_romh_hiram_clear_returns_ram(self, c64):
        """16K cartridge: Setting HIRAM=0 exposes RAM under ROMH."""
        # Create 16K cartridge
        roml_data = bytes([0x11] * 0x2000)
        romh_data = bytes([0x22] * 0x2000)
        cartridge = StaticROMCartridge(
            roml_data=roml_data,
            romh_data=romh_data,
            name="Test16K",
        )
        c64.memory.cartridge = cartridge

        # Write test pattern to RAM
        c64.memory._write_ram_direct(0xA000, 0xCC)

        # LORAM=1, HIRAM=0: Should return RAM, not ROMH
        c64.memory.port = 0x35  # LORAM=1, HIRAM=0, CHAREN=1
        assert c64.memory.read(0xA000) == 0xCC, "HIRAM=0 should expose RAM under ROMH"


@requires_c64_roms
class TestD000RegionBanking:
    """Test $D000-$DFFF region banking (I/O, Character ROM, or RAM)."""

    @pytest.fixture
    def c64(self):
        """Create a C64 instance for testing."""
        return C64(rom_dir=C64_ROMS_DIR, display_mode='headless', video_chip='6569')

    def test_charen_set_returns_io(self, c64):
        """CHAREN=1: I/O area visible at $D000-$DFFF."""
        # CHAREN=1 (bit 2 set)
        c64.memory.port = 0x37  # Default: LORAM=1, HIRAM=1, CHAREN=1

        # Write to VIC register and read back
        c64.vic.write(0xD020, 0x05)  # Border color
        value = c64.memory.read(0xD020)
        assert value == 0x05, "CHAREN=1 should show I/O at $D020"

    def test_charen_clear_with_loram_set_returns_charrom(self, c64):
        """CHAREN=0 with LORAM=1: Character ROM visible."""
        c64.memory.port = 0x33  # LORAM=1, HIRAM=1, CHAREN=0

        # $D000 in Character ROM is the @ symbol bitmap (0x3C, 0x66, ...)
        value = c64.memory.read(0xD000)
        assert value == 0x3C, "CHAREN=0 with LORAM=1 should show Character ROM"

    def test_charen_clear_with_hiram_set_returns_charrom(self, c64):
        """CHAREN=0 with HIRAM=1: Character ROM visible."""
        c64.memory.port = 0x32  # LORAM=0, HIRAM=1, CHAREN=0

        # Character ROM still visible when either LORAM or HIRAM is set
        value = c64.memory.read(0xD000)
        assert value == 0x3C, "CHAREN=0 with HIRAM=1 should show Character ROM"

    def test_charen_clear_loram_clear_hiram_clear_returns_ram(self, c64):
        """CHAREN=0 with LORAM=0 AND HIRAM=0: RAM visible (all ROMs banked out)."""
        # Write test pattern to RAM at $D000
        c64.memory._write_ram_direct(0xD000, 0xAA)
        c64.memory._write_ram_direct(0xD500, 0xBB)
        c64.memory._write_ram_direct(0xDFFF, 0xCC)

        # All ROMs banked out
        c64.memory.port = 0x30  # LORAM=0, HIRAM=0, CHAREN=0

        # Should return RAM, not Character ROM
        assert c64.memory.read(0xD000) == 0xAA, "LORAM=0,HIRAM=0,CHAREN=0 should show RAM"
        assert c64.memory.read(0xD500) == 0xBB, "LORAM=0,HIRAM=0,CHAREN=0 should show RAM"
        assert c64.memory.read(0xDFFF) == 0xCC, "LORAM=0,HIRAM=0,CHAREN=0 should show RAM"

    def test_diagnostic_ram_test_pattern(self, c64):
        """Simulate diagnostic RAM test: write pattern, verify readback with ROMs off."""
        # This is the pattern the 586220 diagnostic uses to test RAM at $D000
        test_patterns = [0x00, 0x55, 0xAA, 0xFF]

        for pattern in test_patterns:
            # Write pattern to RAM under Character ROM
            c64.memory._write_ram_direct(0xD000, pattern)

            # Bank out all ROMs (diagnostic mode)
            c64.memory.port = 0x30  # LORAM=0, HIRAM=0, CHAREN=0

            # Read back - should get RAM, not Character ROM
            value = c64.memory.read(0xD000)
            assert value == pattern, f"Pattern ${pattern:02X} should survive write/read at $D000"

    def test_writes_always_go_to_ram(self, c64):
        """Writes to $D000-$DFFF go to RAM even when I/O is visible."""
        # I/O visible
        c64.memory.port = 0x37  # CHAREN=1

        # Write to underlying RAM via direct write
        c64.memory._write_ram_direct(0xD100, 0x42)

        # Bank out I/O to verify RAM
        c64.memory.port = 0x30  # LORAM=0, HIRAM=0, CHAREN=0
        assert c64.memory.read(0xD100) == 0x42

    def test_port_value_transitions(self, c64):
        """Verify correct behavior across port value transitions."""
        # Write distinctive RAM values
        c64.memory._write_ram_direct(0xD000, 0xDE)
        c64.memory._write_ram_direct(0xD100, 0xAD)

        # Start with I/O visible
        c64.memory.port = 0x37
        # $D000 reads VIC register, not RAM
        vic_value = c64.memory.read(0xD000)

        # Switch to Character ROM
        c64.memory.port = 0x33
        char_value = c64.memory.read(0xD000)
        assert char_value == 0x3C, "Should read Character ROM"

        # Switch to RAM (all ROMs off)
        c64.memory.port = 0x30
        ram_value = c64.memory.read(0xD000)
        assert ram_value == 0xDE, "Should read RAM"

        # Switch back to Character ROM
        c64.memory.port = 0x33
        char_value2 = c64.memory.read(0xD000)
        assert char_value2 == 0x3C, "Should read Character ROM again"


@requires_c64_roms
class TestBankingIntegration:
    """Integration tests for memory banking with cartridges and diagnostics."""

    @pytest.fixture
    def c64(self):
        """Create a C64 instance for testing."""
        return C64(rom_dir=C64_ROMS_DIR, display_mode='headless', video_chip='6569')

    def test_full_ram_test_cycle(self, c64):
        """Simulate a full RAM test cycle like the 586220 diagnostic."""
        # Create 8K cartridge (like the diagnostic)
        roml_data = bytes([0x00] * 0x2000)
        cartridge = StaticROMCartridge(
            roml_data=roml_data,
            name="Diagnostic",
        )
        c64.memory.cartridge = cartridge

        # Test addresses that require banking: $8000, $D000
        test_addresses = [0x8000, 0x8FFF, 0x9000, 0x9FFF, 0xD000, 0xD7FF, 0xD800]
        test_patterns = [0x00, 0x55, 0xAA, 0xFF]

        for addr in test_addresses:
            for pattern in test_patterns:
                # Write pattern to RAM
                c64.memory._write_ram_direct(addr, pattern)

                # Bank out all ROMs
                c64.memory.port = 0x30

                # Read back and verify
                value = c64.memory.read(addr)
                assert value == pattern, f"RAM test failed at ${addr:04X} with pattern ${pattern:02X}"

    def test_kernal_region_with_hiram(self, c64):
        """Test $E000-$FFFF region respects HIRAM bit."""
        # Write RAM pattern
        c64.memory._write_ram_direct(0xE000, 0xAA)

        # HIRAM=1: Should see KERNAL ROM
        c64.memory.port = 0x37
        kernal_value = c64.memory.read(0xE000)
        assert kernal_value != 0xAA, "HIRAM=1 should show KERNAL, not RAM"

        # HIRAM=0: Should see RAM
        c64.memory.port = 0x35  # LORAM=1, HIRAM=0
        ram_value = c64.memory.read(0xE000)
        assert ram_value == 0xAA, "HIRAM=0 should expose RAM"

    def test_basic_region_with_loram(self, c64):
        """Test $A000-$BFFF region respects LORAM bit."""
        # Write RAM pattern
        c64.memory._write_ram_direct(0xA000, 0xBB)

        # LORAM=1, HIRAM=1: Should see BASIC ROM
        c64.memory.port = 0x37
        basic_value = c64.memory.read(0xA000)
        assert basic_value != 0xBB, "LORAM=1,HIRAM=1 should show BASIC, not RAM"

        # LORAM=0, HIRAM=1: Should see RAM
        c64.memory.port = 0x36  # LORAM=0, HIRAM=1
        ram_value = c64.memory.read(0xA000)
        assert ram_value == 0xBB, "LORAM=0 should expose RAM"

    def test_basic_region_with_hiram(self, c64):
        """Test $A000-$BFFF region also respects HIRAM bit for BASIC visibility."""
        # Write RAM pattern
        c64.memory._write_ram_direct(0xA000, 0xCC)

        # LORAM=1, HIRAM=1: Should see BASIC ROM
        c64.memory.port = 0x37
        basic_value = c64.memory.read(0xA000)
        assert basic_value != 0xCC, "LORAM=1,HIRAM=1 should show BASIC, not RAM"

        # LORAM=1, HIRAM=0: Should see RAM (BASIC needs both bits set)
        c64.memory.port = 0x35  # LORAM=1, HIRAM=0, CHAREN=1
        ram_value = c64.memory.read(0xA000)
        assert ram_value == 0xCC, "HIRAM=0 should expose RAM under BASIC"
