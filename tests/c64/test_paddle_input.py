"""
Tests for paddle emulation using mouse position.

Paddles use the same SID POT registers as the 1351 mouse, but with
absolute positioning instead of relative motion.
"""

import pytest
from systems.c64 import C64
from systems.c64.sid import SID
from systems.c64.cia1 import PADDLE_1_FIRE, PADDLE_2_FIRE, BUTTON_PRESSED
from mos6502 import errors
from .conftest import C64_ROMS_DIR, requires_c64_roms


def run_cycles(c64, cycles):
    """Run CPU for specified cycles, catching exhaustion exception."""
    try:
        c64.cpu.execute(cycles=cycles)
    except errors.CPUCycleExhaustionError:
        pass  # Expected when cycles run out


class TestSIDPaddleInput:
    """Test SID POT register updates from paddle input."""

    def test_sid_set_paddle_sets_both_values(self):
        """set_paddle sets both POTX and POTY."""
        sid = SID()

        sid.set_paddle(100, 200)

        assert sid.pot_x == 100
        assert sid.pot_y == 200

    def test_sid_set_paddle_clamps_to_byte(self):
        """set_paddle clamps values to 0-255."""
        sid = SID()

        sid.set_paddle(300, 400)

        assert sid.pot_x == 300 & 0xFF  # 44
        assert sid.pot_y == 400 & 0xFF  # 144

    def test_sid_set_paddle_handles_zero(self):
        """set_paddle handles zero values."""
        sid = SID()
        sid.pot_x = 0x80
        sid.pot_y = 0x80

        sid.set_paddle(0, 0)

        assert sid.pot_x == 0
        assert sid.pot_y == 0

    def test_sid_set_paddle_handles_max(self):
        """set_paddle handles maximum values."""
        sid = SID()

        sid.set_paddle(255, 255)

        assert sid.pot_x == 255
        assert sid.pot_y == 255


@requires_c64_roms
class TestC64PaddleInput:
    """Test C64 paddle input integration."""

    @pytest.fixture
    def c64(self):
        """Create a minimal C64 instance for testing."""
        c64 = C64(display_mode="headless", rom_dir=C64_ROMS_DIR)
        return c64

    def test_paddle_disabled_by_default(self, c64):
        """Paddle is disabled by default."""
        assert c64._paddle_enabled is False

    def test_enable_paddle(self, c64):
        """enable_paddle enables paddle input."""
        c64.enable_paddle(enabled=True, port=1)

        assert c64._paddle_enabled is True
        assert c64._paddle_port == 1

    def test_enable_paddle_port_2(self, c64):
        """Paddle can be configured for port 2."""
        c64.enable_paddle(enabled=True, port=2)

        assert c64._paddle_port == 2

    def test_disable_paddle(self, c64):
        """Paddle can be disabled after being enabled."""
        c64.enable_paddle(enabled=True)
        c64.enable_paddle(enabled=False)

        assert c64._paddle_enabled is False

    def test_update_paddle_position_when_enabled(self, c64):
        """Paddle position updates POT registers when enabled."""
        c64.enable_paddle(enabled=True)

        # Simulate mouse at center of 320x200 window
        c64.update_paddle_position(160, 100, 320, 200)

        # Should map to approximately 127-128 (center of 0-255)
        assert 126 <= c64.sid.pot_x <= 129
        assert 126 <= c64.sid.pot_y <= 129

    def test_update_paddle_position_when_disabled(self, c64):
        """Paddle position is ignored when disabled."""
        initial_x = c64.sid.pot_x
        initial_y = c64.sid.pot_y

        c64.update_paddle_position(160, 100, 320, 200)

        assert c64.sid.pot_x == initial_x
        assert c64.sid.pot_y == initial_y

    def test_paddle_position_left_edge(self, c64):
        """Mouse at left edge maps to POTX=0."""
        c64.enable_paddle(enabled=True)

        c64.update_paddle_position(0, 100, 320, 200)

        assert c64.sid.pot_x == 0

    def test_paddle_position_right_edge(self, c64):
        """Mouse at right edge maps to POTX=255."""
        c64.enable_paddle(enabled=True)

        # At x=320 in a 320-wide window
        c64.update_paddle_position(320, 100, 320, 200)

        assert c64.sid.pot_x == 255

    def test_paddle_position_top_edge(self, c64):
        """Mouse at top edge maps to POTY=0."""
        c64.enable_paddle(enabled=True)

        c64.update_paddle_position(160, 0, 320, 200)

        assert c64.sid.pot_y == 0

    def test_paddle_position_bottom_edge(self, c64):
        """Mouse at bottom edge maps to POTY=255."""
        c64.enable_paddle(enabled=True)

        c64.update_paddle_position(160, 200, 320, 200)

        assert c64.sid.pot_y == 255

    def test_paddle_position_clamps_negative(self, c64):
        """Negative mouse positions clamp to 0."""
        c64.enable_paddle(enabled=True)

        c64.update_paddle_position(-50, -50, 320, 200)

        assert c64.sid.pot_x == 0
        assert c64.sid.pot_y == 0

    def test_paddle_position_clamps_overflow(self, c64):
        """Mouse positions beyond window clamp to 255."""
        c64.enable_paddle(enabled=True)

        c64.update_paddle_position(500, 500, 320, 200)

        assert c64.sid.pot_x == 255
        assert c64.sid.pot_y == 255

    def test_paddle_button_1_press(self, c64):
        """Left mouse button sets paddle 1 fire bit (bit 2)."""
        c64.enable_paddle(enabled=True, port=1)
        assert c64.cia1.joystick_1 == 0xFF  # All released

        c64.set_paddle_button(1, True)

        # Paddle 1 fire is bit 2 (not bit 4 like joystick fire), active low (0 = pressed)
        # Reference: https://www.c64-wiki.com/wiki/Paddle
        assert (c64.cia1.joystick_1 & PADDLE_1_FIRE) == BUTTON_PRESSED

    def test_paddle_button_1_release(self, c64):
        """Left mouse button release clears paddle 1 fire bit."""
        c64.enable_paddle(enabled=True, port=1)
        c64.set_paddle_button(1, True)
        c64.set_paddle_button(1, False)

        # Paddle 1 fire bit 2 released (1 = released)
        assert (c64.cia1.joystick_1 & PADDLE_1_FIRE) == PADDLE_1_FIRE

    def test_paddle_button_2_press(self, c64):
        """Right mouse button sets paddle 2 fire bit (bit 3)."""
        c64.enable_paddle(enabled=True, port=1)

        c64.set_paddle_button(3, True)

        # Paddle 2 fire is bit 3 (not bit 0), active low (0 = pressed)
        # Reference: https://www.c64-wiki.com/wiki/Paddle
        assert (c64.cia1.joystick_1 & PADDLE_2_FIRE) == BUTTON_PRESSED

    def test_paddle_both_buttons_pressed(self, c64):
        """Both paddle fire buttons can be pressed simultaneously."""
        c64.enable_paddle(enabled=True, port=1)

        c64.set_paddle_button(1, True)  # Paddle 1 fire (bit 2)
        c64.set_paddle_button(3, True)  # Paddle 2 fire (bit 3)

        # Both bits 2 and 3 should be low (0 = pressed)
        assert (c64.cia1.joystick_1 & PADDLE_1_FIRE) == BUTTON_PRESSED
        assert (c64.cia1.joystick_1 & PADDLE_2_FIRE) == BUTTON_PRESSED
        both_paddles = PADDLE_1_FIRE | PADDLE_2_FIRE
        assert (c64.cia1.joystick_1 & both_paddles) == BUTTON_PRESSED

    def test_paddle_buttons_ignored_when_disabled(self, c64):
        """Paddle buttons are ignored when paddle is disabled."""
        initial = c64.cia1.joystick_1

        c64.set_paddle_button(1, True)

        assert c64.cia1.joystick_1 == initial

    def test_pot_registers_via_memory_read(self, c64):
        """POT registers are accessible via memory-mapped I/O."""
        c64.enable_paddle(enabled=True)
        c64.update_paddle_position(100, 150, 320, 200)

        # Read via memory (SID is at $D400-$D41F)
        potx = c64.memory.read(0xD419)
        poty = c64.memory.read(0xD41A)

        # Check values are scaled correctly
        expected_x = int((100 / 320) * 255)
        expected_y = int((150 / 200) * 255)
        assert potx == expected_x
        assert poty == expected_y


@requires_c64_roms
class TestPaddleCartridgeIntegration:
    """Integration tests using the mouse test cartridge (works for paddle too)."""

    # Zero-page mirror locations (same as mouse test)
    POTX_MIRROR = 0x03
    POTY_MIRROR = 0x04
    JOY1_MIRROR = 0x05

    @pytest.fixture
    def mouse_cart_path(self):
        """Path to the mouse test cartridge (works for paddle too)."""
        from pathlib import Path
        return Path(__file__).parent.parent / "fixtures" / "c64" / "peripheral_tests" / "test_mouse_input.crt"

    @pytest.fixture
    def c64_with_paddle_cart(self, mouse_cart_path):
        """Create C64 with test cartridge and paddle enabled."""
        if not mouse_cart_path.exists():
            pytest.skip(f"Test cartridge not found: {mouse_cart_path}")
        c64 = C64(display_mode="headless", rom_dir=C64_ROMS_DIR)
        c64.load_cartridge(mouse_cart_path)
        c64.cpu.reset()
        c64.enable_paddle(enabled=True, port=1)
        return c64

    def test_cartridge_reads_paddle_position(self, c64_with_paddle_cart):
        """Cartridge correctly reads paddle position into zero-page."""
        c64 = c64_with_paddle_cart

        # Set paddle position
        c64.update_paddle_position(128, 64, 256, 128)

        # Run enough cycles for the cartridge to read and store values
        run_cycles(c64, 10000)

        # Check zero-page mirrors - position should be 127 and 127 (scaled)
        assert c64.cpu.ram[self.POTX_MIRROR] == 127
        assert c64.cpu.ram[self.POTY_MIRROR] == 127

    def test_cartridge_updates_on_paddle_movement(self, c64_with_paddle_cart):
        """Cartridge reflects paddle movement in zero-page mirrors."""
        c64 = c64_with_paddle_cart

        # Set initial position
        c64.update_paddle_position(0, 0, 320, 200)
        run_cycles(c64, 10000)

        assert c64.cpu.ram[self.POTX_MIRROR] == 0
        assert c64.cpu.ram[self.POTY_MIRROR] == 0

        # Move to center
        c64.update_paddle_position(160, 100, 320, 200)
        run_cycles(c64, 10000)

        # Values should be approximately center (127-128)
        assert 126 <= c64.cpu.ram[self.POTX_MIRROR] <= 129
        assert 126 <= c64.cpu.ram[self.POTY_MIRROR] <= 129

    def test_cartridge_reads_paddle_buttons(self, c64_with_paddle_cart):
        """Cartridge correctly reads paddle button state."""
        c64 = c64_with_paddle_cart

        # Run to let cart initialize
        run_cycles(c64, 10000)

        # Initially no buttons pressed (all bits high)
        assert c64.cpu.ram[self.JOY1_MIRROR] == 0xFF

        # Press paddle 1 fire button
        c64.set_paddle_button(1, True)
        run_cycles(c64, 10000)

        # Paddle 1 fire is bit 2 (not bit 4 like joystick fire)
        # Reference: https://www.c64-wiki.com/wiki/Paddle
        assert (c64.cpu.ram[self.JOY1_MIRROR] & PADDLE_1_FIRE) == BUTTON_PRESSED
