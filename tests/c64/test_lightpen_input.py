"""
Tests for lightpen emulation using mouse position.

Lightpens use VIC-II registers for position (not SID POT like mouse/paddle):
- $D013 (LPX): X coordinate divided by 2
- $D014 (LPY): Y coordinate (sprite coordinates)
- Button triggers joystick fire on port 1 (bit 4)

Lightpen only works on control port 1 (hardware limitation).
Reference: https://www.c64-wiki.com/wiki/Light_pen
"""

import pytest
from systems.c64 import C64
from systems.c64.cia1 import LIGHTPEN_BUTTON, BUTTON_PRESSED, ALL_BUTTONS_RELEASED
from systems.c64.cartridges.rom_builder import (
    PERIPHERAL_TEST_ZP_X,
    PERIPHERAL_TEST_ZP_Y,
    PERIPHERAL_TEST_ZP_BUTTONS,
)
from mos6502 import errors
from .conftest import C64_ROMS_DIR, requires_c64_roms


def run_cycles(c64, cycles):
    """Run CPU for specified cycles, catching exhaustion exception."""
    try:
        c64.cpu.execute(cycles=cycles)
    except errors.CPUCycleExhaustionError:
        pass  # Expected when cycles run out


@requires_c64_roms
class TestC64LightpenInput:
    """Test C64 lightpen input integration."""

    @pytest.fixture
    def c64(self):
        """Create a minimal C64 instance for testing."""
        c64 = C64(display_mode="headless", rom_dir=C64_ROMS_DIR)
        return c64

    def test_lightpen_disabled_by_default(self, c64):
        """Lightpen is disabled by default."""
        assert c64._lightpen_enabled is False

    def test_enable_lightpen(self, c64):
        """enable_lightpen enables lightpen input."""
        c64.enable_lightpen(enabled=True)

        assert c64._lightpen_enabled is True

    def test_disable_lightpen(self, c64):
        """Lightpen can be disabled after being enabled."""
        c64.enable_lightpen(enabled=True)
        c64.enable_lightpen(enabled=False)

        assert c64._lightpen_enabled is False

    def test_update_lightpen_position_when_enabled(self, c64):
        """Lightpen position updates VIC registers when enabled."""
        c64.enable_lightpen(enabled=True)

        # Simulate mouse at center of 320x200 window
        c64.update_lightpen_position(160, 100, 320, 200)

        # Should map to approximately center of visible area in sprite coords
        # X: 24 + 160 = 184, LPX = 184 / 2 = 92
        # Y: 50 + 100 = 150
        assert c64.vic.regs[0x13] == 92  # LPX
        assert c64.vic.regs[0x14] == 150  # LPY

    def test_update_lightpen_position_when_disabled(self, c64):
        """Lightpen position is ignored when disabled."""
        initial_lpx = c64.vic.regs[0x13]
        initial_lpy = c64.vic.regs[0x14]

        c64.update_lightpen_position(160, 100, 320, 200)

        assert c64.vic.regs[0x13] == initial_lpx
        assert c64.vic.regs[0x14] == initial_lpy

    def test_lightpen_position_top_left(self, c64):
        """Mouse at top-left maps to top-left of visible area."""
        c64.enable_lightpen(enabled=True)

        c64.update_lightpen_position(0, 0, 320, 200)

        # X: 24 + 0 = 24, LPX = 24 / 2 = 12
        # Y: 50 + 0 = 50
        assert c64.vic.regs[0x13] == 12  # LPX
        assert c64.vic.regs[0x14] == 50  # LPY

    def test_lightpen_position_bottom_right(self, c64):
        """Mouse at bottom-right maps to bottom-right of visible area."""
        c64.enable_lightpen(enabled=True)

        c64.update_lightpen_position(320, 200, 320, 200)

        # X: 24 + 320 = 344, LPX = 344 / 2 = 172
        # Y: 50 + 200 = 250, clamped to 255 (ok), but 250 is fine
        assert c64.vic.regs[0x13] == 172  # LPX
        assert c64.vic.regs[0x14] == 250  # LPY

    def test_lightpen_position_clamps_negative(self, c64):
        """Negative mouse positions clamp to minimum visible area."""
        c64.enable_lightpen(enabled=True)

        c64.update_lightpen_position(-50, -50, 320, 200)

        # Negative values should clamp to the start of visible area
        # The formula will result in negative offset which should clamp
        # X: 24 + (-50/320)*320 = 24 + (-50) = -26 -> clamped to 0, LPX = 0
        # Y: 50 + (-50/200)*200 = 50 + (-50) = 0 -> clamped to 0
        assert c64.vic.regs[0x13] == 0  # LPX (0/2 = 0)
        assert c64.vic.regs[0x14] == 0  # LPY

    def test_lightpen_position_clamps_overflow(self, c64):
        """Mouse positions beyond window clamp to maximum."""
        c64.enable_lightpen(enabled=True)

        c64.update_lightpen_position(500, 500, 320, 200)

        # Overflow should clamp to max
        # X: 24 + (500/320)*320 = 24 + 500 = 524 -> clamped to 511, LPX = 255
        # Y: 50 + (500/200)*200 = 50 + 500 = 550 -> clamped to 255
        assert c64.vic.regs[0x13] == 255  # LPX (511/2 = 255)
        assert c64.vic.regs[0x14] == 255  # LPY

    def test_lightpen_button_press(self, c64):
        """Left mouse button sets lightpen fire bit (bit 4)."""
        c64.enable_lightpen(enabled=True)
        assert c64.cia1.joystick_1 == 0xFF  # All released

        c64.set_lightpen_button(1, True)

        # Lightpen fire is bit 4, active low (0 = pressed)
        assert (c64.cia1.joystick_1 & LIGHTPEN_BUTTON) == BUTTON_PRESSED

    def test_lightpen_button_release(self, c64):
        """Left mouse button release clears lightpen fire bit."""
        c64.enable_lightpen(enabled=True)
        c64.set_lightpen_button(1, True)
        c64.set_lightpen_button(1, False)

        # Lightpen fire bit 4 released (1 = released)
        assert (c64.cia1.joystick_1 & LIGHTPEN_BUTTON) == LIGHTPEN_BUTTON

    def test_lightpen_button_only_left_click(self, c64):
        """Only left mouse button (button 1) affects lightpen."""
        c64.enable_lightpen(enabled=True)

        # Right button (3) should not affect anything
        c64.set_lightpen_button(3, True)

        # Joystick should still be all released
        assert c64.cia1.joystick_1 == 0xFF

    def test_lightpen_button_ignored_when_disabled(self, c64):
        """Lightpen button is ignored when lightpen is disabled."""
        initial = c64.cia1.joystick_1

        c64.set_lightpen_button(1, True)

        assert c64.cia1.joystick_1 == initial

    def test_lightpen_registers_via_memory_read(self, c64):
        """Lightpen registers are accessible via memory-mapped I/O."""
        c64.enable_lightpen(enabled=True)
        c64.update_lightpen_position(160, 100, 320, 200)

        # Read via memory (VIC is at $D000-$D3FF)
        lpx = c64.memory.read(0xD013)
        lpy = c64.memory.read(0xD014)

        # Check values match what we set
        assert lpx == 92  # Center X / 2
        assert lpy == 150  # Center Y


@requires_c64_roms
class TestLightpenCoordinateMapping:
    """Test the coordinate mapping from mouse to VIC sprite coordinates."""

    @pytest.fixture
    def c64(self):
        c64 = C64(display_mode="headless", rom_dir=C64_ROMS_DIR)
        c64.enable_lightpen(enabled=True)
        return c64

    def test_full_horizontal_sweep(self, c64):
        """Test X coordinates across full horizontal range."""
        # Left edge
        c64.update_lightpen_position(0, 100, 320, 200)
        assert c64.vic.regs[0x13] == 12  # 24 / 2

        # Quarter
        c64.update_lightpen_position(80, 100, 320, 200)
        expected_x = 24 + 80  # 104, LPX = 52
        assert c64.vic.regs[0x13] == 52

        # Half
        c64.update_lightpen_position(160, 100, 320, 200)
        expected_x = 24 + 160  # 184, LPX = 92
        assert c64.vic.regs[0x13] == 92

        # Three quarters
        c64.update_lightpen_position(240, 100, 320, 200)
        expected_x = 24 + 240  # 264, LPX = 132
        assert c64.vic.regs[0x13] == 132

        # Right edge
        c64.update_lightpen_position(320, 100, 320, 200)
        expected_x = 24 + 320  # 344, LPX = 172
        assert c64.vic.regs[0x13] == 172

    def test_full_vertical_sweep(self, c64):
        """Test Y coordinates across full vertical range."""
        # Top edge
        c64.update_lightpen_position(160, 0, 320, 200)
        assert c64.vic.regs[0x14] == 50

        # Quarter
        c64.update_lightpen_position(160, 50, 320, 200)
        expected_y = 50 + 50  # 100
        assert c64.vic.regs[0x14] == 100

        # Half
        c64.update_lightpen_position(160, 100, 320, 200)
        expected_y = 50 + 100  # 150
        assert c64.vic.regs[0x14] == 150

        # Three quarters
        c64.update_lightpen_position(160, 150, 320, 200)
        expected_y = 50 + 150  # 200
        assert c64.vic.regs[0x14] == 200

        # Bottom edge
        c64.update_lightpen_position(160, 200, 320, 200)
        expected_y = 50 + 200  # 250
        assert c64.vic.regs[0x14] == 250

    def test_different_window_sizes(self, c64):
        """Position mapping works with different window sizes."""
        # 640x400 window (2x scale)
        c64.update_lightpen_position(320, 200, 640, 400)
        # Same as center: X=184/2=92, Y=150
        assert c64.vic.regs[0x13] == 92
        assert c64.vic.regs[0x14] == 150

        # 800x600 window (different aspect)
        c64.update_lightpen_position(400, 300, 800, 600)
        # Same as center
        assert c64.vic.regs[0x13] == 92
        assert c64.vic.regs[0x14] == 150

    def test_zero_window_size_safe(self, c64):
        """Zero window size doesn't cause division by zero."""
        # Should not raise exception
        c64.update_lightpen_position(100, 100, 0, 0)
        # Values should be at minimum visible area (max multiplication result)
        # With 0 width/height, the formula uses max(1, 0) = 1
        # X: 24 + (100/1)*320 = way over max, clamped to 511, LPX = 255
        # Y: 50 + (100/1)*200 = way over max, clamped to 255
        assert c64.vic.regs[0x13] == 255
        assert c64.vic.regs[0x14] == 255


@requires_c64_roms
class TestLightpenCartridgeIntegration:
    """Integration tests using the lightpen test cartridge."""

    # VIC lightpen registers
    VIC_LPX = 0xD013
    VIC_LPY = 0xD014

    @pytest.fixture
    def lightpen_cart_path(self):
        """Path to the lightpen test cartridge."""
        from pathlib import Path
        return Path(__file__).parent.parent / "fixtures" / "c64" / "peripheral_tests" / "test_lightpen_input.crt"

    @pytest.fixture
    def c64_with_lightpen_cart(self, lightpen_cart_path):
        """Create C64 with test cartridge and lightpen enabled."""
        if not lightpen_cart_path.exists():
            pytest.skip(f"Test cartridge not found: {lightpen_cart_path}")
        c64 = C64(display_mode="headless", rom_dir=C64_ROMS_DIR)
        c64.load_cartridge(lightpen_cart_path)
        c64.cpu.reset()
        c64.enable_lightpen(enabled=True)
        return c64

    def test_cartridge_reads_lightpen_position(self, c64_with_lightpen_cart):
        """Cartridge correctly reads lightpen position into zero-page."""
        c64 = c64_with_lightpen_cart

        # Set lightpen position (center of screen)
        c64.update_lightpen_position(160, 100, 320, 200)

        # Run enough cycles for the cartridge to read and store values
        run_cycles(c64, 10000)

        # Check zero-page mirrors - should match VIC registers
        assert c64.cpu.ram[PERIPHERAL_TEST_ZP_X] == 92  # 184 / 2
        assert c64.cpu.ram[PERIPHERAL_TEST_ZP_Y] == 150

    def test_cartridge_updates_on_lightpen_movement(self, c64_with_lightpen_cart):
        """Cartridge reflects lightpen movement in zero-page mirrors."""
        c64 = c64_with_lightpen_cart

        # Set initial position (top-left)
        c64.update_lightpen_position(0, 0, 320, 200)
        run_cycles(c64, 10000)

        assert c64.cpu.ram[PERIPHERAL_TEST_ZP_X] == 12  # 24 / 2
        assert c64.cpu.ram[PERIPHERAL_TEST_ZP_Y] == 50

        # Move to bottom-right
        c64.update_lightpen_position(320, 200, 320, 200)
        run_cycles(c64, 10000)

        assert c64.cpu.ram[PERIPHERAL_TEST_ZP_X] == 172  # 344 / 2
        assert c64.cpu.ram[PERIPHERAL_TEST_ZP_Y] == 250

    def test_cartridge_reads_lightpen_button(self, c64_with_lightpen_cart):
        """Cartridge correctly reads lightpen button state."""
        c64 = c64_with_lightpen_cart

        # Run to let cart initialize
        run_cycles(c64, 10000)

        # Initially no button pressed (all bits high)
        assert c64.cpu.ram[PERIPHERAL_TEST_ZP_BUTTONS] == ALL_BUTTONS_RELEASED

        # Press lightpen button
        c64.set_lightpen_button(1, True)
        run_cycles(c64, 10000)

        # Lightpen fire is bit 4 (same as joystick fire)
        assert (c64.cpu.ram[PERIPHERAL_TEST_ZP_BUTTONS] & LIGHTPEN_BUTTON) == BUTTON_PRESSED
