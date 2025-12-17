#!/usr/bin/env python3
"""C64 Memory management and banking logic.

This module contains:
- Memory map constants for the C64
- C64Memory class that implements the C64's memory banking and I/O mapping
"""


from mos6502.compat import logging
from mos6502.compat import TYPE_CHECKING, Optional

from c64.cartridges import (
    Cartridge,
    ROML_START,
    ROML_END,
    ROMH_START,
    ROMH_END,
    IO1_START,
    IO1_END,
    IO2_START,
    IO2_END,
)

if TYPE_CHECKING:
    from c64.cia1 import CIA1
    from c64.cia2 import CIA2
    from c64.sid import SID
    from c64.vic import C64VIC, ScreenDirtyTracker

log = logging.getLogger("c64")

# Debug flags - imported from parent module at runtime to avoid circular imports
DEBUG_SCREEN = False
DEBUG_JIFFY = False
DEBUG_CURSOR = False


# =============================================================================
# Memory Map Constants
# =============================================================================

# ROM regions
BASIC_ROM_START = 0xA000
BASIC_ROM_END = 0xBFFF
BASIC_ROM_SIZE = 0x2000  # 8KB

KERNAL_ROM_START = 0xE000
KERNAL_ROM_END = 0xFFFF
KERNAL_ROM_SIZE = 0x2000  # 8KB

CHAR_ROM_START = 0xD000
CHAR_ROM_END = 0xDFFF
CHAR_ROM_SIZE = 0x1000  # 4KB

# I/O regions within $D000-$DFFF
VIC_START = 0xD000
VIC_END = 0xD3FF
SID_START = 0xD400
SID_END = 0xD7FF
COLOR_RAM_START = 0xD800
COLOR_RAM_END = 0xDBFF
CIA1_START = 0xDC00
CIA1_END = 0xDCFF
CIA2_START = 0xDD00
CIA2_END = 0xDDFF

# C64 BASIC programs typically start here
BASIC_PROGRAM_START = 0x0801


class C64Memory:
    """C64 memory handler with banking logic.

    Implements the C64's complex memory banking scheme:
    - Zero page CPU I/O port ($0000-$0001) controls ROM/IO visibility
    - BASIC ROM ($A000-$BFFF) switchable with RAM
    - KERNAL ROM ($E000-$FFFF) switchable with RAM
    - Character ROM / I/O ($D000-$DFFF) switchable
    - Cartridge ROM support (ROML, ROMH, Ultimax mode)
    """

    def __init__(self, ram, *, basic_rom, kernal_rom, char_rom, cia1, cia2, vic, sid, dirty_tracker=None) -> None:
        # Store reference to flat RAM array for direct access (avoids delegation loop)
        # This eliminates branching on every RAM access
        self._ram = ram.data  # Direct reference to flat bytearray
        self.basic = basic_rom
        self.kernal = kernal_rom
        self.char = char_rom
        self.cia1 = cia1
        self.cia2 = cia2
        self.vic = vic
        self.sid = sid
        self.dirty_tracker = dirty_tracker

        # Color RAM - 1000 bytes ($D800-$DBE7), only low 4 bits used
        self.ram_color = bytearray(1024)

        # CPU I/O port
        self.ddr = 0x00  # $0000
        self.port = 0x37  # $0001 default value

        # Cartridge support - set by C64.load_cartridge()
        # The Cartridge object handles all banking logic and provides
        # EXROM/GAME signals and read methods for ROML/ROMH/IO regions
        self.cartridge: Optional[Cartridge] = None

        # Build read dispatch table indexed by top 4 bits of address (addr >> 12)
        # This eliminates linear if-chain for memory region detection
        self._read_dispatch = (
            self._read_region_0,    # $0xxx - CPU port + RAM
            self._read_ram_direct,  # $1xxx - RAM
            self._read_ram_direct,  # $2xxx - RAM
            self._read_ram_direct,  # $3xxx - RAM
            self._read_ram_direct,  # $4xxx - RAM
            self._read_ram_direct,  # $5xxx - RAM
            self._read_ram_direct,  # $6xxx - RAM
            self._read_ram_direct,  # $7xxx - RAM
            self._read_region_8_9,  # $8xxx - ROML or RAM
            self._read_region_8_9,  # $9xxx - ROML or RAM
            self._read_region_A_B,  # $Axxx - BASIC/ROMH or RAM
            self._read_region_A_B,  # $Bxxx - BASIC/ROMH or RAM
            self._read_ram_direct,  # $Cxxx - RAM
            self._read_region_D,    # $Dxxx - I/O or CHAR ROM
            self._read_region_E_F,  # $Exxx - KERNAL or RAM
            self._read_region_E_F,  # $Fxxx - KERNAL or RAM
        )

    def _read_region_0(self, addr: int) -> int:
        """Read from $0xxx region - CPU port or RAM."""
        if addr == 0x0000:
            return self.ddr
        if addr == 0x0001:
            return (self.port | (~self.ddr)) & 0xFF
        return self._ram[addr]

    def _read_region_8_9(self, addr: int) -> int:
        """Read from $8xxx-$9xxx - ROML cartridge or RAM.

        ROML visibility depends on cartridge EXROM/GAME signals AND CPU port:
        - Ultimax mode (EXROM=1, GAME=0): ROML always visible
        - 8K/16K mode (EXROM=0): ROML visible only when LORAM=1 AND HIRAM=1
          Setting LORAM=0 or HIRAM=0 exposes underlying RAM (used by diagnostics)
        """
        if self.cartridge is not None:
            # Ultimax mode: ROML always visible regardless of CPU port
            if self.cartridge.exrom and not self.cartridge.game:
                return self.cartridge.read_roml(addr)
            # 8K/16K mode (EXROM=0): Check CPU port bits
            if not self.cartridge.exrom:
                # ROML visible only when both LORAM=1 and HIRAM=1
                loram = self.port & 0b00000001
                hiram = self.port & 0b00000010
                if loram and hiram:
                    return self.cartridge.read_roml(addr)
        return self._ram[addr]

    def _read_region_A_B(self, addr: int) -> int:
        """Read from $Axxx-$Bxxx - ROMH cartridge, BASIC ROM, or RAM.

        Visibility depends on cartridge EXROM/GAME signals AND CPU port:
        - 16K mode (EXROM=0, GAME=0): ROMH visible only when LORAM=1 AND HIRAM=1
        - Without 16K cartridge: BASIC ROM visible only when LORAM=1 AND HIRAM=1
        - Setting LORAM=0 or HIRAM=0 exposes underlying RAM
        """
        loram = self.port & 0b00000001
        hiram = self.port & 0b00000010

        # Check for 16K cartridge ROMH (EXROM=0, GAME=0)
        if self.cartridge is not None and not self.cartridge.exrom and not self.cartridge.game:
            # ROMH visible only when both LORAM=1 and HIRAM=1
            if loram and hiram:
                return self.cartridge.read_romh(addr)
            # LORAM=0 or HIRAM=0: RAM visible instead of ROMH
            return self._ram[addr]
        # No 16K cartridge: BASIC ROM visible only when LORAM=1 AND HIRAM=1
        if loram and hiram:
            return self.basic[addr - BASIC_ROM_START]
        return self._ram[addr]

    def _read_region_D(self, addr: int) -> int:
        """Read from $Dxxx - I/O area, CHAR ROM, or RAM.

        The visibility of this region depends on CPU port bits:
        - CHAREN=1 (bit 2): I/O visible ($D000-$DFFF)
        - CHAREN=0 AND (LORAM=1 OR HIRAM=1): Character ROM visible
        - CHAREN=0 AND LORAM=0 AND HIRAM=0: RAM visible (all ROMs banked out)
        """
        charen = self.port & 0b00000100
        if charen:
            # CHAREN=1: I/O area visible
            return self._read_io_area(addr)
        # CHAREN=0: Check if we see Character ROM or RAM
        loram = self.port & 0b00000001
        hiram = self.port & 0b00000010
        if loram or hiram:
            # At least one ROM bit set: Character ROM visible
            return self.char[addr - CHAR_ROM_START]
        # Both LORAM=0 and HIRAM=0: All ROMs banked out, RAM visible
        return self._ram[addr]

    def _read_region_E_F(self, addr: int) -> int:
        """Read from $Exxx-$Fxxx - KERNAL ROM, Ultimax cartridge, or RAM."""
        # Ultimax mode: cartridge replaces KERNAL
        if self.cartridge is not None and self.cartridge.exrom and not self.cartridge.game:
            return self.cartridge.read_ultimax_romh(addr)
        # KERNAL ROM enabled?
        if self.port & 0b00000010:
            return self.kernal[addr - KERNAL_ROM_START]
        return self._ram[addr]

    def _read_ram_direct(self, addr) -> int:
        """Read directly from RAM storage without delegation."""
        # Direct flat array access - no branching
        return self._ram[addr]

    def _write_ram_direct(self, addr, value) -> None:
        """Write directly to RAM storage without delegation."""
        # Direct flat array access - no branching
        self._ram[addr] = int(value) & 0xFF

    def snapshot_ram(self) -> bytes:
        """Create a fast RAM snapshot by directly accessing underlying storage.

        This bypasses the memory handler to avoid triggering VIC/CIA reads
        and the infinite recursion that would cause. The snapshot captures
        the raw RAM state, not the banked view the CPU sees.

        Returns:
            65536 bytes representing the full 64KB RAM.
        """
        # Direct copy of flat RAM array - no memory handler involved
        return bytes(self._ram)

    def snapshot_vic_bank(self, vic_bank: int) -> bytes:
        """Create a fast snapshot of only the 16KB VIC bank the VIC can see.

        The VIC can only see 16KB of RAM at a time, selected by CIA2:
        - Bank 0: $0000-$3FFF (includes screen at $0400)
        - Bank 1: $4000-$7FFF
        - Bank 2: $8000-$BFFF
        - Bank 3: $C000-$FFFF

        Arguments:
            vic_bank: Base address of VIC bank (0x0000, 0x4000, 0x8000, or 0xC000)

        Returns:
            16384 bytes representing the 16KB VIC bank.
        """
        # Direct slice of flat RAM array - simple and fast
        bank_size = 0x4000  # 16KB
        return bytes(self._ram[vic_bank:vic_bank + bank_size])

    def snapshot_screen_area(self, screen_base: int, bitmap_mode: bool = False) -> bytes:
        """Create a minimal snapshot of just the video memory the VIC needs.

        For text mode: Just 1024 bytes at screen_base (1000 chars + sprite ptrs)
        For bitmap mode: 8192 bytes of bitmap data + 1024 bytes screen/color info

        Arguments:
            screen_base: Starting address of screen RAM (e.g., 0x0400)
            bitmap_mode: If True, snapshot includes 8KB bitmap data

        Returns:
            Snapshot of just the visible screen area.
        """
        # Screen RAM is 1000 bytes (40*25), but we grab 1024 to include
        # sprite pointers at screen+$3F8 (8 bytes)
        size = 0x2400 if bitmap_mode else 0x0400  # 9KB or 1KB

        return self._snapshot_range(screen_base, size)

    def _snapshot_range(self, start: int, size: int) -> bytes:
        """Snapshot a specific memory range directly from RAM storage.

        Arguments:
            start: Starting address
            size: Number of bytes to snapshot

        Returns:
            bytes object containing the memory range
        """
        # Direct slice of flat RAM array - simple and fast
        return bytes(self._ram[start:start + size])

    def _read_io_area(self, addr: int) -> int:
        """Read from I/O area ($D000-$DFFF)."""
        # VIC registers
        if VIC_START <= addr <= VIC_END:
            return self.vic.read(addr)
        # SID registers
        if SID_START <= addr <= SID_END:
            return self.sid.read(addr)
        # Color RAM
        if COLOR_RAM_START <= addr <= COLOR_RAM_END:
            return self.ram_color[addr - COLOR_RAM_START] | 0xF0
        # CIA1
        if CIA1_START <= addr <= CIA1_END:
            return self.cia1.read(addr)
        # CIA2
        if CIA2_START <= addr <= CIA2_END:
            return self.cia2.read(addr)
        # Cartridge I/O1 ($DE00-$DEFF)
        if IO1_START <= addr <= IO1_END:
            if self.cartridge is not None:
                return self.cartridge.read_io1(addr)
            return 0xFF
        # Cartridge I/O2 ($DF00-$DFFF)
        if IO2_START <= addr <= IO2_END:
            if self.cartridge is not None:
                return self.cartridge.read_io2(addr)
            return 0xFF
        return 0xFF

    def read(self, addr) -> int:
        """Read from C64 memory using dispatch table for fast region lookup."""
        # Single table lookup replaces 8+ conditional checks
        # addr >> 12 gives top 4 bits (0-15), indexing into 16-entry dispatch table
        return self._read_dispatch[addr >> 12](addr)

    def _write_io_area(self, addr: int, value: int) -> None:
        """Write to I/O area ($D000-$DFFF)."""
        # VIC registers
        if 0xD000 <= addr <= 0xD3FF:
            self.vic.write(addr, value)
            # Track VIC register changes (may affect global rendering)
            if self.dirty_tracker is not None and addr <= 0xD02E:
                self.dirty_tracker.mark_vic_dirty()
            return
        # SID registers
        if 0xD400 <= addr <= 0xD7FF:
            self.sid.write(addr, value)
            return
        # Color RAM
        if 0xD800 <= addr <= 0xDBFF:
            self.ram_color[addr - 0xD800] = value & 0x0F  # Only 4 bits
            # Track color RAM changes
            if self.dirty_tracker is not None:
                self.dirty_tracker.mark_color_dirty(addr)
            return
        # CIA1
        if 0xDC00 <= addr <= 0xDCFF:
            self.cia1.write(addr, value)
            return
        # CIA2
        if 0xDD00 <= addr <= 0xDDFF:
            self.cia2.write(addr, value)
            return
        # Cartridge I/O1 ($DE00-$DEFF) - bank switching registers for many cartridge types
        if IO1_START <= addr <= IO1_END:
            if self.cartridge is not None:
                self.cartridge.write_io1(addr, value)
            return
        # Cartridge I/O2 ($DF00-$DFFF)
        if IO2_START <= addr <= IO2_END:
            if self.cartridge is not None:
                self.cartridge.write_io2(addr, value)
            return

    def write(self, addr, value) -> None:
        """Write to C64 memory with banking logic."""
        # Temporary debug: log ALL write calls
        if DEBUG_SCREEN and 0x0400 <= addr <= 0x07E7:
            log.info(f"*** C64Memory.write() CALLED: addr=${addr:04X}, value=${value:02X} ***")
        # CPU internal port
        if addr == 0x0000:
            self.ddr = value & 0xFF
            return
        if addr == 0x0001:
            self.port = value & 0xFF
            return

        # $0002-$7FFF is always RAM (includes screen RAM at $0400-$07E7)
        if 0x0002 <= addr <= 0x7FFF:
            # Log writes to screen RAM ($0400-$07E7)
            if 0x0400 <= addr <= 0x07E7:
                if DEBUG_SCREEN:
                    log.info(f"*** SCREEN WRITE: addr=${addr:04X}, value=${value:02X} (char={chr(value) if 32 <= value < 127 else '?'}) ***")
                # Track dirty screen cells for optimized rendering
                if self.dirty_tracker is not None:
                    self.dirty_tracker.mark_screen_dirty(addr)
            self._write_ram_direct(addr, value & 0xFF)
            return

        # ROML region ($8000-$9FFF) - check for cartridge RAM first
        if 0x8000 <= addr <= 0x9FFF:
            # Some cartridges (like Action Replay) have writable RAM here
            if self.cartridge is not None and self.cartridge.write_roml(addr, value):
                return  # Cartridge handled the write
            # Otherwise fall through to C64 RAM
            self._write_ram_direct(addr, value & 0xFF)
            return

        # Memory banking logic (only applies to $A000-$FFFF)
        io_enabled = self.port & 0b00000100

        # I/O area ($D000-$DFFF)
        if CHAR_ROM_START <= addr <= CHAR_ROM_END and io_enabled:
            self._write_io_area(addr, value)
            return

        # Writes to $A000-$FFFF always go to underlying RAM
        # (Even if ROM/I/O is visible for reads, writes always go to RAM)
        self._write_ram_direct(addr, value & 0xFF)
