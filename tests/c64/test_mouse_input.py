"""
Tests for 1351 proportional mouse emulation.

Tests the mouse input handling via SID POT registers and CIA1 joystick bits.
"""

import pytest
from systems.c64 import C64
from systems.c64.sid import SID
from systems.c64.cia1 import MOUSE_LEFT_BUTTON, MOUSE_RIGHT_BUTTON, BUTTON_PRESSED, ALL_BUTTONS_RELEASED
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


class TestSIDMouseInput:
    """Test SID POT register updates from mouse input."""

    def test_sid_update_mouse_positive_delta(self):
        """Mouse motion with positive delta increases POT values."""
        sid = SID()
        initial_x = sid.pot_x
        initial_y = sid.pot_y

        sid.update_mouse(10, 5)

        assert sid.pot_x == (initial_x + 10) & 0xFF
        assert sid.pot_y == (initial_y + 5) & 0xFF

    def test_sid_update_mouse_negative_delta(self):
        """Mouse motion with negative delta decreases POT values."""
        sid = SID()
        sid.pot_x = 0x80
        sid.pot_y = 0x80

        sid.update_mouse(-10, -5)

        assert sid.pot_x == 0x80 - 10
        assert sid.pot_y == 0x80 - 5

    def test_sid_update_mouse_wraps_at_255(self):
        """POT values wrap from 255 to 0."""
        sid = SID()
        sid.pot_x = 0xFE
        sid.pot_y = 0xFF

        sid.update_mouse(5, 1)

        assert sid.pot_x == 0x03  # 0xFE + 5 = 0x103 -> 0x03
        assert sid.pot_y == 0x00  # 0xFF + 1 = 0x100 -> 0x00

    def test_sid_update_mouse_wraps_at_0(self):
        """POT values wrap from 0 to 255."""
        sid = SID()
        sid.pot_x = 0x02
        sid.pot_y = 0x00

        sid.update_mouse(-5, -1)

        assert sid.pot_x == 0xFD  # 0x02 - 5 = -3 -> 0xFD
        assert sid.pot_y == 0xFF  # 0x00 - 1 = -1 -> 0xFF

    def test_sid_set_paddle_absolute(self):
        """set_paddle sets absolute POT values."""
        sid = SID()

        sid.set_paddle(100, 200)

        assert sid.pot_x == 100
        assert sid.pot_y == 200

    def test_sid_set_paddle_clamps_to_byte(self):
        """set_paddle clamps values to 0-255."""
        sid = SID()

        sid.set_paddle(0x1FF, 0x100)

        assert sid.pot_x == 0xFF  # 0x1FF & 0xFF
        assert sid.pot_y == 0x00  # 0x100 & 0xFF

    def test_sid_pot_registers_readable(self):
        """POT values are readable via SID read method."""
        sid = SID()
        sid.pot_x = 0x42
        sid.pot_y = 0x84

        assert sid.read(0xD419) == 0x42  # POTX
        assert sid.read(0xD41A) == 0x84  # POTY


@requires_c64_roms
class TestC64MouseInput:
    """Test C64 mouse input integration."""

    @pytest.fixture
    def c64(self):
        """Create a minimal C64 instance for testing."""
        c64 = C64(display_mode="headless", rom_dir=C64_ROMS_DIR)
        return c64

    def test_mouse_disabled_by_default(self, c64):
        """Mouse is disabled by default."""
        assert c64._mouse_enabled is False

    def test_enable_mouse(self, c64):
        """enable_mouse enables mouse input."""
        c64.enable_mouse(enabled=True, port=1, sensitivity=1.0)

        assert c64._mouse_enabled is True
        assert c64._mouse_port == 1
        assert c64._mouse_sensitivity == 1.0
        assert c64.sid.mouse_enabled is True

    def test_enable_mouse_port_2(self, c64):
        """Mouse can be configured for port 2."""
        c64.enable_mouse(enabled=True, port=2)

        assert c64._mouse_port == 2

    def test_enable_mouse_custom_sensitivity(self, c64):
        """Mouse sensitivity can be customized."""
        c64.enable_mouse(enabled=True, sensitivity=2.5)

        assert c64._mouse_sensitivity == 2.5

    def test_disable_mouse(self, c64):
        """Mouse can be disabled after being enabled."""
        c64.enable_mouse(enabled=True)
        c64.enable_mouse(enabled=False)

        assert c64._mouse_enabled is False

    def test_update_mouse_motion_when_enabled(self, c64):
        """Mouse motion updates POT registers when enabled."""
        c64.enable_mouse(enabled=True)
        initial_x = c64.sid.pot_x
        initial_y = c64.sid.pot_y

        c64.update_mouse_motion(20, 15)

        assert c64.sid.pot_x == (initial_x + 20) & 0xFF
        assert c64.sid.pot_y == (initial_y + 15) & 0xFF

    def test_update_mouse_motion_when_disabled(self, c64):
        """Mouse motion is ignored when disabled."""
        initial_x = c64.sid.pot_x
        initial_y = c64.sid.pot_y

        c64.update_mouse_motion(20, 15)

        assert c64.sid.pot_x == initial_x
        assert c64.sid.pot_y == initial_y

    def test_update_mouse_motion_with_sensitivity(self, c64):
        """Mouse motion is scaled by sensitivity."""
        c64.enable_mouse(enabled=True, sensitivity=2.0)
        initial_x = c64.sid.pot_x

        c64.update_mouse_motion(10, 0)

        # 10 * 2.0 = 20
        assert c64.sid.pot_x == (initial_x + 20) & 0xFF

    def test_mouse_left_button_press_port1(self, c64):
        """Left mouse button sets fire bit on port 1."""
        c64.enable_mouse(enabled=True, port=1)
        assert c64.cia1.joystick_1 == 0xFF  # All released

        c64.set_mouse_button(1, True)  # Left button pressed

        # Left button active low (0 = pressed)
        assert (c64.cia1.joystick_1 & MOUSE_LEFT_BUTTON) == BUTTON_PRESSED

    def test_mouse_left_button_release_port1(self, c64):
        """Left mouse button release clears fire bit on port 1."""
        c64.enable_mouse(enabled=True, port=1)
        c64.set_mouse_button(1, True)
        c64.set_mouse_button(1, False)

        # Left button released (1 = released)
        assert (c64.cia1.joystick_1 & MOUSE_LEFT_BUTTON) == MOUSE_LEFT_BUTTON

    def test_mouse_right_button_press_port1(self, c64):
        """Right mouse button sets up bit on port 1."""
        c64.enable_mouse(enabled=True, port=1)

        c64.set_mouse_button(3, True)  # Right button pressed

        # Right button active low (0 = pressed)
        assert (c64.cia1.joystick_1 & MOUSE_RIGHT_BUTTON) == BUTTON_PRESSED

    def test_mouse_right_button_release_port1(self, c64):
        """Right mouse button release clears up bit on port 1."""
        c64.enable_mouse(enabled=True, port=1)
        c64.set_mouse_button(3, True)
        c64.set_mouse_button(3, False)

        # Right button released
        assert (c64.cia1.joystick_1 & MOUSE_RIGHT_BUTTON) == MOUSE_RIGHT_BUTTON

    def test_mouse_buttons_port2(self, c64):
        """Mouse buttons work on port 2."""
        c64.enable_mouse(enabled=True, port=2)
        assert c64.cia1.joystick_2 == 0xFF

        c64.set_mouse_button(1, True)  # Left button

        # Left button on joystick_2
        assert (c64.cia1.joystick_2 & MOUSE_LEFT_BUTTON) == BUTTON_PRESSED

    def test_mouse_buttons_ignored_when_disabled(self, c64):
        """Mouse buttons are ignored when mouse is disabled."""
        initial = c64.cia1.joystick_1

        c64.set_mouse_button(1, True)

        assert c64.cia1.joystick_1 == initial

    def test_both_buttons_can_be_pressed(self, c64):
        """Both mouse buttons can be pressed simultaneously."""
        c64.enable_mouse(enabled=True, port=1)

        c64.set_mouse_button(1, True)  # Left
        c64.set_mouse_button(3, True)  # Right

        # Both fire (bit 4) and up (bit 0) should be low
        assert (c64.cia1.joystick_1 & 0x11) == 0x00

    def test_pot_registers_via_memory_read(self, c64):
        """POT registers are accessible via memory-mapped I/O."""
        c64.enable_mouse(enabled=True)
        c64.sid.pot_x = 0x42
        c64.sid.pot_y = 0x84

        # Read via memory (SID is at $D400-$D41F)
        potx = c64.memory.read(0xD419)
        poty = c64.memory.read(0xD41A)

        assert potx == 0x42
        assert poty == 0x84


@requires_c64_roms
class TestMouseCartridgeIntegration:
    """Integration tests using the mouse test cartridge."""

    @pytest.fixture
    def mouse_cart_path(self):
        """Path to the mouse test cartridge."""
        from pathlib import Path
        return Path(__file__).parent.parent / "fixtures" / "c64" / "peripheral_tests" / "test_mouse_input.crt"

    @pytest.fixture
    def c64_with_mouse_cart(self, mouse_cart_path):
        """Create C64 with mouse test cartridge loaded."""
        if not mouse_cart_path.exists():
            pytest.skip(f"Mouse test cartridge not found: {mouse_cart_path}")
        c64 = C64(display_mode="headless", rom_dir=C64_ROMS_DIR)
        c64.load_cartridge(mouse_cart_path)
        c64.cpu.reset()
        c64.enable_mouse(enabled=True, port=1)
        return c64

    def test_cartridge_reads_pot_registers(self, c64_with_mouse_cart):
        """Cartridge correctly reads SID POT registers into zero-page."""
        c64 = c64_with_mouse_cart

        # Set initial POT values
        c64.sid.pot_x = 0x42
        c64.sid.pot_y = 0x84

        # Run enough cycles for the cartridge to read and store values
        run_cycles(c64, 10000)

        # Check zero-page mirrors
        assert c64.cpu.ram[PERIPHERAL_TEST_ZP_X] == 0x42
        assert c64.cpu.ram[PERIPHERAL_TEST_ZP_Y] == 0x84

    def test_cartridge_updates_on_mouse_motion(self, c64_with_mouse_cart):
        """Cartridge reflects mouse motion in zero-page mirrors."""
        c64 = c64_with_mouse_cart

        # Set initial values and let cart read them
        c64.sid.pot_x = 0x80
        c64.sid.pot_y = 0x80
        run_cycles(c64, 10000)

        initial_x = c64.cpu.ram[PERIPHERAL_TEST_ZP_X]
        initial_y = c64.cpu.ram[PERIPHERAL_TEST_ZP_Y]

        # Move mouse
        c64.update_mouse_motion(20, 10)

        # Run more cycles for cart to update
        run_cycles(c64, 10000)

        # Values should have changed
        assert c64.cpu.ram[PERIPHERAL_TEST_ZP_X] == (initial_x + 20) & 0xFF
        assert c64.cpu.ram[PERIPHERAL_TEST_ZP_Y] == (initial_y + 10) & 0xFF

    def test_cartridge_reads_joystick_buttons(self, c64_with_mouse_cart):
        """Cartridge correctly reads joystick/button state."""
        c64 = c64_with_mouse_cart

        # Run to let cart initialize
        run_cycles(c64, 10000)

        # Initially no buttons pressed (all bits high)
        assert c64.cpu.ram[PERIPHERAL_TEST_ZP_BUTTONS] == ALL_BUTTONS_RELEASED

        # Press left mouse button
        c64.set_mouse_button(1, True)
        run_cycles(c64, 10000)

        # Left button bit should be low
        assert (c64.cpu.ram[PERIPHERAL_TEST_ZP_BUTTONS] & MOUSE_LEFT_BUTTON) == BUTTON_PRESSED

        # Release button
        c64.set_mouse_button(1, False)
        run_cycles(c64, 10000)

        # Left button bit should be high again
        assert (c64.cpu.ram[PERIPHERAL_TEST_ZP_BUTTONS] & MOUSE_LEFT_BUTTON) == MOUSE_LEFT_BUTTON

    def test_cartridge_reads_right_button(self, c64_with_mouse_cart):
        """Cartridge correctly reads right mouse button."""
        c64 = c64_with_mouse_cart

        run_cycles(c64, 10000)

        # Press right mouse button
        c64.set_mouse_button(3, True)
        run_cycles(c64, 10000)

        # Right button bit should be low
        assert (c64.cpu.ram[PERIPHERAL_TEST_ZP_BUTTONS] & MOUSE_RIGHT_BUTTON) == BUTTON_PRESSED


@requires_c64_roms
class TestMouseMotionAccumulation:
    """Test that mouse motion accumulates correctly over multiple updates."""

    @pytest.fixture
    def c64(self):
        c64 = C64(display_mode="headless", rom_dir=C64_ROMS_DIR)
        c64.enable_mouse(enabled=True)
        return c64

    def test_multiple_small_movements(self, c64):
        """Multiple small movements accumulate correctly."""
        c64.sid.pot_x = 0x00
        c64.sid.pot_y = 0x00

        for _ in range(10):
            c64.update_mouse_motion(5, 3)

        assert c64.sid.pot_x == 50  # 10 * 5
        assert c64.sid.pot_y == 30  # 10 * 3

    def test_bidirectional_movement(self, c64):
        """Movement in opposite directions cancels out."""
        c64.sid.pot_x = 0x80
        c64.sid.pot_y = 0x80

        c64.update_mouse_motion(20, 20)
        c64.update_mouse_motion(-20, -20)

        assert c64.sid.pot_x == 0x80
        assert c64.sid.pot_y == 0x80

    def test_wrap_around_multiple_times(self, c64):
        """Large movements wrap around correctly."""
        c64.sid.pot_x = 0x00

        # Move 300 pixels right (wraps once)
        c64.update_mouse_motion(300, 0)

        assert c64.sid.pot_x == 300 & 0xFF  # 44

    def test_negative_sensitivity(self, c64):
        """Negative sensitivity inverts mouse direction."""
        c64._mouse_sensitivity = -1.0
        c64.sid.pot_x = 0x80

        c64.update_mouse_motion(10, 0)

        # Should move left instead of right
        assert c64.sid.pot_x == 0x80 - 10
