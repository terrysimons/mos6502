"""C64 Input Devices Mixin.

Mixin for input devices (mouse, paddle, lightpen, joystick).
"""

from mos6502.compat import logging, Union
from c64.cia1 import (
    PADDLE_1_FIRE,
    PADDLE_2_FIRE,
    MOUSE_LEFT_BUTTON,
    MOUSE_RIGHT_BUTTON,
    LIGHTPEN_BUTTON,
    JOYSTICK_UP,
    JOYSTICK_DOWN,
    JOYSTICK_LEFT,
    JOYSTICK_RIGHT,
    JOYSTICK_FIRE,
)

log = logging.getLogger("c64")


class C64InputDevicesMixin:
    """Mixin for input devices (mouse, paddle, lightpen, joystick)."""

    def enable_mouse(self, enabled: bool = True, port: int = 1, sensitivity: float = 1.0) -> None:
        """Enable or disable mouse input.

        Args:
            enabled: Whether mouse input is enabled
            port: Which joystick port (1 or 2) the mouse is connected to
            sensitivity: Scale factor for mouse motion (1.0 = 1:1 mapping)
        """
        self._mouse_enabled = enabled
        self._mouse_port = port
        self._mouse_sensitivity = sensitivity
        self.sid.mouse_enabled = enabled
        log.info(f"Mouse input {'enabled' if enabled else 'disabled'} on port {port}, sensitivity={sensitivity}")

    def update_mouse_motion(self, delta_x: int, delta_y: int) -> None:
        """Update mouse position from motion delta.

        The 1351 mouse sends relative motion that wraps around 0-255.
        This method should be called with pygame MOUSEMOTION event rel values.

        Args:
            delta_x: Horizontal motion in pixels (positive = right)
            delta_y: Vertical motion in pixels (positive = down)
        """
        if not self._mouse_enabled:
            return

        # Apply sensitivity scaling
        scaled_x = int(delta_x * self._mouse_sensitivity)
        scaled_y = int(delta_y * self._mouse_sensitivity)

        # Update SID POT registers
        self.sid.update_mouse(scaled_x, scaled_y)

    def set_mouse_button(self, button: int, pressed: bool) -> None:
        """Set mouse button state.

        Args:
            button: Button number (1 = left, 3 = right for pygame)
            pressed: True if button is pressed, False if released
        """
        if not self._mouse_enabled:
            return

        # Get the joystick register for the configured port
        if self._mouse_port == 1:
            joystick = self.cia1.joystick_1
        else:
            joystick = self.cia1.joystick_2

        # Mouse buttons use active-low logic (0 = pressed, 1 = released)
        # Left button (1) = Fire (bit 4)
        # Right button (3) = Up (bit 0) - common mapping for 1351
        if button == 1:  # Left button
            if pressed:
                joystick &= ~MOUSE_LEFT_BUTTON  # Clear bit (pressed)
            else:
                joystick |= MOUSE_LEFT_BUTTON   # Set bit (released)
        elif button == 3:  # Right button
            if pressed:
                joystick &= ~MOUSE_RIGHT_BUTTON  # Clear bit (pressed)
            else:
                joystick |= MOUSE_RIGHT_BUTTON   # Set bit (released)

        # Update the joystick state
        if self._mouse_port == 1:
            self.cia1.joystick_1 = joystick
        else:
            self.cia1.joystick_2 = joystick

    # =========================================================================
    # Paddle Input Support
    # =========================================================================
    # Paddles use the same SID POT registers as the 1351 mouse, but with
    # absolute positioning instead of relative motion.
    # - Two paddles per port (directly reading the same POT registers)
    # - Each paddle has a fire button (directly triggers joystick port bits)
    # - Paddle 1: POTX ($D419), fire on bit 2 of joystick port
    # - Paddle 2: POTY ($D41A), fire on bit 3 of joystick port
    # Fire buttons active-low on the joystick port.

    _paddle_enabled: bool = False
    _paddle_port: int = 1  # Which joystick port (1 or 2)

    def enable_paddle(self, enabled: bool = True, port: int = 1) -> None:
        """Enable or disable paddle input.

        Args:
            enabled: Whether paddle input is enabled
            port: Which joystick port (1 or 2) the paddles are connected to
        """
        self._paddle_enabled = enabled
        self._paddle_port = port
        log.info(f"Paddle input {'enabled' if enabled else 'disabled'} on port {port}")

    def update_paddle_position(self, mouse_x: int, mouse_y: int, window_width: int, window_height: int) -> None:
        """Update paddle position from absolute mouse position.

        Args:
            mouse_x: Mouse X position in window (pixels)
            mouse_y: Mouse Y position in window (pixels)
            window_width: Window width (pixels)
            window_height: Window height (pixels)
        """
        if not self._paddle_enabled:
            return

        # Scale mouse position to paddle range (0-255)
        # Clamp to valid range in case mouse is outside window
        paddle_x = max(0, min(255, int((mouse_x / max(1, window_width)) * 255)))
        paddle_y = max(0, min(255, int((mouse_y / max(1, window_height)) * 255)))

        # Update SID POT registers
        self.sid.set_paddle(paddle_x, paddle_y)

    def set_paddle_button(self, button: int, pressed: bool) -> None:
        """Set paddle button state.

        C64 paddle fire buttons use different CIA bits than joystick fire:
        - Paddle 1 (X-axis paddle) fire: Bit 2 of CIA port
        - Paddle 2 (Y-axis paddle) fire: Bit 3 of CIA port

        Port 1 paddles read from $DC01 (CIA1 Port B)
        Port 2 paddles read from $DC00 (CIA1 Port A)

        Reference: https://www.c64-wiki.com/wiki/Paddle

        Args:
            button: Mouse button (1 = left → paddle 1 fire, 3 = right → paddle 2 fire)
            pressed: True if button is pressed, False if released
        """
        if not self._paddle_enabled:
            return

        # Get the joystick register for the configured port
        if self._paddle_port == 1:
            joystick = self.cia1.joystick_1
        else:
            joystick = self.cia1.joystick_2

        # Paddle buttons use active-low logic (0 = pressed, 1 = released)
        # Real C64 paddle fire buttons:
        # - Paddle 1 (X) fire = Bit 2 (directly wired to control port pin 3)
        # - Paddle 2 (Y) fire = Bit 3 (directly wired to control port pin 4)
        if button == 1:  # Left mouse button = Paddle 1 fire
            if pressed:
                joystick &= ~PADDLE_1_FIRE  # Clear bit 2 (pressed)
            else:
                joystick |= PADDLE_1_FIRE   # Set bit 2 (released)
        elif button == 3:  # Right mouse button = Paddle 2 fire
            if pressed:
                joystick &= ~PADDLE_2_FIRE  # Clear bit 3 (pressed)
            else:
                joystick |= PADDLE_2_FIRE   # Set bit 3 (released)

        # Update the joystick state
        if self._paddle_port == 1:
            self.cia1.joystick_1 = joystick
        else:
            self.cia1.joystick_2 = joystick

    # =========================================================================
    # Lightpen Input Support
    # =========================================================================
    # Lightpen uses VIC-II registers for position (not SID POT like mouse/paddle):
    # - $D013 (LPX): X coordinate divided by 2 (multiply by 2 to get actual X)
    # - $D014 (LPY): Y coordinate (same as sprite Y coordinates)
    # - Button triggers joystick fire on port 1 only (bit 4 of $DC01)
    # - Can also trigger VIC IRQ bit 3 when position is latched
    #
    # Lightpen only works on control port 1 (directly wired to VIC).
    # Reference: https://www.c64-wiki.com/wiki/Light_pen

    _lightpen_enabled: bool = False

    def enable_lightpen(self, enabled: bool = True) -> None:
        """Enable or disable lightpen input.

        Note: Lightpen only works on control port 1 (hardware limitation).

        Args:
            enabled: Whether lightpen input is enabled
        """
        self._lightpen_enabled = enabled
        log.info(f"Lightpen input {'enabled' if enabled else 'disabled'}")

    def update_lightpen_position(self, mouse_x: int, mouse_y: int,
                                  window_width: int, window_height: int) -> None:
        """Update lightpen position from mouse position.

        Maps mouse window coordinates to VIC-II lightpen registers.
        The VIC stores X/2 in $D013 and Y in $D014, using sprite coordinate space.

        Args:
            mouse_x: Mouse X position in window (pixels)
            mouse_y: Mouse Y position in window (pixels)
            window_width: Window width (pixels)
            window_height: Window height (pixels)
        """
        if not self._lightpen_enabled:
            return

        # VIC-II visible area in sprite coordinates:
        # PAL: X = 24-343 (320 pixels), Y = 50-249 (200 pixels)
        # We map the window to the visible screen area

        # X coordinate: map window X to sprite X range (24-343), then divide by 2
        # The visible screen is 320 pixels wide, starting at sprite X=24
        sprite_x = 24 + int((mouse_x / max(1, window_width)) * 320)
        sprite_x = max(0, min(511, sprite_x))  # Clamp to 9-bit range
        lpx = sprite_x // 2  # VIC stores X/2

        # Y coordinate: map window Y to sprite Y range (50-249)
        # The visible screen is 200 pixels tall, starting at sprite Y=50
        sprite_y = 50 + int((mouse_y / max(1, window_height)) * 200)
        sprite_y = max(0, min(255, sprite_y))  # Clamp to 8-bit range

        # Update VIC lightpen registers
        self.vic.regs[0x13] = lpx & 0xFF
        self.vic.regs[0x14] = sprite_y & 0xFF

    def set_lightpen_button(self, button: int, pressed: bool) -> None:
        """Set lightpen button state.

        Lightpen button is directly wired to joystick fire on port 1.
        Only left mouse button is used (lightpens have one button).

        Reference: https://www.c64-wiki.com/wiki/Light_pen

        Args:
            button: Mouse button (1 = left/lightpen button)
            pressed: True if button is pressed, False if released
        """
        if not self._lightpen_enabled:
            return

        # Lightpen only uses port 1 (hardware constraint)
        joystick = self.cia1.joystick_1

        # Lightpen button uses active-low logic (0 = pressed, 1 = released)
        # Only left button (1) triggers the lightpen
        if button == 1:
            if pressed:
                joystick &= ~LIGHTPEN_BUTTON  # Clear bit (pressed)
            else:
                joystick |= LIGHTPEN_BUTTON   # Set bit (released)

        self.cia1.joystick_1 = joystick

    # =========================================================================
    # Keyboard Joystick Emulation
    # =========================================================================
    # Maps keyboard keys to joystick directions and fire button.
    # Supports both numpad (8/2/4/6/0) and WASD+Space layouts.
    # Default port is 2 since most C64 games expect joystick in port 2.
    #
    # C64 joystick uses active-low logic (0 = pressed, 1 = released):
    # - Bit 0: Up
    # - Bit 1: Down
    # - Bit 2: Left
    # - Bit 3: Right
    # - Bit 4: Fire
    # Reference: https://www.c64-wiki.com/wiki/Joystick

    _joystick_enabled: bool = False
    _joystick_port: int = 2  # Default to port 2 (most common for C64 games)

    def enable_joystick(self, enabled: bool = True, port: int = 2) -> None:
        """Enable or disable keyboard joystick emulation.

        When enabled, keyboard keys are mapped to joystick directions:
        - Numpad: 8=Up, 2=Down, 4=Left, 6=Right, 0=Fire
        - WASD: W=Up, S=Down, A=Left, D=Right, Space=Fire

        Args:
            enabled: Whether joystick emulation is enabled
            port: Which joystick port to emulate (1 or 2, default: 2)
        """
        self._joystick_enabled = enabled
        self._joystick_port = port
        log.info(f"Keyboard joystick {'enabled' if enabled else 'disabled'} on port {port}")

    def set_joystick_direction(self, direction: int, pressed: bool) -> None:
        """Set a joystick direction or fire button state.

        Args:
            direction: Direction bit (JOYSTICK_UP, JOYSTICK_DOWN, etc.)
            pressed: True if pressed, False if released
        """
        if not self._joystick_enabled:
            return

        if self._joystick_port == 1:
            joystick = self.cia1.joystick_1
        else:
            joystick = self.cia1.joystick_2

        # Active-low logic: 0 = pressed, 1 = released
        if pressed:
            joystick &= ~direction  # Clear bit (pressed)
        else:
            joystick |= direction   # Set bit (released)

        if self._joystick_port == 1:
            self.cia1.joystick_1 = joystick
        else:
            self.cia1.joystick_2 = joystick

    # Pending key releases for non-blocking terminal input
    # Each entry is (release_cycles, row, col) - uses CPU cycles, not wall-clock time
    _pending_key_releases: list = []

    # Pygame keyboard buffer for type-ahead
    # Stores (row, col, needs_shift) tuples for keys waiting to be injected
    _pygame_key_buffer: list = []
    _pygame_keys_currently_pressed: set = set()  # Track physical key state
    _pygame_current_injection: Union[tuple, None]= None  # (row, col, needs_shift, start_cycles, released)

    # Timing in CPU cycles (not wall-clock) so keys inject correctly at any emulator speed
    # KERNAL scans keyboard once per frame (~17000-20000 cycles). We need to span one scan.
    # At ~1MHz: 20000 cycles = ~20ms (one full frame), 2000 cycles = ~2ms
    _key_hold_cycles: int = 20000   # Hold key for one full frame, guarantees KERNAL sees it
    _key_gap_cycles: int = 2000     # Gap between keys
