"""C64 Display Mixin.

Mixin for display and rendering (pygame and terminal).
"""

from mos6502.compat import logging
from c64.vic import (
    COLORS,
    c64_to_ansi_fg,
    c64_to_ansi_bg,
    ANSI_RESET,
)

log = logging.getLogger("c64")


class C64DisplayMixin:
    """Mixin for display and rendering (pygame and terminal)."""

    def init_pygame_display(self) -> bool:
        """Initialize pygame display.

        Returns:
            True if pygame was successfully initialized, False otherwise
        """
        try:
            import pygame
            self.pygame_available = True
        except ImportError:
            log.error("Pygame not installed. Install with: pip install pygame-ce")
            return False

        try:
            pygame.init()

            # Get display dimensions from VIC (hardware characteristics)
            total_width = self.vic.total_width
            total_height = self.vic.total_height

            # Create window with scaled dimensions
            # Disable pygame vsync - we do our own frame timing via VIC
            # This prevents pygame.display.flip() from blocking
            width = total_width * self.scale
            height = total_height * self.scale
            try:
                # pygame 2.0+ supports vsync parameter
                self.pygame_screen = pygame.display.set_mode((width, height), vsync=0)
            except TypeError:
                # Older pygame doesn't support vsync parameter
                self.pygame_screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption(f"C64 Emulator - {self.get_video_standard()} ({self.video_chip})")

            # Enable key repeat (delay=300ms before repeat, interval=30ms between repeats)
            # This matches typical terminal key repeat behavior
            pygame.key.set_repeat(300, 30)

            # Initialize clipboard support for Ctrl+V paste
            try:
                pygame.scrap.init()
            except Exception as e:
                log.warning(f"Clipboard support unavailable: {e}")

            # Create the rendering surface (384x270 with border)
            self.pygame_surface = pygame.Surface((total_width, total_height))

            log.info(f"Pygame display initialized: {width}x{height} (scale={self.scale})")
            return True

        except Exception as e:
            log.error(f"Failed to initialize pygame: {e}")
            self.pygame_available = False
            return False

    def set_speed_sample_count(self, count: int) -> None:
        """Set the number of samples for rolling average speed calculation.

        Args:
            count: Number of samples to keep (e.g., 10 = 10 second rolling window).
                   Set to 0 to disable rolling average.
        """
        from collections import deque
        self._speed_sample_count = count
        # Use positional args for MicroPython compatibility (no kwargs on deque)
        if count > 0:
            self._speed_samples = deque((), count)
        else:
            self._speed_samples = deque((), 1)  # Keep at least 1 for the API
            self._speed_samples.clear()

    def _record_speed_sample(self) -> bool:
        """Record a speed sample for rolling average (rate-limited to once per second).

        Returns:
            True if a sample was recorded, False if rate-limited.
        """
        import time
        now = time.time()

        # Only record once per second
        if self._last_sample_time > 0 and now - self._last_sample_time < 1.0:
            return False

        # Calculate cycles since last sample
        current_cycles = self.cpu.cycles_executed
        if self._last_sample_time > 0:
            delta_time = now - self._last_sample_time
            delta_cycles = current_cycles - self._last_sample_cycles
            if delta_time > 0:
                sample_cps = delta_cycles / delta_time
                self._speed_samples.append(sample_cps)

        self._last_sample_time = now
        self._last_sample_cycles = current_cycles
        return True

    def _update_pygame_title(self, pygame) -> None:
        """Update pygame window title with speed stats (rate-limited to once per second)."""
        if not self._record_speed_sample():
            return

        # Use rolling average if we have samples
        if self._speed_samples:
            cycles_per_second = sum(self._speed_samples) / len(self._speed_samples)
            real_cpu_freq = self.video_timing.cpu_freq
            speedup = cycles_per_second / real_cpu_freq
            chip = self.video_timing.chip_name
            region = "PAL" if chip == "6569" else "NTSC"
            actual_mhz = cycles_per_second / 1e6
            real_mhz = real_cpu_freq / 1e6
            title = (f"C64 Emulator - {region} ({chip}) - "
                     f"{actual_mhz:.3f}MHz ({speedup:.1%} of {real_mhz:.3f}MHz)")
            pygame.display.set_caption(title)

    def show_screen(self) -> None:
        """Display the C64 screen (40x25 characters from screen RAM at $0400)."""
        screen_start = 0x0400
        screen_end = 0x07E7
        cols = 40
        rows = 25

        print("\n" + "=" * 42)
        print(" C64 SCREEN")
        print("=" * 42)

        for row in range(rows):
            line = ""
            for col in range(cols):
                addr = screen_start + (row * cols) + col
                if addr <= screen_end:
                    petscii = int(self.cpu.ram[addr])
                    line += self.petscii_to_ascii(petscii)
                else:
                    line += " "
            # Only print non-empty lines
            if line.strip():
                print(line.rstrip())
            else:
                print()

        print("=" * 42)

    def _render_terminal(self) -> None:
        """Render C64 screen to terminal with dirty region optimization."""
        import sys as _sys

        screen_start = 0x0400
        cols = 40
        rows = 25

        # Header row offset (4 lines: title, speed, separator, top border)
        header_offset = 4

        # Check if we need a full redraw
        needs_full = self.dirty_tracker.needs_full_redraw()

        if needs_full:
            # Full screen redraw
            _sys.stdout.write("\033[2J\033[H")  # Clear screen and move to top

            # Render C64 screen (40x25 characters)
            _sys.stdout.write("=" * 42 + "\n")
            _sys.stdout.write(" C64 SCREEN\n")
            _sys.stdout.write("=" * 42 + "\n")

            for row in range(rows):
                line = ""
                for col in range(cols):
                    addr = screen_start + (row * cols) + col
                    petscii = int(self.cpu.ram[addr])
                    line += self.petscii_to_ascii(petscii)
                _sys.stdout.write(line + "\n")

            _sys.stdout.write("=" * 42 + "\n")

        elif self.dirty_tracker.has_changes():
            # Incremental update - only redraw dirty cells
            dirty_cells = self.dirty_tracker.get_dirty_cells()
            for row, col in dirty_cells:
                # Move cursor to the cell position
                # Terminal rows are 1-indexed, add header offset
                term_row = row + header_offset + 1
                term_col = col + 1
                _sys.stdout.write(f"\033[{term_row};{term_col}H")

                # Get and render the character
                addr = screen_start + (row * cols) + col
                petscii = int(self.cpu.ram[addr])
                char = self.petscii_to_ascii(petscii)
                _sys.stdout.write(char)

        # Always update status line (at row 29: 3 header + 25 screen + 1 border)
        # Add extra row if drive is attached
        status_row = header_offset + rows + 2

        # Move to status line and update it
        _sys.stdout.write(f"\033[{status_row};1H")
        status = self._format_cpu_status("C64")
        # Clear line and write status
        _sys.stdout.write("\033[K" + status)

        # Add drive status line if drive is attached
        drive_status = self._format_drive_status()
        if drive_status:
            _sys.stdout.write(f"\n\033[K" + drive_status)

        # Clear dirty flags after rendering
        self.dirty_tracker.clear()

    def _render_terminal_debug(self) -> None:
        """Render C64 screen and CPU state to terminal (for pygame mode debug).

        This version uses ANSI escape codes to update in place without scrolling.
        It shows the screen, CPU registers, and current instruction.
        """
        import sys as _sys

        screen_start = 0x0400
        cols = 40
        rows = 25

        # Get colors
        bg_color = self.vic.regs[0x21] & 0x0F
        bg_ansi = c64_to_ansi_bg(bg_color)
        border_color = self.vic.regs[0x20] & 0x0F
        border_ansi = c64_to_ansi_bg(border_color)

        # Clear screen and move to top
        _sys.stdout.write("\033[2J\033[H")

        # Border and title
        _sys.stdout.write(border_ansi + " " * 44 + ANSI_RESET + "\n")
        _sys.stdout.write(border_ansi + " " + ANSI_RESET +
                         " C64 (pygame mode) " +
                         border_ansi + " " * 24 + ANSI_RESET + "\n")
        _sys.stdout.write(border_ansi + " " * 44 + ANSI_RESET + "\n")

        # Screen content with colors
        for row in range(rows):
            # Left border
            _sys.stdout.write(border_ansi + "  " + ANSI_RESET)

            last_fg = -1
            for col in range(cols):
                screen_addr = screen_start + (row * cols) + col
                color_addr = row * cols + col
                petscii = int(self.cpu.ram[screen_addr])
                fg_color = self.memory.ram_color[color_addr] & 0x0F

                # Check for reverse video (screen codes 128-255)
                if petscii >= 128:
                    char = self.petscii_to_ascii(petscii)
                    _sys.stdout.write(c64_to_ansi_bg(fg_color) +
                                    c64_to_ansi_fg(bg_color) + char)
                    last_fg = -1
                else:
                    if fg_color != last_fg:
                        _sys.stdout.write(bg_ansi + c64_to_ansi_fg(fg_color))
                        last_fg = fg_color
                    char = self.petscii_to_ascii(petscii)
                    _sys.stdout.write(char)

            # Right border
            _sys.stdout.write(ANSI_RESET + border_ansi + "  " + ANSI_RESET + "\n")

        # Bottom border
        _sys.stdout.write(border_ansi + " " * 44 + ANSI_RESET + "\n")

        # C64 CPU status line
        status = self._format_cpu_status("C64")
        _sys.stdout.write(status + "\n")

        # Drive status line (if drive is attached)
        drive_status = self._format_drive_status()
        if drive_status:
            _sys.stdout.write(drive_status + "\n")

    def _render_terminal_repl(self) -> None:
        """Render C64 screen to terminal for REPL mode with color support.

        This version uses \r\n for line endings to work correctly in cbreak mode.
        Colors are rendered using ANSI 256-color escape codes.
        """
        import sys as _sys

        # Record speed sample for rolling average (once per second)
        self._record_speed_sample()

        screen_start = 0x0400
        cols = 40
        rows = 25

        # Get background color from VIC register $D021
        bg_color = self.vic.regs[0x21] & 0x0F
        bg_ansi = c64_to_ansi_bg(bg_color)

        # Get border color from VIC register $D020
        border_color = self.vic.regs[0x20] & 0x0F
        border_ansi = c64_to_ansi_bg(border_color)

        # Header row offset (4 lines: title, speed, separator, top border)
        header_offset = 4

        # Check if we need a full redraw
        needs_full = self.dirty_tracker.needs_full_redraw()

        if needs_full:
            # Full screen redraw
            _sys.stdout.write("\033[2J\033[H")  # Clear screen and move to top

            # Terminal header (not part of C64 display)
            title_line = f"C64 REPL (Ctrl+C to exit) - {self.get_video_standard()} ({self.video_chip})"
            stats = self.get_speed_stats()
            if stats:
                # Prefer rolling average if available, otherwise use lifetime average
                cps = stats.get('rolling_cycles_per_second', stats['cycles_per_second'])
                speedup = stats.get('rolling_speedup', stats['speedup'])
                actual_mhz = cps / 1e6
                real_mhz = stats['real_cpu_freq'] / 1e6
                speed_line = f"{actual_mhz:.3f}MHz ({speedup:.1%} of {real_mhz:.3f}MHz)"
            else:
                speed_line = "(calculating speed...)"
            _sys.stdout.write(f"{title_line}\r\n")
            _sys.stdout.write(f"{speed_line}\r\n")
            _sys.stdout.write("=" * 44 + "\r\n")

            # C64 screen with border (top border)
            _sys.stdout.write(border_ansi + " " * 44 + ANSI_RESET + "\r\n")

            for row in range(rows):
                # Left border
                _sys.stdout.write(border_ansi + "  " + ANSI_RESET)

                # Screen content with colors
                last_fg = -1
                for col in range(cols):
                    screen_addr = screen_start + (row * cols) + col
                    color_addr = row * cols + col
                    petscii = int(self.cpu.ram[screen_addr])
                    fg_color = self.memory.ram_color[color_addr] & 0x0F

                    # Check for reverse video (screen codes 128-255)
                    if petscii >= 128:
                        # Reverse video: swap fg and bg
                        char = self.petscii_to_ascii(petscii)
                        _sys.stdout.write(c64_to_ansi_bg(fg_color) +
                                        c64_to_ansi_fg(bg_color) + char)
                        last_fg = -1  # Force color reset
                    else:
                        # Normal: fg on bg
                        if fg_color != last_fg:
                            _sys.stdout.write(bg_ansi + c64_to_ansi_fg(fg_color))
                            last_fg = fg_color
                        char = self.petscii_to_ascii(petscii)
                        _sys.stdout.write(char)

                # Right border and reset
                _sys.stdout.write(ANSI_RESET + border_ansi + "  " + ANSI_RESET + "\r\n")

            # Bottom border
            _sys.stdout.write(border_ansi + " " * 44 + ANSI_RESET + "\r\n")

        elif self.dirty_tracker.has_changes():
            # Incremental update - only redraw dirty cells
            dirty_cells = self.dirty_tracker.get_dirty_cells()
            for row, col in dirty_cells:
                # Move cursor to the cell position
                # Terminal rows are 1-indexed, add header offset, +2 for left border
                term_row = row + header_offset + 1
                term_col = col + 3  # +2 for border, +1 for 1-indexing
                _sys.stdout.write(f"\033[{term_row};{term_col}H")

                # Get screen and color data
                screen_addr = screen_start + (row * cols) + col
                color_addr = row * cols + col
                petscii = int(self.cpu.ram[screen_addr])
                fg_color = self.memory.ram_color[color_addr] & 0x0F

                # Render with color
                if petscii >= 128:
                    # Reverse video
                    char = self.petscii_to_ascii(petscii)
                    _sys.stdout.write(c64_to_ansi_bg(fg_color) +
                                    c64_to_ansi_fg(bg_color) + char + ANSI_RESET)
                else:
                    char = self.petscii_to_ascii(petscii)
                    _sys.stdout.write(bg_ansi + c64_to_ansi_fg(fg_color) + char + ANSI_RESET)

        # Always update status line (at row 30: 3 header + 25 screen + 1 border + 1)
        status_row = header_offset + rows + 2

        # Move to status line and update it
        _sys.stdout.write(f"\033[{status_row};1H")
        status = self._format_cpu_status("C64")
        # Clear line and write status
        _sys.stdout.write("\033[K" + status)

        # Add drive status line if drive is attached
        drive_status = self._format_drive_status()
        if drive_status:
            _sys.stdout.write(f"\n\033[K" + drive_status)

        # Clear dirty flags after rendering
        self.dirty_tracker.clear()

    def _render_pygame(self) -> None:
        """Render C64 screen to pygame window with dirty region optimization."""
        if not self.pygame_available or self.pygame_screen is None:
            return

        try:
            import pygame

            # Check if we've entered BASIC ROM (for conditional logging)
            self._check_pc_region()

            # Handle pygame events (window close, keyboard, mouse, etc.)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise errors.QuitRequestError("Window closed")
                elif event.type == pygame.KEYDOWN:
                    if DEBUG_KEYBOARD:
                        log.info(f"*** PYGAME KEYDOWN EVENT: key={event.key} ***")
                    self._handle_pygame_keyboard(event, pygame)
                elif event.type == pygame.KEYUP:
                    self._handle_pygame_keyboard(event, pygame)
                elif event.type == pygame.MOUSEMOTION:
                    # Update mouse/paddle/lightpen position
                    if self._mouse_enabled:
                        # Mouse mode: relative motion (like 1351 proportional mouse)
                        self.update_mouse_motion(event.rel[0], event.rel[1])
                    elif self._paddle_enabled:
                        # Paddle mode: absolute position scaled to window
                        # Mouse X → Paddle 1 (POTX), Mouse Y → Paddle 2 (POTY)
                        window_size = self.pygame_screen.get_size()
                        self.update_paddle_position(event.pos[0], event.pos[1], window_size[0], window_size[1])
                    elif self._lightpen_enabled:
                        # Lightpen mode: absolute position to VIC registers
                        window_size = self.pygame_screen.get_size()
                        self.update_lightpen_position(event.pos[0], event.pos[1], window_size[0], window_size[1])
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Mouse/paddle/lightpen button pressed
                    if self._mouse_enabled:
                        self.set_mouse_button(event.button, True)
                    elif self._paddle_enabled:
                        # Left click → Paddle 1 fire, Right click → Paddle 2 fire
                        self.set_paddle_button(event.button, True)
                    elif self._lightpen_enabled:
                        self.set_lightpen_button(event.button, True)
                elif event.type == pygame.MOUSEBUTTONUP:
                    # Mouse/paddle/lightpen button released
                    if self._mouse_enabled:
                        self.set_mouse_button(event.button, False)
                    elif self._paddle_enabled:
                        self.set_paddle_button(event.button, False)
                    elif self._lightpen_enabled:
                        self.set_lightpen_button(event.button, False)

            # Check if VIC has a new frame ready (VBlank)
            # VIC takes the snapshot at the exact moment of VBlank for consistency
            new_frame = self.vic.frame_complete.is_set()
            if new_frame:
                self.vic.frame_complete.clear()
                self._frame_count = getattr(self, '_frame_count', 0) + 1
                if self._frame_count <= 5 or self._frame_count % 50 == 0:
                    log.info(f"*** PYGAME: Caught frame {self._frame_count}, cycles={self.cpu.cycles_executed} ***")

            # Create memory wrappers for VIC
            # Use VIC's snapshot (taken at VBlank) if available, otherwise live RAM
            # The snapshot is only 16KB (one VIC bank), so we need to adjust addresses
            class RAMWrapper:
                def __init__(wrapper_self, snapshot, snapshot_bank, live_ram):
                    wrapper_self.snapshot = snapshot
                    wrapper_self.snapshot_bank = snapshot_bank
                    wrapper_self.live_ram = live_ram

                def __getitem__(wrapper_self, index):
                    if wrapper_self.snapshot is not None:
                        # Convert absolute address to bank-relative offset
                        # The snapshot covers snapshot_bank to snapshot_bank + 16KB
                        relative_index = index - wrapper_self.snapshot_bank
                        if 0 <= relative_index < len(wrapper_self.snapshot):
                            return wrapper_self.snapshot[relative_index]
                        # Address outside snapshot bank - fall through to live RAM
                    return int(wrapper_self.live_ram[index])

            class ColorRAMWrapper:
                def __init__(wrapper_self, snapshot, live_color):
                    wrapper_self.snapshot = snapshot
                    wrapper_self.live_color = live_color

                def __getitem__(wrapper_self, index):
                    if wrapper_self.snapshot is not None:
                        return wrapper_self.snapshot[index] & 0x0F
                    return wrapper_self.live_color[index] & 0x0F

            # Initialize glyph cache if needed
            if not hasattr(self, '_glyph_cache'):
                self._glyph_cache = {}

            vic = self.vic
            ram_snapshot = vic.ram_snapshot
            ram_snapshot_bank = vic.ram_snapshot_bank
            color_snapshot = vic.color_snapshot

            def read_ram(addr):
                if ram_snapshot is not None:
                    rel = addr - ram_snapshot_bank
                    if 0 <= rel < len(ram_snapshot):
                        return ram_snapshot[rel]
                return int(self.cpu.ram[addr])

            def read_color(idx):
                if color_snapshot is not None:
                    return color_snapshot[idx] & 0x0F
                return self.memory.ram_color[idx] & 0x0F

            surface = self.pygame_surface

            # --- Display-side rendering ---
            border_color = vic.regs[0x20] & 0x0F
            surface.fill(COLORS[border_color])

            vic_bank = vic.get_vic_bank()
            mem_control = vic.regs[0x18]
            screen_base = vic_bank + ((mem_control & 0xF0) >> 4) * 0x0400
            char_bank_offset = ((mem_control & 0x0E) >> 1) * 0x0800

            ecm = bool(vic.regs[0x11] & 0x40)
            bmm = bool(vic.regs[0x11] & 0x20)
            den = bool(vic.regs[0x11] & 0x10)
            mcm = bool(vic.regs[0x16] & 0x10)
            bg_color = vic.regs[0x21] & 0x0F

            hscroll = vic.regs[0x16] & 0x07
            vscroll = vic.regs[0x11] & 0x07
            x_origin = vic.border_left - hscroll
            y_origin = vic.border_top - vscroll

            if den and not bmm and not ecm and not mcm:
                # Standard text mode - cached glyph rendering
                char_rom = vic.char_rom
                for row in range(25):
                    for col in range(40):
                        cell_addr = screen_base + row * 40 + col
                        char_code = read_ram(cell_addr)
                        color = read_color(row * 40 + col)

                        reverse = bool(char_code & 0x80)
                        char_code &= 0x7F

                        glyph_addr = (char_code * 8) + char_bank_offset
                        glyph_addr &= 0x0FFF
                        glyph = char_rom[glyph_addr : glyph_addr + 8]

                        if reverse:
                            fg, bg = bg_color, color
                        else:
                            fg, bg = color, bg_color

                        cache_key = (tuple(glyph), fg, bg)
                        if cache_key not in self._glyph_cache:
                            glyph_surf = pygame.Surface((8, 8))
                            fg_rgb = COLORS[fg]
                            bg_rgb = COLORS[bg]
                            for y in range(8):
                                line = glyph[y]
                                for x in range(8):
                                    bit = (line >> (7 - x)) & 0x01
                                    glyph_surf.set_at((x, y), fg_rgb if bit else bg_rgb)
                            self._glyph_cache[cache_key] = glyph_surf

                        base_x = x_origin + col * 8
                        base_y = y_origin + row * 8
                        surface.blit(self._glyph_cache[cache_key], (base_x, base_y))
            elif den:
                # Other modes - fall back to VIC for now
                ram_wrapper = RAMWrapper(ram_snapshot, ram_snapshot_bank, self.cpu.ram)
                color_wrapper = ColorRAMWrapper(color_snapshot, self.memory.ram_color)
                vic.render_frame(surface, ram_wrapper, color_wrapper)

            # Scale and blit to screen
            scaled_surface = pygame.transform.scale(
                surface,
                (vic.total_width * self.scale, vic.total_height * self.scale)
            )
            self.pygame_screen.blit(scaled_surface, (0, 0))
            pygame.display.flip()

            # Update window title with speed stats (rate-limited to once per second)
            self._update_pygame_title(pygame)

            # Also render terminal repl output (screen with colors)
            # Force full redraw since pygame already handled the dirty tracking
            # DO NOT REMOVE - useful for debugging pygame mode via terminal
            self.dirty_tracker.force_redraw()
            self._render_terminal_repl()

        except Exception as e:
            log.error(f"Error rendering pygame display: {e}")

    def _render_pygame_only(self) -> None:
        """Render C64 screen to pygame window.

        All pygame rendering happens here in the display loop, not in the VIC core.
        Uses glyph caching for fast text mode rendering.
        """
        if not self.pygame_available or self.pygame_screen is None:
            return

        try:
            import pygame
            import time as _time

            render_start = _time.perf_counter()

            # Check if VIC has a new frame ready (VBlank)
            new_frame = self.vic.frame_complete.is_set()
            if new_frame:
                self.vic.frame_complete.clear()
                self._frame_count = getattr(self, '_frame_count', 0) + 1

            # Initialize glyph cache if needed
            if not hasattr(self, '_glyph_cache'):
                self._glyph_cache = {}

            # Get RAM snapshot or live RAM
            vic = self.vic
            ram_snapshot = vic.ram_snapshot
            ram_snapshot_bank = vic.ram_snapshot_bank
            color_snapshot = vic.color_snapshot

            # Helper to read RAM
            def read_ram(addr):
                if ram_snapshot is not None:
                    rel = addr - ram_snapshot_bank
                    if 0 <= rel < len(ram_snapshot):
                        return ram_snapshot[rel]
                return int(self.cpu.ram[addr])

            def read_color(idx):
                if color_snapshot is not None:
                    return color_snapshot[idx] & 0x0F
                return self.memory.ram_color[idx] & 0x0F

            surface = self.pygame_surface

            # --- Render frame (display-side, no VIC pygame code) ---

            # Border colour
            border_color = vic.regs[0x20] & 0x0F
            surface.fill(COLORS[border_color])

            # Get VIC bank from CIA2
            vic_bank = vic.get_vic_bank()

            # Decode $D018
            mem_control = vic.regs[0x18]
            screen_base = vic_bank + ((mem_control & 0xF0) >> 4) * 0x0400
            char_bank_offset = ((mem_control & 0x0E) >> 1) * 0x0800

            # Mode flags
            ecm = bool(vic.regs[0x11] & 0x40)
            bmm = bool(vic.regs[0x11] & 0x20)
            den = bool(vic.regs[0x11] & 0x10)
            mcm = bool(vic.regs[0x16] & 0x10)

            bg_color = vic.regs[0x21] & 0x0F

            hscroll = vic.regs[0x16] & 0x07
            vscroll = vic.regs[0x11] & 0x07
            x_origin = vic.border_left - hscroll
            y_origin = vic.border_top - vscroll

            if den and not bmm and not ecm and not mcm:
                # Standard text mode - use cached glyph rendering
                char_rom = vic.char_rom

                for row in range(25):
                    for col in range(40):
                        cell_addr = screen_base + row * 40 + col
                        char_code = read_ram(cell_addr)

                        color = read_color(row * 40 + col)

                        reverse = bool(char_code & 0x80)
                        char_code &= 0x7F

                        glyph_addr = (char_code * 8) + char_bank_offset
                        glyph_addr &= 0x0FFF
                        glyph = char_rom[glyph_addr : glyph_addr + 8]

                        if reverse:
                            fg, bg = bg_color, color
                        else:
                            fg, bg = color, bg_color

                        # Cache lookup
                        cache_key = (tuple(glyph), fg, bg)
                        if cache_key not in self._glyph_cache:
                            # Render glyph to cache
                            glyph_surf = pygame.Surface((8, 8))
                            fg_rgb = COLORS[fg]
                            bg_rgb = COLORS[bg]
                            for y in range(8):
                                line = glyph[y]
                                for x in range(8):
                                    bit = (line >> (7 - x)) & 0x01
                                    glyph_surf.set_at((x, y), fg_rgb if bit else bg_rgb)
                            self._glyph_cache[cache_key] = glyph_surf

                        # Blit cached glyph
                        base_x = x_origin + col * 8
                        base_y = y_origin + row * 8
                        surface.blit(self._glyph_cache[cache_key], (base_x, base_y))

            elif den:
                # Other modes - fall back to VIC renderer for now
                # TODO: Move bitmap/multicolor/ECM rendering here too
                class RAMWrapper:
                    def __getitem__(wrapper_self, index):
                        return read_ram(index)

                class ColorWrapper:
                    def __getitem__(wrapper_self, index):
                        return read_color(index)

                vic.render_frame(surface, RAMWrapper(), ColorWrapper())

            # Scale and blit to screen
            scaled_surface = pygame.transform.scale(
                surface,
                (vic.total_width * self.scale, vic.total_height * self.scale)
            )
            self.pygame_screen.blit(scaled_surface, (0, 0))
            pygame.display.flip()

            # Log render time periodically
            render_time = _time.perf_counter() - render_start
            if self._frame_count <= 5 or self._frame_count % 60 == 0:
                cache_size = len(self._glyph_cache)
                log.critical(
                    f"*** RENDER: {render_time*1000:.1f}ms "
                    f"(frame {self._frame_count}, cache={cache_size}) ***"
                )

        except Exception as e:
            log.error(f"Error rendering pygame display: {e}")

    def _pump_pygame_events(self) -> None:
        """Process pygame events without rendering.

        Called when the frame_complete wait times out to keep the UI
        responsive (handle window close, keyboard input, mouse input, etc.).
        """
        if not self.pygame_available or self.pygame_screen is None:
            return

        try:
            import pygame

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise errors.QuitRequestError("Window closed")
                elif event.type == pygame.KEYDOWN:
                    if DEBUG_KEYBOARD:
                        log.info(f"*** PYGAME KEYDOWN EVENT: key={event.key} ***")
                    self._handle_pygame_keyboard(event, pygame)
                elif event.type == pygame.KEYUP:
                    self._handle_pygame_keyboard(event, pygame)
                elif event.type == pygame.MOUSEMOTION:
                    # Update mouse/paddle/lightpen position
                    if self._mouse_enabled:
                        # Mouse mode: relative motion (like 1351 proportional mouse)
                        self.update_mouse_motion(event.rel[0], event.rel[1])
                    elif self._paddle_enabled:
                        # Paddle mode: absolute position scaled to window
                        # Mouse X → Paddle 1 (POTX), Mouse Y → Paddle 2 (POTY)
                        window_size = self.pygame_screen.get_size()
                        self.update_paddle_position(event.pos[0], event.pos[1], window_size[0], window_size[1])
                    elif self._lightpen_enabled:
                        # Lightpen mode: absolute position to VIC registers
                        window_size = self.pygame_screen.get_size()
                        self.update_lightpen_position(event.pos[0], event.pos[1], window_size[0], window_size[1])
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Mouse/paddle/lightpen button pressed
                    if self._mouse_enabled:
                        self.set_mouse_button(event.button, True)
                    elif self._paddle_enabled:
                        # Left click → Paddle 1 fire, Right click → Paddle 2 fire
                        self.set_paddle_button(event.button, True)
                    elif self._lightpen_enabled:
                        self.set_lightpen_button(event.button, True)
                elif event.type == pygame.MOUSEBUTTONUP:
                    # Mouse/paddle/lightpen button released
                    if self._mouse_enabled:
                        self.set_mouse_button(event.button, False)
                    elif self._paddle_enabled:
                        self.set_paddle_button(event.button, False)
                    elif self._lightpen_enabled:
                        self.set_lightpen_button(event.button, False)

        except errors.QuitRequestError:
            raise  # Re-raise quit request to propagate up
        except Exception as e:
            log.error(f"Error pumping pygame events: {e}")

    # ASCII to C64 keyboard matrix mapping
    # Maps ASCII characters to (row, col) positions in the C64 keyboard matrix
    # Some characters require SHIFT to be pressed
    ASCII_TO_MATRIX = {
        # Letters (unshifted = uppercase on C64 in default mode)
        'A': (1, 2), 'B': (3, 4), 'C': (2, 4), 'D': (2, 2), 'E': (1, 6),
        'F': (2, 5), 'G': (3, 2), 'H': (3, 5), 'I': (4, 1), 'J': (4, 2),
        'K': (4, 5), 'L': (5, 2), 'M': (4, 4), 'N': (4, 7), 'O': (4, 6),
        'P': (5, 1), 'Q': (7, 6), 'R': (2, 1), 'S': (1, 5), 'T': (2, 6),
        'U': (3, 6), 'V': (3, 7), 'W': (1, 1), 'X': (2, 7), 'Y': (3, 1),
        'Z': (1, 4),
        # Lowercase (same matrix position, C64 handles shift mode internally)
        'a': (1, 2), 'b': (3, 4), 'c': (2, 4), 'd': (2, 2), 'e': (1, 6),
        'f': (2, 5), 'g': (3, 2), 'h': (3, 5), 'i': (4, 1), 'j': (4, 2),
        'k': (4, 5), 'l': (5, 2), 'm': (4, 4), 'n': (4, 7), 'o': (4, 6),
        'p': (5, 1), 'q': (7, 6), 'r': (2, 1), 's': (1, 5), 't': (2, 6),
        'u': (3, 6), 'v': (3, 7), 'w': (1, 1), 'x': (2, 7), 'y': (3, 1),
        'z': (1, 4),
        # Digits
        '0': (4, 3), '1': (7, 0), '2': (7, 3), '3': (1, 0), '4': (1, 3),
        '5': (2, 0), '6': (2, 3), '7': (3, 0), '8': (3, 3), '9': (4, 0),
        # Special characters
        ' ': (7, 4),      # SPACE
        '\n': (0, 1),     # RETURN
        '\r': (0, 1),     # RETURN
        '+': (5, 0),
        '-': (5, 3),
        '*': (6, 1),
        '/': (6, 7),
        '=': (6, 5),
        '.': (5, 4),
        ',': (5, 7),
        ':': (5, 5),
        ';': (6, 2),
        '@': (5, 6),
        '#': None,        # Requires SHIFT+3 (handled specially)
        '$': None,        # Requires SHIFT+4 (handled specially)
        '%': None,        # Requires SHIFT+5 (handled specially)
        '(': None,        # Requires SHIFT+8 (handled specially)
        ')': None,        # Requires SHIFT+9 (handled specially)
        '"': None,        # Requires SHIFT+2 (handled specially)
        '!': None,        # Requires SHIFT+1 (handled specially)
        '?': None,        # Requires SHIFT+/ (handled specially)
        '<': None,        # Requires SHIFT+, (handled specially)
        '>': None,        # Requires SHIFT+. (handled specially)
    }

    # Characters that require SHIFT: (shift_row, shift_col, key_row, key_col)
    ASCII_SHIFTED = {
        '!': (1, 7, 7, 0),   # SHIFT + 1
        '"': (1, 7, 7, 3),   # SHIFT + 2
        '#': (1, 7, 1, 0),   # SHIFT + 3
        '$': (1, 7, 1, 3),   # SHIFT + 4
        '%': (1, 7, 2, 0),   # SHIFT + 5
        '&': (1, 7, 2, 3),   # SHIFT + 6
        "'": (1, 7, 7, 3),   # SHIFT + 2 - produces " (double quote) for BASIC strings
        '(': (1, 7, 3, 3),   # SHIFT + 8
        ')': (1, 7, 4, 0),   # SHIFT + 9
        '?': (1, 7, 6, 7),   # SHIFT + /
        '<': (1, 7, 5, 7),   # SHIFT + ,
        '>': (1, 7, 5, 4),   # SHIFT + .
    }
