"""Commodore 1541 Disk Drive Emulation.

The 1541 is a full computer in itself, containing:
- MOS 6502 CPU (same as C64, runs at ~1MHz)
- 2KB RAM ($0000-$07FF)
- 16KB ROM ($C000-$FFFF) containing DOS 2.6
- Two 6522 VIA chips:
  - VIA1 at $1800-$180F: IEC serial bus communication
  - VIA2 at $1C00-$1C0F: Disk drive mechanics control

Memory Map:
    $0000-$07FF: 2KB RAM
    $1800-$180F: VIA1 (IEC bus) - accent by 16-byte blocks
    $1C00-$1C0F: VIA2 (disk mechanics) - accent by 16-byte blocks
    $C000-$FFFF: 16KB ROM (DOS 2.6)

IEC Bus Signals (accent via VIA1 Port B):
    Bit 0: DATA IN (from bus via 7406 inverter, active HIGH when bus LOW)
    Bit 1: DATA OUT (to bus via inverter)
    Bit 2: CLK IN (from bus via 7406 inverter, active HIGH when bus LOW)
    Bit 3: CLK OUT (to bus via inverter)
    Bit 4: ATN ACK OUT (directly to bus, directly to ATN IN via loopback)
    Bit 5: Device address switch (directly from front panel)
    Bit 6: Device address switch (directly from front panel)
    Bit 7: ATN IN (from bus via 7406 inverter, active HIGH)

Disk Mechanics (VIA2):
    Port B:
        Bits 0-1: Stepper motor phase
        Bit 2: Drive motor on/off
        Bit 3: Drive LED on/off
        Bit 4: Write protect sense (0 = protected)
        Bits 5-6: Density select (bit rate zone)
        Bit 7: SYNC signal (0 = sync detected)

Reference:
- https://www.c64-wiki.com/wiki/Commodore_1541
- https://sta.c64.org/cbm1541mem.html
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .via6522 import VIA6522
from .d64 import D64Image, SECTORS_PER_TRACK, TRACK_SPEED_ZONE
from .gcr import GCRDisk

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU

log = logging.getLogger("drive1541")


# Memory map constants
RAM_START = 0x0000
RAM_END = 0x07FF
RAM_SIZE = 0x0800  # 2KB

VIA1_START = 0x1800
VIA1_END = 0x180F

VIA2_START = 0x1C00
VIA2_END = 0x1C0F

ROM_START = 0xC000
ROM_END = 0xFFFF
ROM_SIZE = 0x4000  # 16KB

# VIA1 Port B bit definitions (IEC bus accent)
VIA1_DATA_IN = 0x01   # Bit 0: DATA line input (via inverter, active HIGH when bus LOW)
VIA1_DATA_OUT = 0x02  # Bit 1: DATA line output (accent)
VIA1_CLK_IN = 0x04    # Bit 2: CLK line input (via inverter, active HIGH when bus LOW)
VIA1_CLK_OUT = 0x08   # Bit 3: CLK line output (accent)
VIA1_ATN_ACK = 0x10   # Bit 4: ATN acknowledge output (directly to bus, directly to ATN IN via loopback)
VIA1_ADDR_SW1 = 0x20  # Bit 5: Device address switch 1 (directly from front panel)
VIA1_ADDR_SW2 = 0x40  # Bit 6: Device address switch 2 (directly from front panel)
VIA1_ATN_IN = 0x80    # Bit 7: ATN line input (via inverter, active HIGH when ATN asserted)

# VIA2 Port B bit definitions (disk mechanics)
VIA2_STEP_MASK = 0x03   # Bits 0-1: Stepper motor phase
VIA2_MOTOR = 0x04       # Bit 2: Drive motor (1 = on)
VIA2_LED = 0x08         # Bit 3: Drive LED (1 = on)
VIA2_WP_SENSE = 0x10    # Bit 4: Write protect (0 = protected)
VIA2_DENSITY = 0x60     # Bits 5-6: Density/speed zone select
VIA2_SYNC = 0x80        # Bit 7: SYNC detect (0 = sync found)


class Drive1541Memory:
    """Memory subsystem for the 1541 drive.

    Handles the 1541's memory map including RAM, VIA chips, and ROM.
    """

    def __init__(self, drive: "Drive1541") -> None:
        self.drive = drive
        self.ram = bytearray(RAM_SIZE)
        self.rom = bytearray(ROM_SIZE)

    def read(self, addr: int) -> int:
        """Read from 1541 memory.

        Args:
            addr: 16-bit address

        Returns:
            Byte value at address
        """
        addr = addr & 0xFFFF

        # RAM: $0000-$07FF (mirrored in entire 2KB space)
        if addr < 0x0800:
            return self.ram[addr]

        # VIA1: $1800-$1BFF (mirrors every 16 bytes)
        # VIA2: $1C00-$1FFF (mirrors every 16 bytes)
        # Note: Check VIA2 first since its range is a subset that was being
        # incorrectly caught by VIA1's broader range check
        if 0x1C00 <= addr < 0x2000:
            return self.drive.via2.read(addr)

        if 0x1800 <= addr < 0x1C00:
            return self.drive.via1.read(addr)

        # ROM: $C000-$FFFF
        if addr >= ROM_START:
            return self.rom[addr - ROM_START]

        # Unmapped areas return open bus (usually $FF or last value)
        return 0xFF

    def write(self, addr: int, value: int) -> None:
        """Write to 1541 memory.

        Args:
            addr: 16-bit address
            value: Byte value to write
        """
        addr = addr & 0xFFFF
        value = value & 0xFF

        # RAM: $0000-$07FF
        if addr < 0x0800:
            self.ram[addr] = value
            return

        # VIA2: $1C00-$1FFF (mirrors every 16 bytes)
        # Note: Check VIA2 first - see read() comment
        if 0x1C00 <= addr < 0x2000:
            self.drive.via2.write(addr, value)
            return

        # VIA1: $1800-$1BFF (mirrors every 16 bytes)
        if 0x1800 <= addr < 0x1C00:
            self.drive.via1.write(addr, value)
            return

        # ROM writes are ignored


class Drive1541:
    """Commodore 1541 Disk Drive Emulator.

    This class emulates a complete 1541 disk drive including its own
    6502 CPU, RAM, ROM, two VIA chips, and disk mechanics.
    """

    def __init__(self, device_number: int = 8) -> None:
        """Initialize 1541 drive.

        Args:
            device_number: IEC device number (8-11, default 8)
        """
        self.device_number = device_number

        # CPU will be set by the C64 when the drive is attached
        self.cpu: Optional[MOS6502CPU] = None

        # Memory subsystem
        self.memory = Drive1541Memory(self)

        # VIA chips
        self.via1 = VIA6522(name="1541-VIA1")
        self.via2 = VIA6522(name="1541-VIA2")

        # Set up VIA callbacks
        self.via1.port_b_read_callback = self._via1_port_b_read
        self.via1.port_b_write_callback = self._via1_port_b_write
        self.via2.port_a_read_callback = self._via2_port_a_read
        self.via2.port_b_read_callback = self._via2_port_b_read
        self.via2.port_b_write_callback = self._via2_port_b_write
        self.via1.irq_callback = self._via1_irq
        self.via2.irq_callback = self._via2_irq

        # Disk image (D64 format)
        self.disk: Optional[D64Image] = None

        # GCR-encoded disk data for low-level emulation
        self.gcr_disk: Optional[GCRDisk] = None

        # IEC bus reference (set when connected to bus)
        self.iec_bus = None

        # IEC bus state (from C64's perspective)
        self.iec_atn = True   # ATN line (directly from C64)
        self.iec_clk = True   # CLK line (directly from bus)
        self.iec_data = True  # DATA line (directly from bus)

        # Initialize VIA1 CA1 to match inverted ATN state
        # ATN released (True) → CA1 LOW (False) via inverter
        self.via1.ca1 = False
        self.via1._ca1_prev = False

        # Drive mechanics state
        self.current_track = 1       # Head position (1-35)
        self.current_sector = 0      # Current sector
        self.motor_on = False        # Drive motor state
        self.led_on = False          # Drive LED state
        self.stepper_phase = 0       # Stepper motor phase (0-3)

        # GCR byte-ready timing
        # The 1541 uses the disk rotation to clock data.
        # At 300 RPM, a full rotation takes 200ms.
        # Bytes are read at varying rates depending on speed zone:
        #   Zone 3: ~26 cycles/byte (tracks 1-17)
        #   Zone 2: ~28 cycles/byte (tracks 18-24)
        #   Zone 1: ~30 cycles/byte (tracks 25-30)
        #   Zone 0: ~32 cycles/byte (tracks 31-35)
        self._byte_ready_counter = 0
        self._last_gcr_byte = 0x00
        self._sync_detected = False

        # Cycles per GCR byte for each speed zone
        self._cycles_per_byte = {
            0: 32,  # Slowest (outer tracks)
            1: 30,
            2: 28,
            3: 26,  # Fastest (inner tracks)
        }

        # ROM loaded flag
        self.rom_loaded = False

        # Cycle budget tracking for tick synchronization.
        # When the C64 asks us to run N cycles, we accumulate them here.
        # When we actually execute an instruction, we deduct the cycles used.
        # This prevents the drive from running ahead when instructions
        # take more cycles than the requested tick.
        self._pending_cycles = 0

    def load_rom(self, rom_path: Path, rom_path_e000: Optional[Path] = None) -> None:
        """Load 1541 DOS ROM.

        Supports two loading modes:
        1. Single 16KB ROM file (1541-II style, e.g., 251968-03.bin)
        2. Two 8KB ROM files (original 1541 style):
           - rom_path: $C000-$DFFF (e.g., 325302-01.bin)
           - rom_path_e000: $E000-$FFFF (e.g., 901229-05.bin)

        Common ROM versions:
        - 1541-II.251968-03.bin (16KB) - Most compatible, recommended
        - 1541-c000.325302-01.bin + 1541-e000.901229-05.bin (8KB each) - Original 1541

        Args:
            rom_path: Path to 16KB ROM, or 8KB ROM for $C000-$DFFF
            rom_path_e000: Optional path to 8KB ROM for $E000-$FFFF

        Raises:
            ValueError: If ROM size is incorrect
        """
        with open(rom_path, "rb") as f:
            rom_data = f.read()

        if len(rom_data) == ROM_SIZE:
            # Single 16KB ROM (1541-II style)
            self.memory.rom[:] = rom_data
            self.rom_loaded = True
            log.info(f"Loaded 1541 ROM (16KB): {rom_path}")

        elif len(rom_data) == ROM_SIZE // 2:
            # 8KB ROM for $C000-$DFFF, need second ROM for $E000-$FFFF
            if rom_path_e000 is None:
                raise ValueError(
                    f"8KB ROM provided ({rom_path.name}) but no $E000 ROM specified. "
                    f"Either provide a 16KB ROM or specify both 8KB ROMs."
                )

            with open(rom_path_e000, "rb") as f:
                rom_data_e000 = f.read()

            if len(rom_data_e000) != ROM_SIZE // 2:
                raise ValueError(
                    f"$E000 ROM must be 8KB, got {len(rom_data_e000)} bytes"
                )

            # Combine: C000 ROM first, then E000 ROM
            self.memory.rom[:0x2000] = rom_data
            self.memory.rom[0x2000:] = rom_data_e000
            self.rom_loaded = True
            log.info(f"Loaded 1541 ROM (8KB+8KB): {rom_path.name} + {rom_path_e000.name}")

        else:
            raise ValueError(
                f"1541 ROM must be 16KB or 8KB, got {len(rom_data)} bytes"
            )

    def insert_disk(self, disk_path: Path) -> None:
        """Insert a disk image into the drive.

        Args:
            disk_path: Path to D64 disk image
        """
        self.disk = D64Image(disk_path)
        # Create GCR-encoded version for low-level emulation
        self.gcr_disk = GCRDisk(self.disk)
        log.info(f"Disk inserted: {self.disk.get_disk_name()} (ID: {self.disk.get_disk_id()})")

    def eject_disk(self) -> None:
        """Eject the current disk."""
        if self.disk:
            log.info(f"Disk ejected: {self.disk.get_disk_name()}")
        self.disk = None
        self.gcr_disk = None

    def reset(self) -> None:
        """Reset the drive to power-on state."""
        self.via1.reset()
        self.via2.reset()
        self.memory.ram[:] = b'\x00' * RAM_SIZE

        self.current_track = 1
        self.current_sector = 0
        self.motor_on = False
        self.led_on = False
        self.stepper_phase = 0

        if self.cpu:
            self.cpu.reset()

    def tick(self, cycles: int = 1) -> None:
        """Advance drive state by CPU cycles.

        This method uses a cycle budget system to maintain proper synchronization
        with the C64. When called with N cycles, those cycles are added to a
        pending budget. We only execute the drive CPU when there are enough
        pending cycles to run at least one instruction (typically 2+ cycles).

        This prevents the drive from running ahead when instructions take more
        cycles than a single tick (e.g., if C64 ticks us with 1 cycle but the
        next instruction takes 4 cycles).

        Args:
            cycles: Number of cycles to advance
        """
        # Update VIA timers
        self.via1.tick(cycles)
        self.via2.tick(cycles)

        # Update GCR byte-ready timing if motor is running
        if self.motor_on and self.gcr_disk:
            self._update_gcr_read(cycles)

        # Execute drive CPU if we have one
        if self.cpu:
            # Add requested cycles to the pending budget
            self._pending_cycles += cycles

            # Only run if we have cycles to spend
            if self._pending_cycles > 0:
                # Record how many cycles we've used before executing
                cycles_before = self.cpu.cycles_executed

                try:
                    # Run until we've used our budget (or more)
                    self.cpu.execute(cycles=self._pending_cycles)
                except Exception as e:
                    # CPUCycleExhaustionError is normal
                    if "Exhausted" not in str(e):
                        log.error(f"1541 CPU error: {e}")

                # Deduct the cycles we actually used from the budget
                # This may go negative, which is fine - we'll wait for more
                # cycles to be added before running again
                cycles_used = self.cpu.cycles_executed - cycles_before
                self._pending_cycles -= cycles_used

    def _update_gcr_read(self, cycles: int) -> None:
        """Update GCR byte-ready timing for disk read.

        The 1541's disk spins at 300 RPM, with data clocked by the rotation.
        Each speed zone has a different bit rate, resulting in different
        cycles-per-byte timing.

        When a new byte is ready:
        1. The byte is latched into VIA2 Port A
        2. VIA2 CA1 (byte-ready) is pulsed to signal the CPU
        3. If SYNC bytes (0xFF) are detected, the SYNC flag is set

        Args:
            cycles: Number of CPU cycles elapsed
        """
        if not self.gcr_disk:
            return

        # Get current track's speed zone
        track_int = int(self.current_track)
        if track_int < 1:
            track_int = 1
        elif track_int > 35:
            track_int = 35

        speed_zone = TRACK_SPEED_ZONE[track_int - 1]
        cycles_per_byte = self._cycles_per_byte[speed_zone]

        # Accumulate cycles
        self._byte_ready_counter += cycles

        # Check if a new byte is ready
        while self._byte_ready_counter >= cycles_per_byte:
            self._byte_ready_counter -= cycles_per_byte

            # Read next GCR byte from track
            gcr_track = self.gcr_disk.get_track(track_int)
            if gcr_track:
                self._last_gcr_byte = gcr_track.read_byte()

                # Check for SYNC (0xFF)
                if self._last_gcr_byte == 0xFF:
                    self._sync_detected = True
                else:
                    # SYNC ends when we see a non-0xFF byte
                    if self._sync_detected:
                        self._sync_detected = False
                        # Signal byte-ready on first non-sync byte after sync
                        # This triggers CA1 edge on VIA2
                        self._signal_byte_ready()
                    else:
                        # Normal byte-ready during data
                        self._signal_byte_ready()

    def _signal_byte_ready(self) -> None:
        """Signal that a new GCR byte is ready for the CPU.

        This triggers VIA2 CA1 to signal the CPU that a byte can be read
        from VIA2 Port A.

        CRITICAL 1541 HARDWARE QUIRK:
        The byte-ready signal from VIA2 CA1 is also connected to the CPU's
        SO (Set Overflow) pin. This causes the V flag to be set when a byte
        is ready. The 1541 DOS uses "BVC *" loops to wait for byte-ready,
        which branch until V is set.

        Reference: https://www.c64-wiki.com/wiki/1541_Disk_Drive
        "The overflow line of the 6502 can be directly set via the DC."
        """
        # Set the CPU's overflow flag - this is how the 1541 detects byte-ready
        # The "BVC *" loop at $F3BE (and similar) waits for this
        if self.cpu:
            self.cpu.V = 1

        # Also trigger VIA2 CA1 for proper interrupt handling
        # Generate a negative pulse: high -> low -> high
        self.via2.set_ca1(False)
        self.via2.set_ca1(True)

    # =========================================================================
    # IEC Bus Interface
    # =========================================================================

    def set_iec_atn(self, state: bool) -> None:
        """Set ATN line state from C64.

        Args:
            state: ATN line state (True = released/high, False = asserted/low)
        """
        old_state = self.iec_atn
        self.iec_atn = state

        # ATN is connected to VIA1 CA1 through a 7406 inverter
        # - Bus ATN LOW (asserted) → Inverter → CA1 HIGH
        # - Bus ATN HIGH (released) → Inverter → CA1 LOW
        # The 1541 DOS uses PCR=$01 (positive edge on CA1)
        # So the interrupt triggers when ATN is ASSERTED (bus LOW → CA1 HIGH)
        self.via1.set_ca1(not state)

    def set_iec_clk(self, state: bool) -> None:
        """Set CLK line state from C64.

        Args:
            state: CLK line state
        """
        self.iec_clk = state

    def set_iec_data(self, state: bool) -> None:
        """Set DATA line state from C64.

        Args:
            state: DATA line state
        """
        self.iec_data = state

    def get_iec_clk(self) -> bool:
        """Get CLK line state as driven by drive.

        Returns:
            CLK line state (directly from drive)
        """
        # Drive's CLK output is VIA1 PB3, inverted on the bus
        clk_out = bool(self.via1.orb & VIA1_CLK_OUT)
        return not clk_out  # Invert for bus

    def get_iec_data(self) -> bool:
        """Get DATA line state as driven by drive.

        Returns:
            DATA line state (driven by drive)
        """
        # Drive's DATA output is VIA1 PB1, inverted on the bus
        data_out = bool(self.via1.orb & VIA1_DATA_OUT)
        return not data_out  # Invert for bus

    # =========================================================================
    # VIA1 Callbacks (IEC Bus)
    # =========================================================================

    def _via1_port_b_read(self) -> int:
        """Read VIA1 Port B (IEC bus state).

        All IEC input lines go through 7406 inverters:
        - Bus signal LOW → inverter → VIA reads HIGH
        - Bus signal HIGH → inverter → VIA reads LOW

        Returns:
            Port B input value
        """
        result = 0xFF

        # Bit 0: DATA IN (from bus via 7406 inverter)
        # Bus DATA LOW (asserted) → inverter → PB0 HIGH (set)
        # Bus DATA HIGH (released) → inverter → PB0 LOW (clear)
        if not self.iec_data:
            result |= VIA1_DATA_IN  # Set bit 0 when DATA is asserted (bus LOW)
        else:
            result &= ~VIA1_DATA_IN  # Clear bit 0 when DATA is released (bus HIGH)

        # Bit 2: CLK IN (from bus via 7406 inverter)
        # Bus CLK LOW (asserted) → inverter → PB2 HIGH (set)
        # Bus CLK HIGH (released) → inverter → PB2 LOW (clear)
        if not self.iec_clk:
            result |= VIA1_CLK_IN  # Set bit 2 when CLK is asserted (bus LOW)
        else:
            result &= ~VIA1_CLK_IN  # Clear bit 2 when CLK is released (bus HIGH)

        # Bits 5-6: Device address switches
        # Device 8 = both switches on (reading 00)
        # Device 9 = SW1 off (reading 01)
        # Device 10 = SW2 off (reading 10)
        # Device 11 = both off (reading 11)
        addr_offset = self.device_number - 8
        if addr_offset & 0x01:
            result |= VIA1_ADDR_SW1
        else:
            result &= ~VIA1_ADDR_SW1
        if addr_offset & 0x02:
            result |= VIA1_ADDR_SW2
        else:
            result &= ~VIA1_ADDR_SW2

        # Bit 7: ATN IN (from bus through 7406 inverter)
        # Bus ATN LOW (asserted) → inverter → PB7 HIGH (set)
        # Bus ATN HIGH (released) → inverter → PB7 LOW (clear)
        if not self.iec_atn:
            result |= VIA1_ATN_IN  # Set bit 7 when ATN is asserted (bus LOW)
        else:
            result &= ~VIA1_ATN_IN  # Clear bit 7 when ATN is released (bus HIGH)

        return result

    def _via1_port_b_write(self, value: int) -> None:
        """Handle VIA1 Port B write (IEC bus control).

        Args:
            value: Port B output value (masked by DDR)
        """
        # The drive is now outputting on the IEC bus
        # Immediately update IEC bus so C64 sees the change
        if self.iec_bus is not None:
            self.iec_bus.update()

    def _via1_irq(self, active: bool) -> None:
        """Handle VIA1 IRQ.

        The 1541's IRQ line is the OR of VIA1 and VIA2's IRQ outputs.
        When either VIA's IRQ state changes, we must recalculate the combined state.

        Args:
            active: Whether VIA1's IRQ is active
        """
        if self.cpu:
            # IRQ is active if either VIA has an active interrupt
            via2_irq = bool(self.via2.ifr & self.via2.ier & 0x7F)
            self.cpu.irq_pending = active or via2_irq

    # =========================================================================
    # VIA2 Callbacks (Disk Mechanics)
    # =========================================================================

    def _via2_port_a_read(self) -> int:
        """Read VIA2 Port A (GCR data from disk).

        The 1541's read head sends GCR-encoded data through the read amplifier
        to VIA2 Port A. Each byte read from Port A is one GCR-encoded byte.

        Returns:
            Last GCR byte read from disk
        """
        return self._last_gcr_byte

    def _via2_port_b_read(self) -> int:
        """Read VIA2 Port B (disk status).

        Returns:
            Port B input value with status bits:
            - Bit 4: Write protect (0 = protected)
            - Bit 7: SYNC (0 = sync detected)
        """
        result = 0x00

        # Bit 4: Write protect sense (0 = protected)
        # For now, always report not write protected
        result |= VIA2_WP_SENSE

        # Bit 7: SYNC signal (0 = sync detected, 1 = no sync)
        # SYNC is detected when we see consecutive 0xFF bytes (all 1s)
        if not self._sync_detected:
            result |= VIA2_SYNC  # No sync - bit is HIGH

        return result

    def _via2_port_b_write(self, value: int) -> None:
        """Handle VIA2 Port B write (disk mechanics control).

        Args:
            value: Port B output value
        """
        # Bits 0-1: Stepper motor phase
        new_phase = value & VIA2_STEP_MASK
        if new_phase != self.stepper_phase:
            self._update_stepper(new_phase)
            self.stepper_phase = new_phase

        # Bit 2: Drive motor
        self.motor_on = bool(value & VIA2_MOTOR)

        # Bit 3: Drive LED
        self.led_on = bool(value & VIA2_LED)

    def _via2_irq(self, active: bool) -> None:
        """Handle VIA2 IRQ.

        The 1541's IRQ line is the OR of VIA1 and VIA2's IRQ outputs.
        When either VIA's IRQ state changes, we must recalculate the combined state.

        Args:
            active: Whether VIA2's IRQ is active
        """
        if self.cpu:
            # IRQ is active if either VIA has an active interrupt
            via1_irq = bool(self.via1.ifr & self.via1.ier & 0x7F)
            self.cpu.irq_pending = active or via1_irq

    def _update_stepper(self, new_phase: int) -> None:
        """Update head position based on stepper motor phase change.

        Args:
            new_phase: New stepper phase (0-3)
        """
        # The stepper motor moves in half-track steps
        # Phase sequence for forward: 0->1->2->3->0
        # Phase sequence for reverse: 0->3->2->1->0
        phase_diff = (new_phase - self.stepper_phase) & 0x03

        if phase_diff == 1:
            # Forward (toward center)
            if self.current_track < 35:
                self.current_track += 0.5
        elif phase_diff == 3:
            # Reverse (toward outer edge)
            if self.current_track > 1:
                self.current_track -= 0.5

        # Clamp to valid track range
        self.current_track = max(1, min(35, self.current_track))

    # =========================================================================
    # Disk Access (for direct access, not through CPU)
    # =========================================================================

    def read_sector(self, track: int, sector: int) -> Optional[bytes]:
        """Read a sector from the disk (direct access).

        Args:
            track: Track number (1-35)
            sector: Sector number

        Returns:
            256 bytes of sector data, or None if no disk
        """
        if not self.disk:
            return None
        try:
            return bytes(self.disk.read_sector(track, sector))
        except ValueError:
            return None

    def write_sector(self, track: int, sector: int, data: bytes) -> bool:
        """Write a sector to the disk (direct access).

        Args:
            track: Track number (1-35)
            sector: Sector number
            data: 256 bytes of data

        Returns:
            True if successful, False otherwise
        """
        if not self.disk:
            return False
        try:
            self.disk.write_sector(track, sector, data)
            return True
        except ValueError:
            return False
