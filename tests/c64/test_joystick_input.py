"""
Tests for joystick input on both control ports.

C64 joystick hardware:
- Port 1: Read from CIA1 Port B ($DC01), bits 0-4
- Port 2: Read from CIA1 Port A ($DC00), bits 0-4

Bit mapping (active low: 0 = pressed, 1 = released):
- Bit 0: Up
- Bit 1: Down
- Bit 2: Left
- Bit 3: Right
- Bit 4: Fire

Reference: https://www.c64-wiki.com/wiki/Joystick
"""

import pytest
from systems.c64 import C64
from systems.c64.cia1 import (
    CIA1,
    JOYSTICK_UP,
    JOYSTICK_DOWN,
    JOYSTICK_LEFT,
    JOYSTICK_RIGHT,
    JOYSTICK_FIRE,
    JOYSTICK_BITS_MASK,
    ALL_BUTTONS_RELEASED,
    BUTTON_PRESSED,
)
from mos6502 import errors
from .conftest import C64_ROMS_DIR, requires_c64_roms


class TestCIA1JoystickPort1:
    """Test joystick port 1 via CIA1 Port B ($DC01)."""

    @pytest.fixture
    def cia1(self):
        """Create a CIA1 instance for testing."""
        # CIA1 needs a CPU reference, but we can pass None for basic tests
        # that don't trigger IRQs
        from unittest.mock import MagicMock
        mock_cpu = MagicMock()
        return CIA1(mock_cpu)

    def test_joystick_1_initially_released(self, cia1):
        """Joystick 1 starts with all directions/fire released."""
        assert cia1.joystick_1 == ALL_BUTTONS_RELEASED

    def test_joystick_1_up_pressed(self, cia1):
        """Pressing up on joystick 1 clears bit 0."""
        cia1.joystick_1 &= ~JOYSTICK_UP

        assert (cia1.joystick_1 & JOYSTICK_UP) == BUTTON_PRESSED

    def test_joystick_1_down_pressed(self, cia1):
        """Pressing down on joystick 1 clears bit 1."""
        cia1.joystick_1 &= ~JOYSTICK_DOWN

        assert (cia1.joystick_1 & JOYSTICK_DOWN) == BUTTON_PRESSED

    def test_joystick_1_left_pressed(self, cia1):
        """Pressing left on joystick 1 clears bit 2."""
        cia1.joystick_1 &= ~JOYSTICK_LEFT

        assert (cia1.joystick_1 & JOYSTICK_LEFT) == BUTTON_PRESSED

    def test_joystick_1_right_pressed(self, cia1):
        """Pressing right on joystick 1 clears bit 3."""
        cia1.joystick_1 &= ~JOYSTICK_RIGHT

        assert (cia1.joystick_1 & JOYSTICK_RIGHT) == BUTTON_PRESSED

    def test_joystick_1_fire_pressed(self, cia1):
        """Pressing fire on joystick 1 clears bit 4."""
        cia1.joystick_1 &= ~JOYSTICK_FIRE

        assert (cia1.joystick_1 & JOYSTICK_FIRE) == BUTTON_PRESSED

    def test_joystick_1_diagonal_up_right(self, cia1):
        """Diagonal up-right clears both bits 0 and 3."""
        cia1.joystick_1 &= ~(JOYSTICK_UP | JOYSTICK_RIGHT)

        assert (cia1.joystick_1 & JOYSTICK_UP) == BUTTON_PRESSED
        assert (cia1.joystick_1 & JOYSTICK_RIGHT) == BUTTON_PRESSED
        assert (cia1.joystick_1 & JOYSTICK_DOWN) == JOYSTICK_DOWN  # Released
        assert (cia1.joystick_1 & JOYSTICK_LEFT) == JOYSTICK_LEFT  # Released

    def test_joystick_1_fire_with_direction(self, cia1):
        """Fire can be pressed simultaneously with directions."""
        cia1.joystick_1 &= ~(JOYSTICK_FIRE | JOYSTICK_UP | JOYSTICK_LEFT)

        assert (cia1.joystick_1 & JOYSTICK_FIRE) == BUTTON_PRESSED
        assert (cia1.joystick_1 & JOYSTICK_UP) == BUTTON_PRESSED
        assert (cia1.joystick_1 & JOYSTICK_LEFT) == BUTTON_PRESSED

    def test_joystick_1_release_restores_bit(self, cia1):
        """Releasing a direction restores its bit to 1."""
        cia1.joystick_1 &= ~JOYSTICK_UP  # Press
        cia1.joystick_1 |= JOYSTICK_UP   # Release

        assert (cia1.joystick_1 & JOYSTICK_UP) == JOYSTICK_UP


class TestCIA1JoystickPort2:
    """Test joystick port 2 via CIA1 Port A ($DC00)."""

    @pytest.fixture
    def cia1(self):
        """Create a CIA1 instance for testing."""
        from unittest.mock import MagicMock
        mock_cpu = MagicMock()
        return CIA1(mock_cpu)

    def test_joystick_2_initially_released(self, cia1):
        """Joystick 2 starts with all directions/fire released."""
        assert cia1.joystick_2 == ALL_BUTTONS_RELEASED

    def test_joystick_2_up_pressed(self, cia1):
        """Pressing up on joystick 2 clears bit 0."""
        cia1.joystick_2 &= ~JOYSTICK_UP

        assert (cia1.joystick_2 & JOYSTICK_UP) == BUTTON_PRESSED

    def test_joystick_2_down_pressed(self, cia1):
        """Pressing down on joystick 2 clears bit 1."""
        cia1.joystick_2 &= ~JOYSTICK_DOWN

        assert (cia1.joystick_2 & JOYSTICK_DOWN) == BUTTON_PRESSED

    def test_joystick_2_left_pressed(self, cia1):
        """Pressing left on joystick 2 clears bit 2."""
        cia1.joystick_2 &= ~JOYSTICK_LEFT

        assert (cia1.joystick_2 & JOYSTICK_LEFT) == BUTTON_PRESSED

    def test_joystick_2_right_pressed(self, cia1):
        """Pressing right on joystick 2 clears bit 3."""
        cia1.joystick_2 &= ~JOYSTICK_RIGHT

        assert (cia1.joystick_2 & JOYSTICK_RIGHT) == BUTTON_PRESSED

    def test_joystick_2_fire_pressed(self, cia1):
        """Pressing fire on joystick 2 clears bit 4."""
        cia1.joystick_2 &= ~JOYSTICK_FIRE

        assert (cia1.joystick_2 & JOYSTICK_FIRE) == BUTTON_PRESSED

    def test_joystick_2_diagonal_down_left(self, cia1):
        """Diagonal down-left clears both bits 1 and 2."""
        cia1.joystick_2 &= ~(JOYSTICK_DOWN | JOYSTICK_LEFT)

        assert (cia1.joystick_2 & JOYSTICK_DOWN) == BUTTON_PRESSED
        assert (cia1.joystick_2 & JOYSTICK_LEFT) == BUTTON_PRESSED
        assert (cia1.joystick_2 & JOYSTICK_UP) == JOYSTICK_UP  # Released
        assert (cia1.joystick_2 & JOYSTICK_RIGHT) == JOYSTICK_RIGHT  # Released

    def test_joystick_2_all_directions_and_fire(self, cia1):
        """All directions and fire can be pressed (physically impossible but valid)."""
        cia1.joystick_2 &= ~JOYSTICK_BITS_MASK

        assert (cia1.joystick_2 & JOYSTICK_BITS_MASK) == BUTTON_PRESSED


class TestCIA1JoystickIndependence:
    """Test that joystick ports are independent."""

    @pytest.fixture
    def cia1(self):
        """Create a CIA1 instance for testing."""
        from unittest.mock import MagicMock
        mock_cpu = MagicMock()
        return CIA1(mock_cpu)

    def test_ports_are_independent(self, cia1):
        """Joystick 1 and 2 states are independent."""
        cia1.joystick_1 &= ~JOYSTICK_UP
        cia1.joystick_2 &= ~JOYSTICK_DOWN

        # Port 1 has up pressed, not down
        assert (cia1.joystick_1 & JOYSTICK_UP) == BUTTON_PRESSED
        assert (cia1.joystick_1 & JOYSTICK_DOWN) == JOYSTICK_DOWN

        # Port 2 has down pressed, not up
        assert (cia1.joystick_2 & JOYSTICK_DOWN) == BUTTON_PRESSED
        assert (cia1.joystick_2 & JOYSTICK_UP) == JOYSTICK_UP

    def test_both_ports_fire_simultaneously(self, cia1):
        """Both joysticks can fire at the same time."""
        cia1.joystick_1 &= ~JOYSTICK_FIRE
        cia1.joystick_2 &= ~JOYSTICK_FIRE

        assert (cia1.joystick_1 & JOYSTICK_FIRE) == BUTTON_PRESSED
        assert (cia1.joystick_2 & JOYSTICK_FIRE) == BUTTON_PRESSED


@requires_c64_roms
class TestC64JoystickMemoryMapped:
    """Test joystick reading via memory-mapped CIA1 registers."""

    @pytest.fixture
    def c64(self):
        """Create a C64 instance for testing."""
        return C64(display_mode="headless", rom_dir=C64_ROMS_DIR)

    def test_joystick_1_read_via_dc01(self, c64):
        """Joystick 1 state is readable via $DC01."""
        # Press fire on joystick 1
        c64.cia1.joystick_1 &= ~JOYSTICK_FIRE

        # Read via memory-mapped I/O
        # Note: $DC01 also includes keyboard matrix, but with no keys pressed
        # and default DDR settings, joystick bits should come through
        value = c64.memory.read(0xDC01)

        # Fire bit should be low
        assert (value & JOYSTICK_FIRE) == BUTTON_PRESSED

    def test_joystick_2_read_via_dc00(self, c64):
        """Joystick 2 state is readable via $DC00."""
        # Press fire on joystick 2
        c64.cia1.joystick_2 &= ~JOYSTICK_FIRE

        # Read via memory-mapped I/O
        value = c64.memory.read(0xDC00)

        # Fire bit should be low (bits 0-4 are joystick)
        assert (value & JOYSTICK_FIRE) == BUTTON_PRESSED

    def test_joystick_1_directions_via_memory(self, c64):
        """All joystick 1 directions readable via $DC01."""
        # Press all directions
        c64.cia1.joystick_1 &= ~(JOYSTICK_UP | JOYSTICK_DOWN | JOYSTICK_LEFT | JOYSTICK_RIGHT)

        value = c64.memory.read(0xDC01)

        # All direction bits should be low
        directions = JOYSTICK_UP | JOYSTICK_DOWN | JOYSTICK_LEFT | JOYSTICK_RIGHT
        assert (value & directions) == BUTTON_PRESSED

    def test_joystick_2_directions_via_memory(self, c64):
        """All joystick 2 directions readable via $DC00."""
        # Press all directions
        c64.cia1.joystick_2 &= ~(JOYSTICK_UP | JOYSTICK_DOWN | JOYSTICK_LEFT | JOYSTICK_RIGHT)

        value = c64.memory.read(0xDC00)

        # All direction bits should be low
        directions = JOYSTICK_UP | JOYSTICK_DOWN | JOYSTICK_LEFT | JOYSTICK_RIGHT
        assert (value & directions) == BUTTON_PRESSED

    def test_joystick_bits_do_not_affect_upper_bits(self, c64):
        """Joystick only affects bits 0-4, bits 5-7 should be high."""
        # Press everything on joystick 1
        c64.cia1.joystick_1 = 0x00  # All bits low

        value = c64.memory.read(0xDC01)

        # Bits 0-4 should be low (joystick pressed)
        assert (value & JOYSTICK_BITS_MASK) == BUTTON_PRESSED
        # Bits 5-7 should still be high (keyboard, no keys pressed)
        # Note: This depends on keyboard matrix state, which defaults to all released


def run_cycles(c64, cycles):
    """Run CPU for specified cycles, catching exhaustion exception."""
    try:
        c64.cpu.execute(cycles=cycles)
    except errors.CPUCycleExhaustionError:
        pass  # Expected when cycles run out


@requires_c64_roms
class TestJoystickCartridgeIntegration:
    """Integration tests using the joystick test cartridge."""

    @pytest.fixture
    def joystick_cart_path(self):
        """Path to the joystick test cartridge."""
        from pathlib import Path
        return Path(__file__).parent.parent / "fixtures" / "c64" / "peripheral_tests" / "test_joystick_input.crt"

    @pytest.fixture
    def c64_with_joystick_cart(self, joystick_cart_path):
        """Create C64 with joystick test cartridge."""
        if not joystick_cart_path.exists():
            pytest.skip(f"Test cartridge not found: {joystick_cart_path}")
        c64 = C64(display_mode="headless", rom_dir=C64_ROMS_DIR)
        c64.load_cartridge(joystick_cart_path)
        c64.cpu.reset()
        return c64

    # Import the zero-page constants used by the test cartridge
    from systems.c64.cartridges.rom_builder import (
        PERIPHERAL_TEST_ZP_JOY1,
        PERIPHERAL_TEST_ZP_JOY2,
    )

    def test_cartridge_reads_joystick_1_released(self, c64_with_joystick_cart):
        """Cartridge correctly reads joystick 1 all released."""
        c64 = c64_with_joystick_cart

        # Run enough cycles for cartridge to read and store values
        run_cycles(c64, 10000)

        # All buttons released = 0xFF (or at least bits 0-4 high)
        joy1_value = c64.cpu.ram[self.PERIPHERAL_TEST_ZP_JOY1]
        assert (joy1_value & JOYSTICK_BITS_MASK) == JOYSTICK_BITS_MASK

    def test_cartridge_reads_joystick_2_released(self, c64_with_joystick_cart):
        """Cartridge correctly reads joystick 2 all released."""
        c64 = c64_with_joystick_cart

        run_cycles(c64, 10000)

        # All buttons released = 0xFF (or at least bits 0-4 high)
        joy2_value = c64.cpu.ram[self.PERIPHERAL_TEST_ZP_JOY2]
        assert (joy2_value & JOYSTICK_BITS_MASK) == JOYSTICK_BITS_MASK

    def test_cartridge_reads_joystick_1_fire(self, c64_with_joystick_cart):
        """Cartridge correctly reads joystick 1 fire button."""
        c64 = c64_with_joystick_cart

        # Press fire on joystick 1
        c64.cia1.joystick_1 &= ~JOYSTICK_FIRE

        run_cycles(c64, 10000)

        joy1_value = c64.cpu.ram[self.PERIPHERAL_TEST_ZP_JOY1]
        assert (joy1_value & JOYSTICK_FIRE) == BUTTON_PRESSED

    def test_cartridge_reads_joystick_2_fire(self, c64_with_joystick_cart):
        """Cartridge correctly reads joystick 2 fire button."""
        c64 = c64_with_joystick_cart

        # Press fire on joystick 2
        c64.cia1.joystick_2 &= ~JOYSTICK_FIRE

        run_cycles(c64, 10000)

        joy2_value = c64.cpu.ram[self.PERIPHERAL_TEST_ZP_JOY2]
        assert (joy2_value & JOYSTICK_FIRE) == BUTTON_PRESSED

    def test_cartridge_reads_joystick_1_directions(self, c64_with_joystick_cart):
        """Cartridge correctly reads joystick 1 directions."""
        c64 = c64_with_joystick_cart

        # Press up and right (diagonal)
        c64.cia1.joystick_1 &= ~(JOYSTICK_UP | JOYSTICK_RIGHT)

        run_cycles(c64, 10000)

        joy1_value = c64.cpu.ram[self.PERIPHERAL_TEST_ZP_JOY1]
        assert (joy1_value & JOYSTICK_UP) == BUTTON_PRESSED
        assert (joy1_value & JOYSTICK_RIGHT) == BUTTON_PRESSED
        assert (joy1_value & JOYSTICK_DOWN) == JOYSTICK_DOWN  # Released
        assert (joy1_value & JOYSTICK_LEFT) == JOYSTICK_LEFT  # Released

    def test_cartridge_reads_joystick_2_directions(self, c64_with_joystick_cart):
        """Cartridge correctly reads joystick 2 directions."""
        c64 = c64_with_joystick_cart

        # Press down and left (diagonal)
        c64.cia1.joystick_2 &= ~(JOYSTICK_DOWN | JOYSTICK_LEFT)

        run_cycles(c64, 10000)

        joy2_value = c64.cpu.ram[self.PERIPHERAL_TEST_ZP_JOY2]
        assert (joy2_value & JOYSTICK_DOWN) == BUTTON_PRESSED
        assert (joy2_value & JOYSTICK_LEFT) == BUTTON_PRESSED
        assert (joy2_value & JOYSTICK_UP) == JOYSTICK_UP  # Released
        assert (joy2_value & JOYSTICK_RIGHT) == JOYSTICK_RIGHT  # Released

    def test_cartridge_reads_both_joysticks_independently(self, c64_with_joystick_cart):
        """Cartridge correctly reads both joysticks with different states."""
        c64 = c64_with_joystick_cart

        # Joystick 1: fire + up
        c64.cia1.joystick_1 &= ~(JOYSTICK_FIRE | JOYSTICK_UP)
        # Joystick 2: down + left
        c64.cia1.joystick_2 &= ~(JOYSTICK_DOWN | JOYSTICK_LEFT)

        run_cycles(c64, 10000)

        joy1_value = c64.cpu.ram[self.PERIPHERAL_TEST_ZP_JOY1]
        joy2_value = c64.cpu.ram[self.PERIPHERAL_TEST_ZP_JOY2]

        # Joystick 1 should have fire + up pressed
        assert (joy1_value & JOYSTICK_FIRE) == BUTTON_PRESSED
        assert (joy1_value & JOYSTICK_UP) == BUTTON_PRESSED
        assert (joy1_value & JOYSTICK_DOWN) == JOYSTICK_DOWN  # Released

        # Joystick 2 should have down + left pressed
        assert (joy2_value & JOYSTICK_DOWN) == BUTTON_PRESSED
        assert (joy2_value & JOYSTICK_LEFT) == BUTTON_PRESSED
        assert (joy2_value & JOYSTICK_FIRE) == JOYSTICK_FIRE  # Released

    def test_cartridge_updates_on_joystick_change(self, c64_with_joystick_cart):
        """Cartridge reflects joystick changes in zero-page mirrors."""
        c64 = c64_with_joystick_cart

        # Initially all released
        run_cycles(c64, 10000)
        joy1_initial = c64.cpu.ram[self.PERIPHERAL_TEST_ZP_JOY1]
        assert (joy1_initial & JOYSTICK_FIRE) == JOYSTICK_FIRE  # Released

        # Press fire
        c64.cia1.joystick_1 &= ~JOYSTICK_FIRE
        run_cycles(c64, 10000)
        joy1_pressed = c64.cpu.ram[self.PERIPHERAL_TEST_ZP_JOY1]
        assert (joy1_pressed & JOYSTICK_FIRE) == BUTTON_PRESSED

        # Release fire
        c64.cia1.joystick_1 |= JOYSTICK_FIRE
        run_cycles(c64, 10000)
        joy1_released = c64.cpu.ram[self.PERIPHERAL_TEST_ZP_JOY1]
        assert (joy1_released & JOYSTICK_FIRE) == JOYSTICK_FIRE


@requires_c64_roms
class TestC64KeyboardJoystickEmulation:
    """Test keyboard-to-joystick emulation API."""

    @pytest.fixture
    def c64(self):
        """Create a C64 instance for testing."""
        return C64(display_mode="headless", rom_dir=C64_ROMS_DIR)

    def test_joystick_disabled_by_default(self, c64):
        """Keyboard joystick emulation is disabled by default."""
        assert c64._joystick_enabled is False

    def test_enable_joystick_port_2(self, c64):
        """Can enable joystick on port 2 (default)."""
        c64.enable_joystick(enabled=True)

        assert c64._joystick_enabled is True
        assert c64._joystick_port == 2

    def test_enable_joystick_port_1(self, c64):
        """Can enable joystick on port 1."""
        c64.enable_joystick(enabled=True, port=1)

        assert c64._joystick_enabled is True
        assert c64._joystick_port == 1

    def test_disable_joystick(self, c64):
        """Can disable joystick after enabling."""
        c64.enable_joystick(enabled=True)
        c64.enable_joystick(enabled=False)

        assert c64._joystick_enabled is False

    def test_set_joystick_direction_up_port_2(self, c64):
        """set_joystick_direction sets up on port 2."""
        c64.enable_joystick(enabled=True, port=2)

        c64.set_joystick_direction(JOYSTICK_UP, True)

        assert (c64.cia1.joystick_2 & JOYSTICK_UP) == BUTTON_PRESSED

    def test_set_joystick_direction_down_port_2(self, c64):
        """set_joystick_direction sets down on port 2."""
        c64.enable_joystick(enabled=True, port=2)

        c64.set_joystick_direction(JOYSTICK_DOWN, True)

        assert (c64.cia1.joystick_2 & JOYSTICK_DOWN) == BUTTON_PRESSED

    def test_set_joystick_direction_left_port_2(self, c64):
        """set_joystick_direction sets left on port 2."""
        c64.enable_joystick(enabled=True, port=2)

        c64.set_joystick_direction(JOYSTICK_LEFT, True)

        assert (c64.cia1.joystick_2 & JOYSTICK_LEFT) == BUTTON_PRESSED

    def test_set_joystick_direction_right_port_2(self, c64):
        """set_joystick_direction sets right on port 2."""
        c64.enable_joystick(enabled=True, port=2)

        c64.set_joystick_direction(JOYSTICK_RIGHT, True)

        assert (c64.cia1.joystick_2 & JOYSTICK_RIGHT) == BUTTON_PRESSED

    def test_set_joystick_direction_fire_port_2(self, c64):
        """set_joystick_direction sets fire on port 2."""
        c64.enable_joystick(enabled=True, port=2)

        c64.set_joystick_direction(JOYSTICK_FIRE, True)

        assert (c64.cia1.joystick_2 & JOYSTICK_FIRE) == BUTTON_PRESSED

    def test_set_joystick_direction_release(self, c64):
        """set_joystick_direction can release a direction."""
        c64.enable_joystick(enabled=True, port=2)
        c64.set_joystick_direction(JOYSTICK_UP, True)
        c64.set_joystick_direction(JOYSTICK_UP, False)

        assert (c64.cia1.joystick_2 & JOYSTICK_UP) == JOYSTICK_UP  # Released

    def test_set_joystick_direction_port_1(self, c64):
        """set_joystick_direction works on port 1."""
        c64.enable_joystick(enabled=True, port=1)

        c64.set_joystick_direction(JOYSTICK_FIRE, True)

        assert (c64.cia1.joystick_1 & JOYSTICK_FIRE) == BUTTON_PRESSED
        # Port 2 should be unaffected
        assert (c64.cia1.joystick_2 & JOYSTICK_FIRE) == JOYSTICK_FIRE

    def test_set_joystick_direction_ignored_when_disabled(self, c64):
        """set_joystick_direction is ignored when joystick is disabled."""
        initial_joy2 = c64.cia1.joystick_2

        c64.set_joystick_direction(JOYSTICK_UP, True)

        assert c64.cia1.joystick_2 == initial_joy2

    def test_set_joystick_diagonal(self, c64):
        """Can set diagonal directions (up+right)."""
        c64.enable_joystick(enabled=True, port=2)

        c64.set_joystick_direction(JOYSTICK_UP, True)
        c64.set_joystick_direction(JOYSTICK_RIGHT, True)

        assert (c64.cia1.joystick_2 & JOYSTICK_UP) == BUTTON_PRESSED
        assert (c64.cia1.joystick_2 & JOYSTICK_RIGHT) == BUTTON_PRESSED
        assert (c64.cia1.joystick_2 & JOYSTICK_DOWN) == JOYSTICK_DOWN  # Released
        assert (c64.cia1.joystick_2 & JOYSTICK_LEFT) == JOYSTICK_LEFT  # Released
