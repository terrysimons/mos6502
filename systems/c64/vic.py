#!/usr/bin/env python3
"""VIC-II (Video Interface Chip) emulation for C64.

This module contains:
- VideoTiming: Timing parameters for different VIC-II chip variants
- ScreenDirtyTracker: Tracks which screen cells need redrawing
- C64VIC: The main VIC-II chip emulation class
- Color constants and ANSI conversion utilities
"""


from mos6502.compat import logging
# Multiprocessing is optional - only needed for cross-process frame sync
try:
    import multiprocessing
    _multiprocessing_available = True
except ImportError:
    _multiprocessing_available = False

# Simple Event class for when multiprocessing is not available
class _SimpleEvent:
    """Simple Event replacement when multiprocessing is not available."""
    def __init__(self):
        self._flag = False
    def set(self):
        self._flag = True
    def clear(self):
        self._flag = False
    def is_set(self):
        return self._flag
    def wait(self, timeout=None):
        return self._flag

def _create_event():
    """Create an Event - uses multiprocessing if available, otherwise simple."""
    if _multiprocessing_available:
        return multiprocessing.Event()
    return _SimpleEvent()

from mos6502.compat import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from c64.cia2 import CIA2
    from mos6502.core import MOS6502CPU

log = logging.getLogger("c64")


# =============================================================================
# Video Timing Constants
# =============================================================================

# VideoTiming - try to use NamedTuple, fall back to collections.namedtuple for MicroPython
try:
    # CPython - use class syntax with NamedTuple
    class VideoTiming(NamedTuple):
        """Video system timing parameters for VIC-II chip variants.

        VIC-II Chip Variants:
            6569 (PAL)       - Europe, Australia (312 lines, 63 cycles/line, ~50Hz)
            6567R8 (NTSC)    - North America 1984+ (263 lines, 65 cycles/line, ~60Hz)
            6567R56A (NTSC)  - North America 1982-1984 (262 lines, 64 cycles/line, ~60Hz)

        Access standard timing configurations via class attributes:
            VideoTiming.VIC_6569     - PAL chip
            VideoTiming.VIC_6567R8   - New NTSC chip (default for NTSC)
            VideoTiming.VIC_6567R56A - Old NTSC chip
            VideoTiming.PAL          - Alias for VIC_6569
            VideoTiming.NTSC         - Alias for VIC_6567R8
        """
        chip_name: str          # VIC-II chip identifier (6569, 6567R8, 6567R56A)
        cpu_freq: int           # CPU frequency in Hz
        refresh_hz: float       # Screen refresh rate in Hz
        cycles_per_frame: int   # CPU cycles per video frame
        cycles_per_line: int    # CPU cycles per raster line
        raster_lines: int       # Total raster lines per frame
        render_interval: float  # Seconds between frame renders (1/refresh_hz)
    # Test that it works (will fail on MicroPython)
    _test = VideoTiming(chip_name="test", cpu_freq=0, refresh_hz=0.0,
                        cycles_per_frame=0, cycles_per_line=0, raster_lines=0,
                        render_interval=0.0)
    del _test
except (TypeError, AttributeError):
    # MicroPython - use collections.namedtuple
    from collections import namedtuple
    VideoTiming = namedtuple('VideoTiming', [
        'chip_name', 'cpu_freq', 'refresh_hz', 'cycles_per_frame',
        'cycles_per_line', 'raster_lines', 'render_interval'
    ])


# VIC-II 6569 (PAL) - Europe, Australia
# More compatible with demos/games, slightly slower CPU
VIC_6569 = VideoTiming(
    chip_name="6569",
    cpu_freq=985248,           # ~0.985 MHz
    refresh_hz=50.125,         # ~50 Hz
    cycles_per_frame=19656,    # 312 lines × 63 cycles
    cycles_per_line=63,
    raster_lines=312,
    render_interval=1.0 / 50.125,
)

# VIC-II 6567R8 (NTSC) - North America, Japan (1984 onwards)
# "New" NTSC chip, most common in later C64s
VIC_6567R8 = VideoTiming(
    chip_name="6567R8",
    cpu_freq=1022727,          # ~1.023 MHz
    refresh_hz=59.826,         # ~60 Hz
    cycles_per_frame=17095,    # 263 lines × 65 cycles
    cycles_per_line=65,
    raster_lines=263,
    render_interval=1.0 / 59.826,
)

# VIC-II 6567R56A (NTSC) - North America (1982-1984)
# "Old" NTSC chip, found in early C64s
VIC_6567R56A = VideoTiming(
    chip_name="6567R56A",
    cpu_freq=1022727,          # ~1.023 MHz
    refresh_hz=59.826,         # ~60 Hz (slightly different in reality)
    cycles_per_frame=16768,    # 262 lines × 64 cycles
    cycles_per_line=64,
    raster_lines=262,
    render_interval=1.0 / 59.826,
)

# Module-level aliases
PAL = VIC_6569
NTSC = VIC_6567R8  # Default to new NTSC chip

# Try to set class attributes for backwards compatibility (may fail on MicroPython)
try:
    VideoTiming.VIC_6569 = VIC_6569
    VideoTiming.VIC_6567R8 = VIC_6567R8
    VideoTiming.VIC_6567R56A = VIC_6567R56A
    VideoTiming.PAL = PAL
    VideoTiming.NTSC = NTSC
except (TypeError, AttributeError):
    pass  # MicroPython doesn't allow setting attributes on namedtuple


# =============================================================================
# Color Constants
# =============================================================================

# Colodore palette - the most accurate VIC-II color representation
# Based on Pepto's Colodore algorithm: https://www.pepto.de/projects/colorvic/
# Values from VICE emulator's colodore.vpl:
# https://github.com/libretro/vice-libretro/blob/master/vice/data/C64/colodore.vpl
COLORS = [
    (0x00, 0x00, 0x00),   # 0  Black
    (0xFF, 0xFF, 0xFF),   # 1  White
    (0x96, 0x28, 0x2E),   # 2  Red
    (0x5B, 0xD6, 0xCE),   # 3  Cyan
    (0x9F, 0x2D, 0xAD),   # 4  Purple
    (0x41, 0xB9, 0x36),   # 5  Green
    (0x27, 0x24, 0xC4),   # 6  Blue
    (0xEF, 0xF3, 0x47),   # 7  Yellow
    (0x9F, 0x48, 0x15),   # 8  Orange
    (0x5E, 0x35, 0x00),   # 9  Brown
    (0xDA, 0x5F, 0x66),   # 10 Light red
    (0x47, 0x47, 0x47),   # 11 Dark gray
    (0x78, 0x78, 0x78),   # 12 Medium gray
    (0x91, 0xFF, 0x84),   # 13 Light green
    (0x68, 0x64, 0xFF),   # 14 Light blue
    (0xAE, 0xAE, 0xAE),   # 15 Light gray
]

# ANSI true color (24-bit) escape sequences for exact C64 color matching
# Using 24-bit mode: \033[38;2;R;G;Bm for foreground, \033[48;2;R;G;Bm for background


def c64_to_ansi_fg(c64_color: int) -> str:
    """Convert C64 color to ANSI 24-bit true color foreground escape sequence."""
    r, g, b = COLORS[c64_color & 0x0F]
    return f"\033[38;2;{r};{g};{b}m"


def c64_to_ansi_bg(c64_color: int) -> str:
    """Convert C64 color to ANSI 24-bit true color background escape sequence."""
    r, g, b = COLORS[c64_color & 0x0F]
    return f"\033[48;2;{r};{g};{b}m"


ANSI_RESET = "\033[0m"


# =============================================================================
# Screen Dirty Tracker
# =============================================================================

class ScreenDirtyTracker:
    """Track which screen cells have changed since last render.

    Optimizes rendering by only updating cells that have been modified.
    Tracks both screen RAM ($0400-$07E7) and color RAM ($D800-$DBE7).
    Also tracks VIC register changes that affect global rendering.
    """

    SCREEN_RAM_START = 0x0400
    SCREEN_RAM_END = 0x07E7
    COLOR_RAM_START = 0xD800
    COLOR_RAM_END = 0xDBE7
    VIC_START = 0xD000
    VIC_END = 0xD02E

    SCREEN_COLS = 40
    SCREEN_ROWS = 25
    SCREEN_SIZE = SCREEN_COLS * SCREEN_ROWS  # 1000 cells

    def __init__(self):
        # Track dirty cells as a set of (row, col) tuples for fast lookup
        self._dirty_cells = set()
        # Track if any VIC registers changed (requires full redraw)
        self._vic_dirty = False
        # Track if color RAM changed
        self._color_dirty_cells = set()
        # Force full redraw on first frame
        self._force_full_redraw = True
        # Previous screen state for comparison (optional optimization)
        self._prev_screen = None
        self._prev_color = None

    def mark_screen_dirty(self, addr: int) -> None:
        """Mark a screen RAM address as dirty."""
        if self.SCREEN_RAM_START <= addr <= self.SCREEN_RAM_END:
            offset = addr - self.SCREEN_RAM_START
            row = offset // self.SCREEN_COLS
            col = offset % self.SCREEN_COLS
            self._dirty_cells.add((row, col))

    def mark_color_dirty(self, addr: int) -> None:
        """Mark a color RAM address as dirty."""
        if self.COLOR_RAM_START <= addr <= self.COLOR_RAM_END:
            offset = addr - self.COLOR_RAM_START
            if offset < self.SCREEN_SIZE:
                row = offset // self.SCREEN_COLS
                col = offset % self.SCREEN_COLS
                self._color_dirty_cells.add((row, col))

    def mark_vic_dirty(self) -> None:
        """Mark VIC registers as changed (forces full redraw)."""
        self._vic_dirty = True

    def mark_address_dirty(self, addr: int) -> None:
        """Mark any address as dirty (routes to appropriate tracker)."""
        if self.SCREEN_RAM_START <= addr <= self.SCREEN_RAM_END:
            self.mark_screen_dirty(addr)
        elif self.COLOR_RAM_START <= addr <= self.COLOR_RAM_END:
            self.mark_color_dirty(addr)
        elif self.VIC_START <= addr <= self.VIC_END:
            self.mark_vic_dirty()

    def needs_full_redraw(self) -> bool:
        """Check if a full screen redraw is needed."""
        return self._force_full_redraw or self._vic_dirty

    def get_dirty_cells(self) -> set:
        """Get all dirty cells (screen + color changes combined)."""
        return self._dirty_cells | self._color_dirty_cells

    def get_dirty_rows(self) -> set:
        """Get set of row numbers that have any dirty cells."""
        dirty = self.get_dirty_cells()
        return {row for row, col in dirty}

    def has_changes(self) -> bool:
        """Check if any changes need to be rendered."""
        return (self._force_full_redraw or
                self._vic_dirty or
                len(self._dirty_cells) > 0 or
                len(self._color_dirty_cells) > 0)

    def clear(self) -> None:
        """Clear all dirty flags after rendering."""
        self._dirty_cells.clear()
        self._color_dirty_cells.clear()
        self._vic_dirty = False
        self._force_full_redraw = False

    def force_redraw(self) -> None:
        """Force a full redraw on next render."""
        self._force_full_redraw = True


# =============================================================================
# VIC-II Chip Emulation
# =============================================================================

class C64VIC:
    """
    VIC-II video chip emulation.

    Supports:
    - 40×25 character text mode (standard and multicolor)
    - Bitmap modes (320x200 hires, 160x200 multicolor)
    - Extended background color mode
    - 8 hardware sprites with collision detection
    - Border and background colors
    - $D018 screen/character memory selection
    - $D011/$D016 fine scroll
    - Raster IRQ, sprite-sprite collision IRQ, sprite-background collision IRQ
    - Light pen registers
    """

    def __init__(self, char_rom, cpu: "MOS6502CPU", cia2: "CIA2" = None, video_timing: VideoTiming = None) -> None:
        self.log = logging.getLogger("c64.vic")
        self.regs = [0] * 0x40
        self.char_rom = char_rom
        self.cpu = cpu
        self.cia2 = cia2  # For VIC bank selection
        self.video_timing = video_timing if video_timing is not None else PAL

        # --- Power-on register defaults (C64 reset state-ish) -----------------
        # Sprite X positions ($D000-$D00F): all 0
        for i in range(16):
            self.regs[i] = 0x00

        # Sprite X MSB ($D010): all 0
        self.regs[0x10] = 0x00

        # $D011: Control register 1 (vertical scroll, display enable, 25-row mode)
        #  %00011011 = $1B
        self.regs[0x11] = 0x1B

        # $D012: raster low byte
        self.regs[0x12] = 0x00

        # Light pen registers ($D013-$D014)
        self.regs[0x13] = 0x00  # Light pen X
        self.regs[0x14] = 0x00  # Light pen Y

        # $D015: sprite enable (all off)
        self.regs[0x15] = 0x00

        # $D016: Control register 2 (horizontal scroll, 40-column mode)
        #  %00001000 = $08
        self.regs[0x16] = 0x08

        # $D017: sprite Y-expand (all off)
        self.regs[0x17] = 0x00

        # $D018: Memory control – start with screen at $0400, chars at $1000
        # Bits 4-7 = 0001 → 1 * $0400 = $0400 (screen RAM)
        # Bits 1-3 = 010  → 2 * $0800 = $1000 (character ROM offset)
        self.regs[0x18] = 0x14
        log.info(
            f"*** VIC INIT: Set $D018 = ${self.regs[0x18]:02X} "
            f"(screen=$0400, char=$1000) ***"
        )

        # $D019: IRQ flags – set bit 0 so KERNAL has something to clear
        self.irq_flags = 0x01

        # $D01A: IRQ enable mask
        self.irq_enabled = 0x00

        # $D01B: Sprite-to-background priority (0=sprite in front)
        self.regs[0x1B] = 0x00

        # $D01C: Sprite multicolor mode
        self.regs[0x1C] = 0x00

        # $D01D: Sprite X-expand
        self.regs[0x1D] = 0x00

        # $D01E: Sprite-sprite collision (read clears)
        self.sprite_sprite_collision = 0x00

        # $D01F: Sprite-background collision (read clears)
        self.sprite_bg_collision = 0x00

        # Colours
        # $D020: border colour – light blue (14)
        self.regs[0x20] = 0x0E
        # $D021: background colour 0 – blue (6)
        self.regs[0x21] = 0x06
        # $D022: background colour 1
        self.regs[0x22] = 0x00
        # $D023: background colour 2
        self.regs[0x23] = 0x00
        # $D024: background colour 3
        self.regs[0x24] = 0x00
        # $D025: sprite multicolor 0
        self.regs[0x25] = 0x00
        # $D026: sprite multicolor 1
        self.regs[0x26] = 0x00
        # $D027-$D02E: sprite colors
        for i in range(8):
            self.regs[0x27 + i] = 0x00

        # --- Geometry / timing -----------------------------------------------
        # Text area: 40×25 chars → 320×200 pixels
        self.text_width = 320
        self.text_height = 200

        # Choose a total frame large enough for borders; keep your 384×270
        self.total_width = 384
        self.total_height = 270

        # Center the text area within the total frame
        # This gives symmetric borders on all sides
        self.border_left = (self.total_width - self.text_width) // 2    # 32 pixels
        self.border_right = self.total_width - self.border_left - self.text_width  # 32 pixels
        self.border_top = (self.total_height - self.text_height) // 2   # 35 pixels
        self.border_bottom = self.total_height - self.border_top - self.text_height  # 35 pixels

        # Video timing from VIC-II chip variant
        # 6569 (PAL):     312 raster lines, 63 cycles/line, 19656 cycles/frame
        # 6567R8 (NTSC):  263 raster lines, 65 cycles/line, 17095 cycles/frame
        # 6567R56A (old): 262 raster lines, 64 cycles/line, 16768 cycles/frame
        self.raster_lines = self.video_timing.raster_lines
        self.cycles_per_line = self.video_timing.cycles_per_line
        self.cycles_per_frame = self.video_timing.cycles_per_frame

        # Current raster line
        self.current_raster = 0

        # Track last CPU cycle count to derive raster position
        self.last_cycle_count = 0

        # Track when the KERNAL has acknowledged the initial IRQ
        self.initialized = False

        # Light pen state
        self.light_pen_triggered = False

        # Frame-ready flag for render synchronization
        # VIC sets this when a frame completes (raster wraps to 0)
        # Pygame checks it, grabs a snapshot, and clears it
        # No blocking - VIC runs at full speed, pygame renders what it catches
        # Using Event for frame sync (multiprocessing.Event if available)
        self.frame_complete = _create_event()

        # RAM snapshots taken at VBlank for consistent rendering
        # Only the 16KB VIC bank is snapshotted (not full 64KB) for performance
        self.ram_snapshot = None
        self.ram_snapshot_bank = 0  # Base address of snapshotted bank
        self.color_snapshot = None
        # VIC register snapshot for consistent scroll/mode during render
        # Games like Pitfall change scroll mid-frame; we capture at VBlank
        self.regs_snapshot = None
        # VIC bank snapshot (from CIA2) - games may switch banks mid-frame
        self.vic_bank_snapshot = None
        self.c64_memory = None  # Set later via set_memory()

        self.log.info(
            "VIC-II %s initialized (%d lines, %d cycles/line, %d cycles/frame)",
            self.video_timing.chip_name,
            self.raster_lines,
            self.cycles_per_line,
            self.cycles_per_frame,
        )

    def set_cia2(self, cia2: "CIA2") -> None:
        """Set reference to CIA2 for VIC bank selection."""
        self.cia2 = cia2

    def set_memory(self, c64_memory) -> None:
        """Set reference to C64Memory for VBlank snapshots."""
        self.c64_memory = c64_memory

    def get_vic_bank(self) -> int:
        """Get the current VIC bank address from CIA2."""
        if self.cia2:
            return self.cia2.get_vic_bank()
        return 0x0000  # Default to bank 0

    # --------------------------------------------------------------------- IRQ /
    def update(self) -> None:
        """
        Update raster position based on CPU cycles and generate raster IRQ
        when the raster counter matches the compare register.
        """
        # Derive raster from total CPU cycles; we don't try to be sub-cycle accurate.
        total_lines = self.cpu.cycles_executed // self.cycles_per_line
        new_raster = total_lines % self.raster_lines

        if new_raster != self.current_raster:
            # Snapshot VIC registers at first visible line (~51 on PAL)
            # This captures scroll/mode values when the game has set them for display
            # Games like Pitfall change scroll during visible area, reset during border
            # Snapshotting at VBlank would catch inconsistent values
            first_visible_line = 51  # First line of display area on PAL/NTSC
            if self.current_raster < first_visible_line <= new_raster:
                # Crossed into visible area - snapshot registers now
                self.regs_snapshot = bytes(self.regs)
                self.vic_bank_snapshot = self.get_vic_bank()

            # Detect frame completion (VBlank) when raster wraps back to 0
            # This happens when new_raster < current_raster (wrapped around)
            if new_raster < self.current_raster:
                # Take RAM snapshot NOW while we're at VBlank
                # This ensures consistent frame data before CPU continues
                # Use snapshot_vic_bank() to bypass memory handler and avoid infinite recursion
                # Only snapshot the 16KB VIC bank that's currently visible
                if self.c64_memory:
                    vic_bank = self.get_vic_bank()
                    self.ram_snapshot = self.c64_memory.snapshot_vic_bank(vic_bank)
                    self.ram_snapshot_bank = vic_bank  # Remember bank offset for rendering
                    self.color_snapshot = bytes(self.c64_memory.ram_color)
                # Warn if frame_complete is still set (render thread falling behind)
                if self.frame_complete.is_set():
                    log.warning(
                        "VIC: frame_complete still set at VBlank - render thread falling behind"
                    )
                # Signal frame complete - pygame will use the snapshot
                self.frame_complete.set()
            # 9-bit raster compare value: low byte in $D012, bit 8 in $D011 bit 7
            compare = self.regs[0x12] | ((self.regs[0x11] & 0x80) << 1)

            if new_raster == compare:
                # Always set the raster IRQ flag when raster matches compare value
                # This flag is set regardless of whether IRQ is enabled
                # (The enable bit only controls whether an actual interrupt fires)
                # This is critical for PAL/NTSC detection which reads $D019
                self.irq_flags |= 0x01

                log.info(
                    "*** VIC RASTER MATCH: line %d == compare %d, irq_enabled=$%02X "
                    "(bit0=%s), irq_flags now=$%02X ***",
                    new_raster,
                    compare,
                    self.irq_enabled,
                    "set" if (self.irq_enabled & 0x01) else "clear",
                    self.irq_flags,
                )

                if self.irq_enabled & 0x01:
                    # Tell CPU an IRQ is pending
                    self.cpu.irq_pending = True
                    log.info(
                        "*** VIC TRIGGERING IRQ: raster line %d, "
                        "cpu.irq_pending=True, cycles=%d ***",
                        new_raster,
                        self.cpu.cycles_executed,
                    )
                    self.log.debug(
                        "VIC raster IRQ: line %d, setting cpu.irq_pending=True",
                        new_raster,
                    )

        self.current_raster = new_raster

    # ---------------------------------------------------------------- Register I/O /
    def read(self, addr) -> int:
        reg = addr & 0x3F

        # $D011: Control register 1 (bit 7 is raster bit 8)
        if reg == 0x11:
            # Bit 7 is raster line bit 8
            result = self.regs[0x11] & 0x7F
            if self.current_raster > 255:
                result |= 0x80
            return result

        # $D012: raster counter (low 8 bits)
        if reg == 0x12:
            self.update()
            return self.current_raster & 0xFF

        # $D018: handy debug decode
        if reg == 0x18:
            val = self.regs[reg]
            screen_addr = ((val & 0xF0) >> 4) * 0x0400
            char_offset = ((val & 0x0E) >> 1) * 0x0800
            log.info(
                "*** VIC $D018 READ: value=$%02X, screen=$%04X, char_offset=$%04X ***",
                val,
                screen_addr,
                char_offset,
            )

        # $D019: IRQ flags
        if reg == 0x19:
            flags = self.irq_flags & 0x0F
            if flags:
                flags |= 0x80  # bit 7 set if any IRQ occurred
            return flags

        # $D01E: Sprite-sprite collision (cleared on read)
        if reg == 0x1E:
            result = self.sprite_sprite_collision
            self.sprite_sprite_collision = 0x00
            return result

        # $D01F: Sprite-background collision (cleared on read)
        if reg == 0x1F:
            result = self.sprite_bg_collision
            self.sprite_bg_collision = 0x00
            return result

        return self.regs[reg]

    def write(self, addr, val) -> None:
        reg = addr & 0x3F
        self.regs[reg] = val & 0xFF

        # $D012: raster compare low byte
        if reg == 0x12:
            compare = val | ((self.regs[0x11] & 0x80) << 1)
            log.info(
                "*** VIC RASTER COMPARE: $D012 = $%02X, full compare value = %d ***",
                val,
                compare,
            )

        # $D011: control register (contains raster compare bit 8 as bit 7)
        if reg == 0x11:
            compare = self.regs[0x12] | ((val & 0x80) << 1)
            log.info(
                "*** VIC CONTROL: $D011 = $%02X, raster compare = %d ***",
                val,
                compare,
            )

        # $D018: memory control (screen + char memory)
        if reg == 0x18:
            screen_addr = ((val & 0xF0) >> 4) * 0x0400
            char_offset = ((val & 0x0E) >> 1) * 0x0800
            log.info(
                "*** VIC $D018 WRITE: value=$%02X, screen=$%04X, char_offset=$%04X ***",
                val,
                screen_addr,
                char_offset,
            )

        # $D019: IRQ flags — write 1 to clear corresponding bits
        if reg == 0x19:
            was_set = self.irq_flags & 0x0F
            self.irq_flags &= ~(val & 0x0F)

            if (self.irq_flags & 0x0F) == 0:
                # All IRQ sources cleared, let CPU drop its pending flag
                self.cpu.irq_pending = False
                self.log.debug("VIC IRQ acknowledged, cpu.irq_pending cleared")

            # Detect completion of KERNAL's initial IRQ sequence
            if not self.initialized and was_set and (self.irq_flags & 0x0F) == 0:
                self.initialized = True
                self.log.info("VIC-II initialization complete (IRQ acknowledged)")

        # $D01A: IRQ enable mask
        if reg == 0x1A:
            self.irq_enabled = val & 0x0F
            log.info(
                "*** VIC IRQ ENABLE: $D01A = $%02X, irq_enabled=$%02X, "
                "raster IRQ %s ***",
                val,
                self.irq_enabled,
                "ENABLED" if (self.irq_enabled & 0x01) else "DISABLED",
            )

    # ---------------------------------------------------------------- Rendering /
    def _get_char_data(self, ram, vic_bank, char_offset, char_code):
        """Get 8-byte character glyph data from char ROM or RAM.

        The VIC-II can see character ROM at offset $1000-$1FFF within banks 0 and 2:
        - Bank 0 ($0000): Char ROM at VIC address $1000-$1FFF (CPU $1000-$1FFF)
        - Bank 1 ($4000): No char ROM - always RAM
        - Bank 2 ($8000): Char ROM at VIC address $1000-$1FFF (CPU $9000-$9FFF)
        - Bank 3 ($C000): No char ROM - always RAM

        Args:
            ram: RAM array
            vic_bank: VIC bank base address ($0000, $4000, $8000, or $C000)
            char_offset: Character base offset within VIC bank (from D018 bits 1-3)
            char_code: Character code (0-255)

        Returns:
            8-byte character glyph data
        """
        glyph_offset = char_code * 8

        # Check if char ROM is visible at this address
        # Char ROM appears at offset $1000-$1FFF within banks 0 and 2 only
        char_addr_in_bank = char_offset + glyph_offset
        use_char_rom = False

        if vic_bank == 0x0000 or vic_bank == 0x8000:
            # Banks 0 and 2 have char ROM at $1000-$1FFF
            if 0x1000 <= char_addr_in_bank < 0x2000:
                use_char_rom = True

        if use_char_rom:
            # Read from character ROM
            rom_addr = (char_addr_in_bank - 0x1000) & 0x0FFF
            return self.char_rom[rom_addr : rom_addr + 8]
        else:
            # Read from RAM
            ram_addr = vic_bank + char_addr_in_bank
            return bytes(ram[ram_addr + i] for i in range(8))

    def render_frame(self, surface, ram, color_ram) -> None:
        """
        Render a full frame into the given pygame surface.

        Supports:
        - Standard character mode (40x25)
        - Multicolor character mode
        - Extended background color mode
        - Standard bitmap mode (320x200)
        - Multicolor bitmap mode (160x200)
        - 8 hardware sprites with priority and collision
        """
        # Use snapshotted registers if available (captured at VBlank)
        # This prevents "bouncing" in games like Pitfall that change scroll mid-frame
        regs = self.regs_snapshot if self.regs_snapshot is not None else self.regs

        # Border colour
        border_color = regs[0x20] & 0x0F
        surface.fill(COLORS[border_color])

        # Get VIC bank - use snapshot if available, otherwise read live from CIA2
        vic_bank = self.vic_bank_snapshot if self.vic_bank_snapshot is not None else self.get_vic_bank()

        # Decode $D018: video matrix base + character/bitmap offset
        mem_control = regs[0x18]

        # Bits 4-7: screen base in 1 KB blocks (within VIC bank)
        screen_base = vic_bank + ((mem_control & 0xF0) >> 4) * 0x0400

        # Bits 1-3: char/bitmap base in 2 KB blocks (within VIC bank)
        char_bank_offset = ((mem_control & 0x0E) >> 1) * 0x0800

        # Mode flags from $D011 and $D016
        ecm = bool(regs[0x11] & 0x40)  # Extended Color Mode
        bmm = bool(regs[0x11] & 0x20)  # Bitmap Mode
        den = bool(regs[0x11] & 0x10)  # Display Enable
        mcm = bool(regs[0x16] & 0x10)  # Multicolor Mode

        # Background colours
        bg_colors = [
            regs[0x21] & 0x0F,
            regs[0x22] & 0x0F,
            regs[0x23] & 0x0F,
            regs[0x24] & 0x0F,
        ]

        # Fine scroll values
        hscroll = regs[0x16] & 0x07
        vscroll = regs[0x11] & 0x07

        x_origin = self.border_left - hscroll
        y_origin = self.border_top - vscroll

        if not den:
            # Display disabled - just show border
            return

        if bmm:
            # Bitmap mode
            bitmap_base = vic_bank + char_bank_offset
            if mcm:
                self._render_multicolor_bitmap(surface, ram, color_ram, bitmap_base, screen_base, bg_colors[0], x_origin, y_origin)
            else:
                self._render_hires_bitmap(surface, ram, bitmap_base, screen_base, x_origin, y_origin)
        elif ecm:
            # Extended background color mode
            self._render_ecm_text(surface, ram, color_ram, vic_bank, char_bank_offset, screen_base, bg_colors, x_origin, y_origin)
        elif mcm:
            # Multicolor text mode
            self._render_multicolor_text(surface, ram, color_ram, vic_bank, char_bank_offset, screen_base, bg_colors, x_origin, y_origin)
        else:
            # Standard text mode
            self._render_standard_text(surface, ram, color_ram, vic_bank, char_bank_offset, screen_base, bg_colors[0], x_origin, y_origin)

        # Render sprites on top
        self._render_sprites(surface, ram, vic_bank, screen_base, x_origin, y_origin, regs)

    def _render_standard_text(self, surface, ram, color_ram, vic_bank, char_offset, screen_base, bg_color, x_origin, y_origin):
        """Render standard 40x25 text mode."""
        for row in range(25):
            for col in range(40):
                cell_addr = screen_base + row * 40 + col
                char_code = ram[cell_addr]

                color_offset = row * 40 + col
                color = color_ram[color_offset] & 0x0F

                # Reverse video if bit 7 set
                reverse = char_code & 0x80
                char_code &= 0x7F

                # Fetch 8×8 glyph from char ROM or RAM
                glyph = self._get_char_data(ram, vic_bank, char_offset, char_code)

                base_x = x_origin + col * 8
                base_y = y_origin + row * 8

                for y in range(8):
                    line = glyph[y]
                    for x in range(8):
                        bit = (line >> (7 - x)) & 0x01

                        if reverse:
                            fg = COLORS[bg_color]
                            bg = COLORS[color]
                        else:
                            fg = COLORS[color]
                            bg = COLORS[bg_color]

                        surface.set_at((base_x + x, base_y + y), fg if bit else bg)

    def _render_multicolor_text(self, surface, ram, color_ram, vic_bank, char_offset, screen_base, bg_colors, x_origin, y_origin):
        """Render multicolor text mode (MCM=1, BMM=0, ECM=0)."""
        for row in range(25):
            for col in range(40):
                cell_addr = screen_base + row * 40 + col
                char_code = ram[cell_addr]

                color_offset = row * 40 + col
                char_color = color_ram[color_offset] & 0x0F

                # If color bit 3 is set, use multicolor mode for this cell
                use_multicolor = char_color & 0x08

                # Fetch 8×8 glyph from char ROM or RAM
                glyph = self._get_char_data(ram, vic_bank, char_offset, char_code)

                base_x = x_origin + col * 8
                base_y = y_origin + row * 8

                for y in range(8):
                    line = glyph[y]
                    if use_multicolor:
                        # Multicolor: 4 double-width pixels
                        for x in range(4):
                            bits = (line >> (6 - x * 2)) & 0x03
                            if bits == 0:
                                c = COLORS[bg_colors[0]]
                            elif bits == 1:
                                c = COLORS[bg_colors[1]]
                            elif bits == 2:
                                c = COLORS[bg_colors[2]]
                            else:
                                c = COLORS[char_color & 0x07]
                            surface.set_at((base_x + x * 2, base_y + y), c)
                            surface.set_at((base_x + x * 2 + 1, base_y + y), c)
                    else:
                        # Standard: 8 single-width pixels
                        for x in range(8):
                            bit = (line >> (7 - x)) & 0x01
                            c = COLORS[char_color] if bit else COLORS[bg_colors[0]]
                            surface.set_at((base_x + x, base_y + y), c)

    def _render_ecm_text(self, surface, ram, color_ram, vic_bank, char_offset, screen_base, bg_colors, x_origin, y_origin):
        """Render extended background color mode (ECM=1, BMM=0, MCM=0)."""
        for row in range(25):
            for col in range(40):
                cell_addr = screen_base + row * 40 + col
                char_code = ram[cell_addr]

                color_offset = row * 40 + col
                char_color = color_ram[color_offset] & 0x0F

                # Bits 6-7 select background color
                bg_select = (char_code >> 6) & 0x03
                char_code &= 0x3F  # Only 64 characters available

                # Fetch 8×8 glyph from char ROM or RAM
                glyph = self._get_char_data(ram, vic_bank, char_offset, char_code)

                base_x = x_origin + col * 8
                base_y = y_origin + row * 8

                for y in range(8):
                    line = glyph[y]
                    for x in range(8):
                        bit = (line >> (7 - x)) & 0x01
                        c = COLORS[char_color] if bit else COLORS[bg_colors[bg_select]]
                        surface.set_at((base_x + x, base_y + y), c)

    def _render_hires_bitmap(self, surface, ram, bitmap_base, screen_base, x_origin, y_origin):
        """Render standard hires bitmap mode (320x200, BMM=1, MCM=0)."""
        for char_row in range(25):
            for char_col in range(40):
                # Get colors from screen RAM
                cell_addr = screen_base + char_row * 40 + char_col
                color_byte = ram[cell_addr]
                fg_color = (color_byte >> 4) & 0x0F
                bg_color = color_byte & 0x0F

                # Get 8 bytes of bitmap data
                bitmap_addr = bitmap_base + char_row * 320 + char_col * 8

                base_x = x_origin + char_col * 8
                base_y = y_origin + char_row * 8

                for y in range(8):
                    byte_val = ram[bitmap_addr + y]
                    for x in range(8):
                        bit = (byte_val >> (7 - x)) & 0x01
                        c = COLORS[fg_color] if bit else COLORS[bg_color]
                        surface.set_at((base_x + x, base_y + y), c)

    def _render_multicolor_bitmap(self, surface, ram, color_ram, bitmap_base, screen_base, bg_color, x_origin, y_origin):
        """Render multicolor bitmap mode (160x200, BMM=1, MCM=1)."""
        for char_row in range(25):
            for char_col in range(40):
                # Get colors
                cell_addr = screen_base + char_row * 40 + char_col
                color_byte = ram[cell_addr]
                color1 = (color_byte >> 4) & 0x0F
                color2 = color_byte & 0x0F
                color3 = color_ram[char_row * 40 + char_col] & 0x0F

                colors = [bg_color, color1, color2, color3]

                bitmap_addr = bitmap_base + char_row * 320 + char_col * 8

                base_x = x_origin + char_col * 8
                base_y = y_origin + char_row * 8

                for y in range(8):
                    byte_val = ram[bitmap_addr + y]
                    for x in range(4):
                        bits = (byte_val >> (6 - x * 2)) & 0x03
                        c = COLORS[colors[bits]]
                        surface.set_at((base_x + x * 2, base_y + y), c)
                        surface.set_at((base_x + x * 2 + 1, base_y + y), c)

    def _render_sprites(self, surface, ram, vic_bank, screen_base, x_origin, y_origin, regs=None):
        """Render all 8 sprites with priority handling."""
        # Use provided regs (snapshot) or fall back to live regs
        if regs is None:
            regs = self.regs

        sprite_enable = regs[0x15]
        sprite_priority = regs[0x1B]  # 0 = sprite in front, 1 = behind
        sprite_multicolor = regs[0x1C]
        sprite_x_expand = regs[0x1D]
        sprite_y_expand = regs[0x17]
        sprite_x_msb = regs[0x10]

        mc_color0 = regs[0x25] & 0x0F
        mc_color1 = regs[0x26] & 0x0F

        # Sprite pointer base is at end of screen RAM
        sprite_ptr_base = screen_base + 0x3F8

        # Render sprites from 7 to 0 (lower numbers have higher priority)
        for sprite_num in range(7, -1, -1):
            if not (sprite_enable & (1 << sprite_num)):
                continue

            # Get sprite position
            x_pos = regs[sprite_num * 2]
            if sprite_x_msb & (1 << sprite_num):
                x_pos += 256
            y_pos = regs[sprite_num * 2 + 1]

            # Convert to screen coordinates
            sprite_x = x_pos - 24 + self.border_left
            sprite_y = y_pos - 50 + self.border_top

            # Get sprite data pointer
            sprite_ptr = ram[sprite_ptr_base + sprite_num]
            sprite_data_addr = vic_bank + sprite_ptr * 64

            # Get sprite color
            sprite_color = regs[0x27 + sprite_num] & 0x0F

            # Check expand flags
            x_expand = bool(sprite_x_expand & (1 << sprite_num))
            y_expand = bool(sprite_y_expand & (1 << sprite_num))
            is_multicolor = bool(sprite_multicolor & (1 << sprite_num))

            # Render 21 lines of 24 pixels (3 bytes per line)
            for line in range(21):
                y_screen = sprite_y + line * (2 if y_expand else 1)
                if y_expand:
                    y_screen2 = y_screen + 1

                for byte_idx in range(3):
                    byte_val = ram[sprite_data_addr + line * 3 + byte_idx]

                    if is_multicolor:
                        # Multicolor: 4 double-width pixels per byte
                        for px in range(4):
                            bits = (byte_val >> (6 - px * 2)) & 0x03
                            if bits == 0:
                                continue  # Transparent
                            elif bits == 1:
                                c = COLORS[mc_color0]
                            elif bits == 2:
                                c = COLORS[sprite_color]
                            else:
                                c = COLORS[mc_color1]

                            x_screen = sprite_x + byte_idx * 8 + px * 2
                            if x_expand:
                                x_screen *= 2
                                for dx in range(4):
                                    self._set_sprite_pixel(surface, x_screen + dx, y_screen, c)
                                    if y_expand:
                                        self._set_sprite_pixel(surface, x_screen + dx, y_screen2, c)
                            else:
                                self._set_sprite_pixel(surface, x_screen, y_screen, c)
                                self._set_sprite_pixel(surface, x_screen + 1, y_screen, c)
                                if y_expand:
                                    self._set_sprite_pixel(surface, x_screen, y_screen2, c)
                                    self._set_sprite_pixel(surface, x_screen + 1, y_screen2, c)
                    else:
                        # Standard: 8 single-width pixels per byte
                        for px in range(8):
                            if not (byte_val & (0x80 >> px)):
                                continue  # Transparent

                            c = COLORS[sprite_color]
                            x_screen = sprite_x + byte_idx * 8 + px
                            if x_expand:
                                x_screen *= 2
                                self._set_sprite_pixel(surface, x_screen, y_screen, c)
                                self._set_sprite_pixel(surface, x_screen + 1, y_screen, c)
                                if y_expand:
                                    self._set_sprite_pixel(surface, x_screen, y_screen2, c)
                                    self._set_sprite_pixel(surface, x_screen + 1, y_screen2, c)
                            else:
                                self._set_sprite_pixel(surface, x_screen, y_screen, c)
                                if y_expand:
                                    self._set_sprite_pixel(surface, x_screen, y_screen2, c)

    def _set_sprite_pixel(self, surface, x, y, color):
        """Set a sprite pixel with bounds checking."""
        if 0 <= x < self.total_width and 0 <= y < self.total_height:
            surface.set_at((x, y), color)
