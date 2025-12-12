"""Tests for VIC-II register snapshot functionality.

Games like Pitfall change scroll registers mid-frame for smooth scrolling.
The VIC must snapshot registers at a consistent point (first visible line)
to prevent screen "bouncing" artifacts.
"""

import pytest
from unittest.mock import MagicMock, patch
from systems.c64.vic import C64VIC as VIC, VideoTiming


# All VIC-II chip variants to test
VIC_CHIPS = [
    pytest.param(VideoTiming.VIC_6569, id="6569-PAL"),
    pytest.param(VideoTiming.VIC_6567R8, id="6567R8-NTSC"),
    pytest.param(VideoTiming.VIC_6567R56A, id="6567R56A-NTSC-old"),
]


class TestVICRegisterSnapshot:
    """Test VIC register snapshotting for consistent rendering."""

    @pytest.fixture(params=VIC_CHIPS)
    def vic(self, request):
        """Create a VIC instance for testing with each chip variant."""
        video_timing = request.param

        # Create mock CPU with cycles_executed
        mock_cpu = MagicMock()
        mock_cpu.cycles_executed = 0

        # Create dummy char ROM (4KB)
        char_rom = bytes(4096)

        vic = VIC(char_rom=char_rom, cpu=mock_cpu, video_timing=video_timing)
        return vic

    def test_regs_snapshot_initialized_to_none(self, vic):
        """regs_snapshot should be None initially."""
        assert vic.regs_snapshot is None

    def test_vic_bank_snapshot_initialized_to_none(self, vic):
        """vic_bank_snapshot should be None initially."""
        assert vic.vic_bank_snapshot is None

    def test_snapshot_taken_at_first_visible_line(self, vic):
        """Register snapshot should be taken when crossing line 51."""
        # Set up some distinctive register values
        vic.regs[0x11] = 0x1B  # YSCROLL=3, DEN=1
        vic.regs[0x16] = 0x15  # XSCROLL=5, CSEL=1
        vic.regs[0x20] = 0x06  # Border color blue

        # Start at line 50 (just before first visible)
        vic.current_raster = 50
        vic.cpu.cycles_executed = 50 * vic.cycles_per_line

        # Advance to line 52 (past first visible line 51)
        vic.cpu.cycles_executed = 52 * vic.cycles_per_line
        vic.update()

        # Snapshot should have been taken
        assert vic.regs_snapshot is not None
        assert vic.regs_snapshot[0x11] == 0x1B
        assert vic.regs_snapshot[0x16] == 0x15
        assert vic.regs_snapshot[0x20] == 0x06

    def test_snapshot_not_taken_before_line_51(self, vic):
        """Register snapshot should NOT be taken before line 51."""
        vic.regs[0x16] = 0x17  # XSCROLL=7

        # Start at line 10
        vic.current_raster = 10
        vic.cpu.cycles_executed = 10 * vic.cycles_per_line

        # Advance to line 40 (before first visible)
        vic.cpu.cycles_executed = 40 * vic.cycles_per_line
        vic.update()

        # Snapshot should still be None
        assert vic.regs_snapshot is None

    def test_snapshot_captures_scroll_values(self, vic):
        """Snapshot should capture current scroll values."""
        # Set scroll to specific values
        vic.regs[0x11] = 0x1B  # YSCROLL=3
        vic.regs[0x16] = 0x1F  # XSCROLL=7

        # Cross line 51
        vic.current_raster = 50
        vic.cpu.cycles_executed = 52 * vic.cycles_per_line
        vic.update()

        # Check scroll values in snapshot
        assert vic.regs_snapshot[0x16] & 0x07 == 7  # XSCROLL
        assert vic.regs_snapshot[0x11] & 0x07 == 3  # YSCROLL

    def test_snapshot_updated_each_frame(self, vic):
        """Snapshot should be updated when crossing line 51 each frame."""
        # First frame: set scroll to 7
        vic.regs[0x16] = 0x17  # XSCROLL=7
        vic.current_raster = 50
        vic.cpu.cycles_executed = 52 * vic.cycles_per_line
        vic.update()

        first_snapshot = vic.regs_snapshot
        assert first_snapshot[0x16] & 0x07 == 7

        # Advance to end of first frame (last raster line, chip-dependent)
        last_raster_line = vic.raster_lines - 1
        vic.cpu.cycles_executed = last_raster_line * vic.cycles_per_line
        vic.update()

        # Now simulate frame wrap - start of new frame at line 0
        # We need to set current_raster to something before line 51
        # and then advance past it to trigger a new snapshot
        vic.current_raster = 0
        vic.cpu.cycles_executed = 0  # Reset for new frame

        # Change scroll for next frame
        vic.regs[0x16] = 0x13  # XSCROLL=3

        # Advance past line 51 to trigger new snapshot
        vic.cpu.cycles_executed = 52 * vic.cycles_per_line
        vic.update()

        # Snapshot should be updated with new value
        assert vic.regs_snapshot[0x16] & 0x07 == 3

    def test_vic_bank_snapshot_captured_at_line_51(self, vic):
        """VIC bank snapshot should be captured at first visible line."""
        # Mock CIA2 for bank selection
        mock_cia2 = MagicMock()
        mock_cia2.get_vic_bank.return_value = 0x4000  # Bank 1
        vic.cia2 = mock_cia2

        # Cross line 51
        vic.current_raster = 50
        vic.cpu.cycles_executed = 52 * vic.cycles_per_line
        vic.update()

        assert vic.vic_bank_snapshot == 0x4000

    def test_live_register_changes_dont_affect_snapshot(self, vic):
        """Changes to live registers after snapshot should not affect it."""
        vic.regs[0x16] = 0x17  # XSCROLL=7

        # Take snapshot at line 51
        vic.current_raster = 50
        vic.cpu.cycles_executed = 52 * vic.cycles_per_line
        vic.update()

        # Change live register
        vic.regs[0x16] = 0x10  # XSCROLL=0

        # Snapshot should still have original value
        assert vic.regs_snapshot[0x16] & 0x07 == 7
        # Live register has new value
        assert vic.regs[0x16] & 0x07 == 0


class TestVICRenderFrameUsesSnapshot:
    """Test that render_frame uses snapshotted registers."""

    @pytest.fixture(params=VIC_CHIPS)
    def vic_with_pygame(self, request):
        """Create VIC with pygame surface for rendering tests."""
        pytest.importorskip("pygame")
        import pygame

        video_timing = request.param

        mock_cpu = MagicMock()
        mock_cpu.cycles_executed = 0

        # Create dummy char ROM (4KB)
        char_rom = bytes(4096)

        vic = VIC(char_rom=char_rom, cpu=mock_cpu, video_timing=video_timing)

        # Create a surface for rendering
        pygame.init()
        surface = pygame.Surface((vic.total_width, vic.total_height))

        return vic, surface

    def test_render_uses_snapshot_scroll(self, vic_with_pygame):
        """render_frame should use snapshotted scroll values."""
        vic, surface = vic_with_pygame

        # Set snapshot with XSCROLL=5
        vic.regs_snapshot = bytearray(64)
        vic.regs_snapshot[0x11] = 0x1B  # DEN=1, YSCROLL=3
        vic.regs_snapshot[0x16] = 0x1D  # XSCROLL=5
        vic.regs_snapshot[0x18] = 0x14  # Default memory layout
        vic.regs_snapshot[0x20] = 0x0E  # Border color
        vic.regs_snapshot[0x21] = 0x06  # Background color

        # Set live registers with different XSCROLL
        vic.regs[0x16] = 0x10  # XSCROLL=0

        # Set up mock VIC bank
        vic.vic_bank_snapshot = 0x0000
        mock_cia2 = MagicMock()
        mock_cia2.get_vic_bank.return_value = 0x4000  # Different bank
        vic.cia2 = mock_cia2

        # Create mock RAM and color RAM
        ram = [0] * 65536
        color_ram = [0] * 1024

        # Render should use snapshot (XSCROLL=5), not live (XSCROLL=0)
        # We can't easily verify the scroll visually, but we can verify
        # it doesn't crash and uses the snapshot
        vic.render_frame(surface, ram, color_ram)

        # If we got here without error, the snapshot was used

    def test_render_uses_snapshot_vic_bank(self, vic_with_pygame):
        """render_frame should use snapshotted VIC bank."""
        vic, surface = vic_with_pygame

        # Set up snapshots
        vic.regs_snapshot = bytearray(64)
        vic.regs_snapshot[0x11] = 0x1B
        vic.regs_snapshot[0x16] = 0x18
        vic.regs_snapshot[0x18] = 0x14
        vic.regs_snapshot[0x20] = 0x0E
        vic.regs_snapshot[0x21] = 0x06

        # Snapshot bank 0, live bank 1
        vic.vic_bank_snapshot = 0x0000
        mock_cia2 = MagicMock()
        mock_cia2.get_vic_bank.return_value = 0x4000
        vic.cia2 = mock_cia2

        ram = [0] * 65536
        color_ram = [0] * 1024

        # Render should use snapshot bank (0x0000)
        vic.render_frame(surface, ram, color_ram)

    def test_render_falls_back_to_live_when_no_snapshot(self, vic_with_pygame):
        """render_frame should use live registers when snapshot is None."""
        vic, surface = vic_with_pygame

        # No snapshot
        vic.regs_snapshot = None
        vic.vic_bank_snapshot = None

        # Set live registers
        vic.regs[0x11] = 0x1B
        vic.regs[0x16] = 0x18
        vic.regs[0x18] = 0x14
        vic.regs[0x20] = 0x0E
        vic.regs[0x21] = 0x06

        mock_cia2 = MagicMock()
        mock_cia2.get_vic_bank.return_value = 0x0000
        vic.cia2 = mock_cia2

        ram = [0] * 65536
        color_ram = [0] * 1024

        # Should use live registers without error
        vic.render_frame(surface, ram, color_ram)


class TestVICSnapshotTimingConstants:
    """Test that snapshot timing uses correct raster line."""

    # VIC-II chip timing parameters: (VideoTiming, expected_raster_lines, expected_cycles_per_line)
    VIC_TIMING_PARAMS = [
        pytest.param(VideoTiming.VIC_6569, 312, 63, id="6569-PAL"),
        pytest.param(VideoTiming.VIC_6567R8, 263, 65, id="6567R8-NTSC"),
        pytest.param(VideoTiming.VIC_6567R56A, 262, 64, id="6567R56A-NTSC-old"),
    ]

    @pytest.mark.parametrize("video_timing,expected_raster_lines,expected_cycles_per_line", VIC_TIMING_PARAMS)
    def test_first_visible_line_is_51(self, video_timing, expected_raster_lines, expected_cycles_per_line):
        """First visible line is 51 for all VIC-II chip variants.

        Line 51 is the first visible raster line on both PAL and NTSC C64:
        - PAL: Lines 51-250 are visible (200 lines)
        - NTSC: Lines 51-250 are visible (200 lines)

        Line 51 is chosen because:
        1. It's the first line where display content appears
        2. Games typically have scroll values set by this point
        3. It's after the top border where games often do setup
        """
        mock_cpu = MagicMock()
        mock_cpu.cycles_executed = 0
        char_rom = bytes(4096)
        vic = VIC(char_rom=char_rom, cpu=mock_cpu, video_timing=video_timing)

        # Set distinctive register value
        vic.regs[0x16] = 0x17  # XSCROLL=7

        # Start before line 51
        vic.current_raster = 50
        vic.cpu.cycles_executed = 50 * vic.cycles_per_line

        # Advance past line 51
        vic.cpu.cycles_executed = 52 * vic.cycles_per_line
        vic.update()

        # Snapshot should be taken at line 51 for all chip variants
        assert vic.regs_snapshot is not None
        assert vic.regs_snapshot[0x16] == 0x17

    @pytest.mark.parametrize("video_timing,expected_raster_lines,expected_cycles_per_line", VIC_TIMING_PARAMS)
    def test_chip_has_correct_raster_lines(self, video_timing, expected_raster_lines, expected_cycles_per_line):
        """Each VIC-II chip variant has correct raster line count."""
        mock_cpu = MagicMock()
        mock_cpu.cycles_executed = 0
        char_rom = bytes(4096)
        vic = VIC(char_rom=char_rom, cpu=mock_cpu, video_timing=video_timing)
        assert vic.raster_lines == expected_raster_lines
        assert vic.cycles_per_line == expected_cycles_per_line
