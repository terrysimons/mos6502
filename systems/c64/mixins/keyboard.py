"""C64 Keyboard Mixin.

Mixin for keyboard input handling.
"""

from mos6502.compat import logging, Tuple

log = logging.getLogger("c64")


class C64KeyboardMixin:
    """Mixin for keyboard input handling."""

    def inject_keyboard_buffer(self, text: str) -> None:
        """Inject a string into the KERNAL keyboard buffer.

        This writes directly to the keyboard buffer at $0277-$0280 and sets
        the buffer count at $00C6. The KERNAL will process these characters
        as if they were typed. Maximum 10 characters.

        Arguments:
            text: String to inject (max 10 chars, typically ending with \\r for RETURN)
        """
        # Convert to PETSCII (for simple ASCII chars, it's mostly the same)
        # RETURN key is 0x0D in PETSCII
        petscii_text = text.replace('\r', '\x0d').replace('\n', '\x0d')

        # Limit to 10 characters (keyboard buffer size)
        if len(petscii_text) > 10:
            log.warning(f"Keyboard buffer overflow: truncating '{text}' to 10 chars")
            petscii_text = petscii_text[:10]

        # Write characters to buffer at $0277
        for i, char in enumerate(petscii_text):
            self.cpu.ram[self.KEYBOARD_BUFFER + i] = ord(char)

        # Set buffer count at $00C6
        self.cpu.ram[self.KEYBOARD_BUFFER_SIZE] = len(petscii_text)

        log.info(f"Injected '{text.strip()}' into keyboard buffer ({len(petscii_text)} chars)")

    def inject_keyboard_string(self, text: str, cycles_per_chunk: int = 100_000) -> None:
        """Inject a string into the keyboard buffer, handling strings longer than 10 chars.

        For strings longer than 10 characters, this method injects them in chunks
        of 10 characters each, running the CPU between chunks to allow KERNAL
        to process the buffer.

        Arguments:
            text: String to inject (any length, typically ending with \\r for RETURN)
            cycles_per_chunk: CPU cycles to run between chunks (default 100,000)
        """
        from mos6502.errors import CPUCycleExhaustionError

        # Convert to PETSCII
        petscii_text = text.replace('\r', '\x0d').replace('\n', '\x0d')

        # Process in chunks of 10 characters
        chunk_size = 10
        position = 0

        while position < len(petscii_text):
            # Wait for keyboard buffer to be empty
            max_wait_cycles = 1_000_000
            waited = 0
            while int(self.cpu.ram[self.KEYBOARD_BUFFER_SIZE]) > 0 and waited < max_wait_cycles:
                try:
                    self.cpu.execute(cycles=10_000)
                except CPUCycleExhaustionError:
                    pass
                waited += 10_000

            if waited >= max_wait_cycles:
                log.warning("Timeout waiting for keyboard buffer to empty")
                break

            # Inject next chunk
            chunk = petscii_text[position:position + chunk_size]
            for i, char in enumerate(chunk):
                self.cpu.ram[self.KEYBOARD_BUFFER + i] = ord(char)
            self.cpu.ram[self.KEYBOARD_BUFFER_SIZE] = len(chunk)

            log.debug(f"Injected chunk {position//chunk_size + 1}: {len(chunk)} chars")
            position += chunk_size

            # Run CPU to process this chunk
            if position < len(petscii_text):
                try:
                    self.cpu.execute(cycles=cycles_per_chunk)
                except CPUCycleExhaustionError:
                    pass

        log.info(f"Injected '{text.strip()}' into keyboard buffer ({len(petscii_text)} chars total)")

    def _handle_pygame_keyboard(self, event, pygame) -> None:
        """Handle pygame keyboard events and update CIA1 keyboard matrix.

        Args:
            event: Pygame event
            pygame: Pygame module
        """
        # C64 keyboard matrix mapping: (row, col)
        # Reference: https://www.c64-wiki.com/wiki/Keyboard
        key_map = {
            # Row 0
            pygame.K_BACKSPACE: (0, 0),  # DEL/INST
            pygame.K_RETURN: (0, 1),     # RETURN
            pygame.K_KP_ENTER: (0, 1),   # RETURN (numeric keypad)
            pygame.K_RIGHT: (0, 2),      # CRSR →
            pygame.K_F7: (0, 3),         # F7
            pygame.K_F1: (0, 4),         # F1
            pygame.K_F3: (0, 5),         # F3
            pygame.K_F5: (0, 6),         # F5
            pygame.K_DOWN: (0, 7),       # CRSR ↓

            # Row 1
            pygame.K_3: (1, 0),
            pygame.K_w: (1, 1),
            pygame.K_a: (1, 2),
            pygame.K_4: (1, 3),
            pygame.K_z: (1, 4),
            pygame.K_s: (1, 5),
            pygame.K_e: (1, 6),
            pygame.K_LSHIFT: (1, 7),     # Left SHIFT

            # Row 2
            pygame.K_5: (2, 0),
            pygame.K_r: (2, 1),
            pygame.K_d: (2, 2),
            pygame.K_6: (2, 3),
            pygame.K_c: (2, 4),
            pygame.K_f: (2, 5),
            pygame.K_t: (2, 6),
            pygame.K_x: (2, 7),

            # Row 3
            pygame.K_7: (3, 0),
            pygame.K_y: (3, 1),
            pygame.K_g: (3, 2),
            pygame.K_8: (3, 3),
            pygame.K_b: (3, 4),
            pygame.K_h: (3, 5),
            pygame.K_u: (3, 6),
            pygame.K_v: (3, 7),

            # Row 4
            pygame.K_9: (4, 0),
            pygame.K_i: (4, 1),
            pygame.K_j: (4, 2),
            pygame.K_0: (4, 3),
            pygame.K_m: (4, 4),
            pygame.K_k: (4, 5),
            pygame.K_o: (4, 6),
            pygame.K_n: (4, 7),

            # Row 5
            pygame.K_PLUS: (5, 0),       # +
            pygame.K_p: (5, 1),
            pygame.K_l: (5, 2),
            pygame.K_MINUS: (5, 3),      # -
            pygame.K_PERIOD: (5, 4),     # .
            pygame.K_COLON: (5, 5),      # :
            pygame.K_AT: (5, 6),         # @
            pygame.K_COMMA: (5, 7),      # ,

            # Row 6
            # pygame.K_POUND: (6, 0),    # £ (pound symbol on C64, no direct US keyboard equivalent)
            pygame.K_QUOTE: (7, 3),      # Map to '2' key - SHIFT+2 produces " (double quote) for BASIC strings
            pygame.K_ASTERISK: (6, 1),   # *
            pygame.K_KP_MULTIPLY: (6, 1),  # * on numpad
            pygame.K_SEMICOLON: (6, 2),  # ;
            pygame.K_HOME: (6, 3),       # HOME/CLR
            # pygame.K_CLR: (6, 4),      # CLR (combined with HOME)
            pygame.K_EQUALS: (6, 5),     # =
            pygame.K_UP: (6, 6),         # ↑ (up arrow, mapped to up key)
            pygame.K_SLASH: (6, 7),      # /
            # US keyboard Shift+number symbols mapped to C64 equivalents
            # On US keyboard: Shift+8=*, Shift+9=(, Shift+0=)
            # On C64: Shift+8=(, Shift+9=), * is separate key
            pygame.K_LEFTPAREN: (3, 3),  # ( -> maps to '8' key (C64: Shift+8 = '(')
            pygame.K_RIGHTPAREN: (4, 0), # ) -> maps to '9' key (C64: Shift+9 = ')')

            # Row 7
            pygame.K_1: (7, 0),
            pygame.K_LEFT: (7, 1),       # ← (CRSR left, using arrow key)
            pygame.K_LCTRL: (7, 2),      # CTRL
            pygame.K_2: (7, 3),
            pygame.K_QUOTEDBL: (7, 3),   # " (double quote) - same as '2' key (SHIFT+2 on C64)
            pygame.K_SPACE: (7, 4),      # SPACE
            # pygame.K_COMMODORE: (7, 5), # C= (no pygame equivalent)
            pygame.K_q: (7, 6),
            pygame.K_ESCAPE: (7, 7),     # RUN/STOP (mapped to ESC)
        }

        # Keys that should be held directly (not buffered) - modifiers and control keys
        # These affect the state of other keys and need real-time response
        direct_keys = {
            pygame.K_LSHIFT, pygame.K_RSHIFT,  # SHIFT modifiers
            pygame.K_LCTRL, pygame.K_RCTRL,    # CTRL
            pygame.K_ESCAPE,                    # RUN/STOP
        }

        # Keyboard-to-joystick mappings when joystick emulation is enabled
        # Numpad: 8=Up, 2=Down, 4=Left, 6=Right, 0=Fire, 5=Fire (alt)
        # Cursor keys: Up/Down/Left/Right arrows, Right Ctrl=Fire
        joystick_key_map = {
            # Numpad
            pygame.K_KP8: JOYSTICK_UP,
            pygame.K_KP2: JOYSTICK_DOWN,
            pygame.K_KP4: JOYSTICK_LEFT,
            pygame.K_KP6: JOYSTICK_RIGHT,
            pygame.K_KP0: JOYSTICK_FIRE,
            pygame.K_KP5: JOYSTICK_FIRE,      # Alt fire on numpad center
            # Cursor keys (when joystick enabled, these become joystick instead of C64 cursor)
            pygame.K_UP: JOYSTICK_UP,
            pygame.K_DOWN: JOYSTICK_DOWN,
            pygame.K_LEFT: JOYSTICK_LEFT,
            pygame.K_RIGHT: JOYSTICK_RIGHT,
            pygame.K_RCTRL: JOYSTICK_FIRE,    # Right Ctrl = Fire
            pygame.K_KP_ENTER: JOYSTICK_FIRE, # Numpad Enter = Fire
        }

        if event.type == pygame.KEYDOWN:
            # Log all key presses with key code and name
            key_name = pygame.key.name(event.key) if hasattr(pygame.key, 'name') else str(event.key)

            # Try to get ASCII representation
            try:
                ascii_char = chr(event.key) if 32 <= event.key < 127 else f"<{event.key}>"
                ascii_code = event.key
            except (ValueError, OverflowError):
                ascii_char = f"<non-printable>"
                ascii_code = event.key

            # Handle Ctrl+V for paste from system clipboard
            ctrl_held = bool(event.mod & (pygame.KMOD_LCTRL | pygame.KMOD_RCTRL))
            if ctrl_held and event.key == pygame.K_v:
                try:
                    clipboard_text = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if clipboard_text:
                        # Decode bytes to string if needed
                        if isinstance(clipboard_text, bytes):
                            clipboard_text = clipboard_text.decode('utf-8', errors='ignore')
                        # Remove null terminator if present
                        clipboard_text = clipboard_text.rstrip('\x00')
                        if clipboard_text:
                            self._paste_text(clipboard_text)
                            log.info(f"Pasted {len(clipboard_text)} characters from clipboard")
                except Exception as e:
                    log.warning(f"Paste failed: {e}")
                return

            # Handle joystick keys first (if joystick enabled)
            if self._joystick_enabled and event.key in joystick_key_map:
                direction = joystick_key_map[event.key]
                self.set_joystick_direction(direction, True)
                if DEBUG_KEYBOARD:
                    log.info(f"*** JOYSTICK KEYDOWN: key={key_name}, direction=0x{direction:02X} ***")
                return  # Don't process as keyboard key

            # US keyboard to C64 symbol remapping when SHIFT is held
            # US keyboard: Shift+8=*, Shift+9=(, Shift+0=)
            # C64 keyboard: Shift+8=(, Shift+9=), * is separate key
            # Remap these to produce expected characters on C64
            shift_held = bool(event.mod & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT))
            remapped_key = event.key
            remap_needs_shift = False
            remap_suppress_shift = False
            if shift_held:
                if event.key == pygame.K_8:
                    # US Shift+8 = * → C64 * key (must suppress shift!)
                    remapped_key = pygame.K_ASTERISK
                    remap_needs_shift = False
                    remap_suppress_shift = True  # User is holding shift, but we want unshifted *
                elif event.key == pygame.K_9:
                    # US Shift+9 = ( → C64 Shift+8
                    remapped_key = pygame.K_8
                    remap_needs_shift = True
                elif event.key == pygame.K_0:
                    # US Shift+0 = ) → C64 Shift+9
                    remapped_key = pygame.K_9
                    remap_needs_shift = True

            if remapped_key in key_map:
                row, col = key_map[remapped_key]

                # Track physical key state
                self._pygame_keys_currently_pressed.add(event.key)

                # Direct keys (modifiers) are pressed immediately for real-time feel
                if event.key in direct_keys:
                    self.cia1.press_key(row, col)
                else:
                    # Buffer the key for injection with proper timing
                    # Some keys need SHIFT to produce the expected character on C64:
                    # - Quote/double-quote: SHIFT+2 on C64
                    # - Parentheses: SHIFT+8 for '(', SHIFT+9 for ')' on C64
                    # - Remapped shifted number keys (set above)
                    needs_shift = (remap_needs_shift or
                                   event.key == pygame.K_QUOTE or
                                   event.key == pygame.K_QUOTEDBL or
                                   event.key == pygame.K_LEFTPAREN or
                                   event.key == pygame.K_RIGHTPAREN)
                    self._buffer_pygame_key(row, col, needs_shift, remap_suppress_shift)

                if DEBUG_KEYBOARD:
                    petscii_key = self.cia1._get_key_name(row, col)
                    buffered = "BUFFERED" if event.key not in direct_keys else "DIRECT"
                    log.info(f"*** KEYDOWN [{buffered}]: pygame='{key_name}' (code={event.key}), ASCII='{ascii_char}' (0x{ascii_code:02X}), matrix=({row},{col}), PETSCII={petscii_key}, buffer_len={len(self._pygame_key_buffer)} ***")
            else:
                if DEBUG_KEYBOARD:
                    log.info(f"*** UNMAPPED KEYDOWN: pygame='{key_name}' (code={event.key}), ASCII='{ascii_char}' ***")

        elif event.type == pygame.KEYUP:
            # Handle joystick keys first (if joystick enabled)
            if self._joystick_enabled and event.key in joystick_key_map:
                direction = joystick_key_map[event.key]
                self.set_joystick_direction(direction, False)
                if DEBUG_KEYBOARD:
                    key_name = pygame.key.name(event.key) if hasattr(pygame.key, 'name') else str(event.key)
                    log.info(f"*** JOYSTICK KEYUP: key={key_name}, direction=0x{direction:02X} ***")
                return  # Don't process as keyboard key

            if event.key in key_map:
                row, col = key_map[event.key]

                # Track physical key state
                self._pygame_keys_currently_pressed.discard(event.key)

                # Direct keys are released immediately
                if event.key in direct_keys:
                    self.cia1.release_key(row, col)

                # Buffered keys don't need explicit release - buffer handles timing

                if DEBUG_KEYBOARD:
                    log.info(f"*** KEYUP: pygame key {event.key}, row={row}, col={col} ***")

    def ascii_to_key_press(self, char: str) -> tuple:
        """Convert ASCII character to C64 key press.

        Arguments:
            char: Single ASCII character

        Returns:
            Tuple of (needs_shift, row, col) or None if not mappable
        """
        if char in self.ASCII_SHIFTED:
            shift_row, shift_col, key_row, key_col = self.ASCII_SHIFTED[char]
            return (True, key_row, key_col)
        elif char in self.ASCII_TO_MATRIX:
            pos = self.ASCII_TO_MATRIX[char]
            if pos is not None:
                return (False, pos[0], pos[1])
        return None

    def type_character(self, char: str, hold_cycles: int = 5000) -> None:
        """Simulate typing a character on the C64 keyboard.

        Arguments:
            char: Single ASCII character to type
            hold_cycles: Number of CPU cycles to hold the key down
        """
        key_info = self.ascii_to_key_press(char)
        if key_info is None:
            log.warning(f"Cannot type character: {repr(char)}")
            return

        needs_shift, row, col = key_info

        # Press SHIFT if needed
        if needs_shift:
            self.cia1.press_key(1, 7)  # Left SHIFT

        # Press the key
        self.cia1.press_key(row, col)

        # Run CPU for some cycles to let the KERNAL process the keypress
        try:
            self.cpu.execute(cycles=hold_cycles)
        except errors.CPUCycleExhaustionError:
            pass

        # Release the key
        self.cia1.release_key(row, col)

        # Release SHIFT if it was pressed
        if needs_shift:
            self.cia1.release_key(1, 7)

        # Run a bit more to ensure key release is processed
        try:
            self.cpu.execute(cycles=hold_cycles // 2)
        except errors.CPUCycleExhaustionError:
            pass

    def type_string(self, text: str, hold_cycles: int = 5000) -> None:
        """Type a string of characters on the C64 keyboard.

        Arguments:
            text: String to type
            hold_cycles: Number of CPU cycles to hold each key down
        """
        for char in text:
            self.type_character(char, hold_cycles)

    # -------------------------------------------------------------------------
    # Mouse Input (1351 proportional mouse emulation)
    # -------------------------------------------------------------------------
    # The Commodore 1351 mouse uses:
    # - SID POT registers ($D419/$D41A) for position (relative motion, wraps 0-255)
    # - Joystick port for buttons (active low):
    #   - Left button = Fire (bit 4)
    #   - Right button = Up (bit 0) in some implementations
    # Mouse is typically plugged into Port 1 (joystick_1)

    _mouse_enabled: bool = False
    _mouse_port: int = 1  # Which joystick port (1 or 2)
    _mouse_sensitivity: float = 1.0  # Scale factor for mouse motion

    def _queue_key_release(self, row: int, col: int) -> bool:
        """Queue a key for release after a delay (cycle-based, not wall-clock).

        Uses CPU cycles for timing so key handling works correctly at any
        emulator speed (throttled or unthrottled).

        Implements debouncing: if this key already has a pending release,
        the keypress is skipped entirely to prevent key repeat issues.

        Args:
            row: Keyboard matrix row
            col: Keyboard matrix column

        Returns:
            True if key was queued, False if skipped due to debouncing
        """
        # Check if this key already has a pending release (debounce)
        for _, pending_row, pending_col in self._pending_key_releases:
            if pending_row == row and pending_col == col:
                # Key already pending - skip this press (debounce)
                return False

        release_cycles = self.cpu.cycles_executed + self._key_hold_cycles
        self._pending_key_releases.append((release_cycles, row, col))
        return True

    def _process_pending_key_releases(self) -> None:
        """Process any pending key releases (call from main loop).

        Uses CPU cycles for timing, which scales correctly with emulator speed.
        """
        if not self._pending_key_releases:
            return

        current_cycles = self.cpu.cycles_executed
        still_pending = []
        for release_cycles, row, col in self._pending_key_releases:
            if current_cycles >= release_cycles:
                self.cia1.release_key(row, col)
            else:
                still_pending.append((release_cycles, row, col))
        self._pending_key_releases = still_pending

    def _buffer_pygame_key(self, row: int, col: int, needs_shift: bool = False,
                            suppress_shift: bool = False) -> None:
        """Buffer a keypress from pygame for injection into CIA.

        Keys are buffered and injected one at a time with proper timing
        to ensure the KERNAL sees every keypress.

        Args:
            row: C64 keyboard matrix row
            col: C64 keyboard matrix column
            needs_shift: If True, press SHIFT along with this key
            suppress_shift: If True, release SHIFT while pressing this key
                           (for when user is holding shift but we want unshifted char)
        """
        self._pygame_key_buffer.append((row, col, needs_shift, suppress_shift))

    def _paste_text(self, text: str) -> None:
        """Paste text by buffering keystrokes for each character.

        Converts ASCII/Unicode text to C64 key matrix positions and buffers
        them for injection via the pygame key buffer system.

        Args:
            text: Text to paste (ASCII characters)
        """
        # ASCII character to C64 keyboard matrix mapping: (row, col, needs_shift)
        # Based on the C64 keyboard matrix
        ascii_to_matrix = {
            # Letters (unshifted = uppercase on C64)
            'A': (1, 2, False), 'B': (3, 4, False), 'C': (2, 4, False),
            'D': (2, 2, False), 'E': (1, 6, False), 'F': (2, 5, False),
            'G': (3, 2, False), 'H': (3, 5, False), 'I': (4, 1, False),
            'J': (4, 2, False), 'K': (4, 5, False), 'L': (5, 2, False),
            'M': (4, 4, False), 'N': (4, 7, False), 'O': (4, 6, False),
            'P': (5, 1, False), 'Q': (7, 6, False), 'R': (2, 1, False),
            'S': (1, 5, False), 'T': (2, 6, False), 'U': (3, 6, False),
            'V': (3, 7, False), 'W': (1, 1, False), 'X': (2, 7, False),
            'Y': (3, 1, False), 'Z': (1, 4, False),
            # Lowercase -> same as uppercase (C64 types uppercase by default)
            'a': (1, 2, False), 'b': (3, 4, False), 'c': (2, 4, False),
            'd': (2, 2, False), 'e': (1, 6, False), 'f': (2, 5, False),
            'g': (3, 2, False), 'h': (3, 5, False), 'i': (4, 1, False),
            'j': (4, 2, False), 'k': (4, 5, False), 'l': (5, 2, False),
            'm': (4, 4, False), 'n': (4, 7, False), 'o': (4, 6, False),
            'p': (5, 1, False), 'q': (7, 6, False), 'r': (2, 1, False),
            's': (1, 5, False), 't': (2, 6, False), 'u': (3, 6, False),
            'v': (3, 7, False), 'w': (1, 1, False), 'x': (2, 7, False),
            'y': (3, 1, False), 'z': (1, 4, False),
            # Numbers
            '1': (7, 0, False), '2': (7, 3, False), '3': (1, 0, False),
            '4': (1, 3, False), '5': (2, 0, False), '6': (2, 3, False),
            '7': (3, 0, False), '8': (3, 3, False), '9': (4, 0, False),
            '0': (4, 3, False),
            # Symbols (unshifted)
            ' ': (7, 4, False),   # SPACE
            '\r': (0, 1, False),  # RETURN
            '\n': (0, 1, False),  # RETURN (newline)
            ',': (5, 7, False),   # COMMA
            '.': (5, 4, False),   # PERIOD
            ':': (5, 5, False),   # COLON
            ';': (6, 2, False),   # SEMICOLON
            '/': (6, 7, False),   # SLASH
            '=': (6, 5, False),   # EQUALS
            '+': (5, 0, False),   # PLUS
            '-': (5, 3, False),   # MINUS
            '*': (6, 1, False),   # ASTERISK
            '@': (5, 6, False),   # AT
            # Shifted symbols
            '!': (7, 0, True),    # SHIFT+1
            '"': (7, 3, True),    # SHIFT+2 (quote)
            '#': (1, 0, True),    # SHIFT+3
            '$': (1, 3, True),    # SHIFT+4
            '%': (2, 0, True),    # SHIFT+5
            '&': (2, 3, True),    # SHIFT+6
            "'": (3, 0, True),    # SHIFT+7 (apostrophe)
            '(': (3, 3, True),    # SHIFT+8
            ')': (4, 0, True),    # SHIFT+9
            '<': (5, 7, True),    # SHIFT+COMMA
            '>': (5, 4, True),    # SHIFT+PERIOD
            '?': (6, 7, True),    # SHIFT+SLASH
        }

        for char in text:
            if char in ascii_to_matrix:
                row, col, needs_shift = ascii_to_matrix[char]
                self._buffer_pygame_key(row, col, needs_shift, suppress_shift=False)
            else:
                # Skip unmapped characters
                log.debug(f"Paste: skipping unmapped character '{char}' (0x{ord(char):02X})")

    def _process_pygame_key_buffer(self) -> None:
        """Process the pygame key buffer, injecting keys into CIA.

        Called from main loop. Handles timing for key injection using CPU cycles
        so keys inject faster when emulator runs faster than real-time.
        - Press key, hold for ~20000 cycles (~20ms at 1MHz)
        - Release key, wait ~5000 cycles gap
        - Repeat for next key
        """
        current_cycles = self.cpu.cycles_executed

        # If we have a current injection in progress, check timing
        if self._pygame_current_injection is not None:
            row, col, needs_shift, suppress_shift, start_cycles, released = self._pygame_current_injection

            if not released:
                # Key is being held - check if hold cycles elapsed
                if current_cycles - start_cycles >= self._key_hold_cycles:
                    # Release the key
                    self.cia1.release_key(row, col)
                    if needs_shift:
                        self.cia1.release_key(1, 7)  # Release SHIFT
                    if suppress_shift:
                        # Re-press shift if user is still holding it physically
                        import pygame
                        if pygame.K_LSHIFT in self._pygame_keys_currently_pressed or \
                           pygame.K_RSHIFT in self._pygame_keys_currently_pressed:
                            self.cia1.press_key(1, 7)
                    # Mark as released, record release cycle
                    self._pygame_current_injection = (row, col, needs_shift, suppress_shift, current_cycles, True)
            else:
                # Key is released - check if gap cycles elapsed
                if current_cycles - start_cycles >= self._key_gap_cycles:
                    # Done with this key, clear injection
                    self._pygame_current_injection = None

        # If no current injection and buffer has keys, start next one
        if self._pygame_current_injection is None and self._pygame_key_buffer:
            row, col, needs_shift, suppress_shift = self._pygame_key_buffer.pop(0)
            # Press the key
            if needs_shift:
                self.cia1.press_key(1, 7)  # Press SHIFT
            if suppress_shift:
                self.cia1.release_key(1, 7)  # Release SHIFT even if physically held
            self.cia1.press_key(row, col)
            # Record injection start (not released yet)
            self._pygame_current_injection = (row, col, needs_shift, suppress_shift, current_cycles, False)

    def _handle_terminal_input(self, char: str) -> bool:
        """Handle a single character of terminal input.

        Converts ASCII input to C64 key presses. Handles escape sequences
        for arrow keys and other special keys. Uses non-blocking key release
        queue to avoid stalling the main loop.

        Arguments:
            char: Single character from terminal input

        Returns:
            True if Ctrl+C was pressed (should exit), False otherwise
        """
        import sys as _sys

        # Handle special keys
        if char == '\x03':  # Ctrl+C
            return True
        elif char == '\x1b':  # Escape sequence
            # Read the rest of the escape sequence
            try:
                import select
                if select.select([_sys.stdin], [], [], 0.1)[0]:
                    seq = _sys.stdin.read(2)
                    if seq == '[A':  # Up arrow -> CRSR UP (SHIFT + CRSR DOWN)
                        self.cia1.press_key(1, 7)  # SHIFT
                        self.cia1.press_key(0, 7)  # CRSR DOWN
                        self._queue_key_release(0, 7)
                        self._queue_key_release(1, 7)
                    elif seq == '[B':  # Down arrow -> CRSR DOWN
                        self.cia1.press_key(0, 7)
                        self._queue_key_release(0, 7)
                    elif seq == '[C':  # Right arrow -> CRSR RIGHT
                        self.cia1.press_key(0, 2)
                        self._queue_key_release(0, 2)
                    elif seq == '[D':  # Left arrow -> CRSR LEFT (SHIFT + CRSR RIGHT)
                        self.cia1.press_key(1, 7)  # SHIFT
                        self.cia1.press_key(0, 2)  # CRSR RIGHT
                        self._queue_key_release(0, 2)
                        self._queue_key_release(1, 7)
                    elif seq == '[3':  # Delete key (followed by ~)
                        if select.select([_sys.stdin], [], [], 0.1)[0]:
                            _sys.stdin.read(1)  # Consume the ~
                        self.cia1.press_key(0, 0)  # DEL
                        self._queue_key_release(0, 0)
            except ImportError:
                pass  # select not available
        elif char == '\x7f':  # Backspace
            # Check if key is already pending (debounce)
            already_pending = any(r == 0 and c == 0 for _, r, c in self._pending_key_releases)
            if not already_pending:
                self.cia1.press_key(0, 0)  # DEL
                self._queue_key_release(0, 0)
        else:
            # Regular character - press key and queue release
            key_info = self.ascii_to_key_press(char)
            if key_info:
                needs_shift, row, col = key_info
                # Check if key is already pending (debounce)
                already_pending = any(r == row and c == col for _, r, c in self._pending_key_releases)
                if not already_pending:
                    if needs_shift:
                        self.cia1.press_key(1, 7)  # SHIFT
                    self.cia1.press_key(row, col)
                    self._queue_key_release(row, col)
                    if needs_shift:
                        self._queue_key_release(1, 7)

        return False
