"""Tests for C64 memory snapshot functionality.

These tests verify the RAM snapshot methods used for thread-safe VIC rendering.
The snapshot methods bypass the memory handler to avoid infinite recursion
while providing consistent frame data for the display thread.
"""

from pathlib import Path

import pytest
from systems.c64 import C64

# Use the same ROM directory pattern as other C64 tests
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
C64_ROMS_DIR = FIXTURES_DIR / "roms" / "c64"

# Check if C64 ROMs are available
C64_ROMS_AVAILABLE = (
    C64_ROMS_DIR.exists()
    and (C64_ROMS_DIR / "basic.901226-01.bin").exists()
    and (C64_ROMS_DIR / "kernal.901227-03.bin").exists()
    and (C64_ROMS_DIR / "characters.901225-01.bin").exists()
)

requires_c64_roms = pytest.mark.skipif(
    not C64_ROMS_AVAILABLE,
    reason=f"C64 ROMs not found in {C64_ROMS_DIR}"
)


@requires_c64_roms
class TestMemorySnapshot:
    """Test C64Memory snapshot methods."""

    @pytest.fixture
    def c64(self):
        """Create a C64 instance for testing."""
        return C64(rom_dir=C64_ROMS_DIR, display_mode='headless', video_chip='6569')

    def test_snapshot_ram_returns_64kb(self, c64):
        """snapshot_ram() should return exactly 64KB (65536 bytes)."""
        snapshot = c64.memory.snapshot_ram()
        assert isinstance(snapshot, bytes)
        assert len(snapshot) == 65536

    def test_snapshot_ram_captures_data(self, c64):
        """snapshot_ram() should capture data written to RAM."""
        # Write test pattern to various locations
        c64.memory._write_ram_direct(0x0010, 0x42)  # Zero page
        c64.memory._write_ram_direct(0x0180, 0x43)  # Stack
        c64.memory._write_ram_direct(0x0400, 0x44)  # Screen RAM

        snapshot = c64.memory.snapshot_ram()

        assert snapshot[0x0010] == 0x42
        assert snapshot[0x0180] == 0x43
        assert snapshot[0x0400] == 0x44

    def test_snapshot_vic_bank_returns_16kb(self, c64):
        """snapshot_vic_bank() should return exactly 16KB (16384 bytes)."""
        for bank in [0x0000, 0x4000, 0x8000, 0xC000]:
            snapshot = c64.memory.snapshot_vic_bank(bank)
            assert isinstance(snapshot, bytes)
            assert len(snapshot) == 16384, f"Bank {bank:#06x} returned {len(snapshot)} bytes"

    def test_snapshot_vic_bank_captures_correct_region(self, c64):
        """snapshot_vic_bank() should capture data from the correct 16KB region."""
        # Write distinctive values to each bank
        c64.memory._write_ram_direct(0x0400, 0x10)  # Bank 0
        c64.memory._write_ram_direct(0x4400, 0x20)  # Bank 1
        c64.memory._write_ram_direct(0x8400, 0x30)  # Bank 2
        c64.memory._write_ram_direct(0xC400, 0x40)  # Bank 3

        # Bank 0: $0000-$3FFF
        snap0 = c64.memory.snapshot_vic_bank(0x0000)
        assert snap0[0x0400] == 0x10

        # Bank 1: $4000-$7FFF
        snap1 = c64.memory.snapshot_vic_bank(0x4000)
        assert snap1[0x0400] == 0x20  # $4400 relative to bank start

        # Bank 2: $8000-$BFFF
        snap2 = c64.memory.snapshot_vic_bank(0x8000)
        assert snap2[0x0400] == 0x30  # $8400 relative to bank start

        # Bank 3: $C000-$FFFF
        snap3 = c64.memory.snapshot_vic_bank(0xC000)
        assert snap3[0x0400] == 0x40  # $C400 relative to bank start

    def test_snapshot_screen_area_returns_correct_size(self, c64):
        """snapshot_screen_area() should return correct size based on mode."""
        # Text mode: 1KB
        text_snap = c64.memory.snapshot_screen_area(0x0400, bitmap_mode=False)
        assert len(text_snap) == 0x0400  # 1KB

        # Bitmap mode: 9KB
        bitmap_snap = c64.memory.snapshot_screen_area(0x0400, bitmap_mode=True)
        assert len(bitmap_snap) == 0x2400  # 9KB

    def test_snapshot_screen_area_captures_screen_ram(self, c64):
        """snapshot_screen_area() should capture screen RAM contents."""
        # Write test pattern to screen RAM at $0400
        for i in range(40):
            c64.memory._write_ram_direct(0x0400 + i, 0x41 + i)  # 'A', 'B', 'C', ...

        snapshot = c64.memory.snapshot_screen_area(0x0400)

        for i in range(40):
            assert snapshot[i] == 0x41 + i

    def test_snapshot_range_fast_path(self, c64):
        """_snapshot_range() should use fast path for addresses >= 512."""
        # Write test data to heap region
        c64.memory._write_ram_direct(0x0800, 0xAA)
        c64.memory._write_ram_direct(0x08FF, 0xBB)

        # Fast path: entirely in heap
        snapshot = c64.memory._snapshot_range(0x0800, 0x100)
        assert len(snapshot) == 0x100
        assert snapshot[0] == 0xAA
        assert snapshot[0xFF] == 0xBB

    def test_snapshot_immutable(self, c64):
        """Snapshots should be immutable bytes objects."""
        snapshot = c64.memory.snapshot_ram()
        assert isinstance(snapshot, bytes)

        # Modifying RAM after snapshot shouldn't affect the snapshot
        original_value = snapshot[0x0400]
        c64.memory._write_ram_direct(0x0400, original_value ^ 0xFF)

        # Take new snapshot - original should be unchanged
        new_snapshot = c64.memory.snapshot_ram()
        assert snapshot[0x0400] == original_value
        assert new_snapshot[0x0400] == original_value ^ 0xFF


@requires_c64_roms
class TestVICSnapshotIntegration:
    """Test VIC integration with memory snapshots."""

    @pytest.fixture
    def c64(self):
        """Create a C64 instance for testing."""
        return C64(rom_dir=C64_ROMS_DIR, display_mode='headless', video_chip='6569')

    def test_vic_takes_snapshot_at_vblank(self, c64):
        """VIC should take RAM snapshot when frame completes (VBlank)."""
        # Start at last raster line
        c64.vic.current_raster = 311  # PAL has 312 lines (0-311)

        # Advance past frame boundary
        c64.cpu.cycles_executed = 313 * c64.vic.cycles_per_line
        c64.vic.update()

        # VIC should have taken a snapshot
        assert c64.vic.ram_snapshot is not None
        assert c64.vic.color_snapshot is not None
        assert c64.vic.frame_complete.is_set()

    def test_vic_snapshot_is_16kb_bank(self, c64):
        """VIC snapshot should be 16KB (one VIC bank)."""
        c64.vic.current_raster = 311
        c64.cpu.cycles_executed = 313 * c64.vic.cycles_per_line
        c64.vic.update()

        assert len(c64.vic.ram_snapshot) == 16384

    def test_vic_snapshot_bank_matches_cia2(self, c64):
        """VIC snapshot bank should match CIA2 VIC bank selection."""
        # Default bank is 0 (CIA2 port A bits 0-1 = 11 -> bank 0)
        c64.vic.current_raster = 311
        c64.cpu.cycles_executed = 313 * c64.vic.cycles_per_line
        c64.vic.update()

        expected_bank = c64.vic.get_vic_bank()
        assert c64.vic.ram_snapshot_bank == expected_bank

    def test_vic_snapshot_color_ram(self, c64):
        """VIC should snapshot color RAM at VBlank."""
        # Write test pattern to color RAM
        c64.memory.ram_color[0] = 0x05  # Green
        c64.memory.ram_color[39] = 0x0E  # Light blue

        c64.vic.current_raster = 311
        c64.cpu.cycles_executed = 313 * c64.vic.cycles_per_line
        c64.vic.update()

        assert c64.vic.color_snapshot is not None
        assert c64.vic.color_snapshot[0] == 0x05
        assert c64.vic.color_snapshot[39] == 0x0E

    def test_vic_no_snapshot_without_c64_memory(self, c64):
        """VIC should not crash if c64_memory is not set."""
        # Remove memory reference
        c64.vic.c64_memory = None

        c64.vic.current_raster = 311
        c64.cpu.cycles_executed = 313 * c64.vic.cycles_per_line

        # Should not raise
        c64.vic.update()

        # frame_complete should still be set
        assert c64.vic.frame_complete.is_set()
        # But no snapshot taken
        assert c64.vic.ram_snapshot is None
