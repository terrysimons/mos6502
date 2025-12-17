"""IEC Serial Bus Emulation.

The IEC (IEEE-488 derived) serial bus connects the C64 to disk drives and
other peripherals. It uses an open-collector design with active-low signaling.

Bus Signals:
    ATN (Attention): Controlled by C64, signals start of command
    CLK (Clock): Timing for serial data transmission
    DATA: Serial data line

Signal Logic:
    - All lines are active-low (0 = asserted, 1 = released)
    - Open-collector: any device can pull a line low
    - Lines go high only when ALL devices release them

C64 Connection (via CIA2 Port A):
    Bit 3: ATN OUT (directly to bus)
    Bit 4: CLK OUT (to bus)
    Bit 5: DATA OUT (to bus)
    Bit 6: CLK IN (from bus)
    Bit 7: DATA IN (from bus)

1541 Connection (via VIA1 Port B):
    Bit 0: DATA IN (from bus)
    Bit 1: DATA OUT (to bus via inverter)
    Bit 2: CLK IN (from bus)
    Bit 3: CLK OUT (to bus via inverter)
    Bit 7: ATN IN (from bus)

The outputs pass through a 7406 inverter on both ends:
    - C64: Port bit 1 -> inverter -> bus line LOW
    - C64: Port bit 0 -> inverter -> bus line HIGH (released)
    - 1541: Same logic applies

Reference:
- https://www.pagetable.com/?p=1135 (IEC bus timings)
- https://www.c64-wiki.com/wiki/Serial_Port
"""


from mos6502.compat import logging
from mos6502.compat import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from ..cia2 import CIA2
    from .drive1541 import Drive1541

log = logging.getLogger("iec_bus")


class IECBus:
    """IEC Serial Bus connecting C64 to peripheral devices.

    This class manages the electrical state of the IEC bus, handling
    the open-collector logic where any device can pull a line low.
    """

    def __init__(self) -> None:
        """Initialize the IEC bus."""
        # Connected devices
        self.cia2: Optional["CIA2"] = None  # C64's CIA2
        self.drives: List["Drive1541"] = []

        # Bus line states (True = released/high, False = asserted/low)
        # These represent the actual bus state after open-collector resolution
        self.atn = True
        self.clk = True
        self.data = True

        # Track what each device is driving (for open-collector logic)
        # C64's output states (from CIA2 Port A)
        self._c64_atn_out = False   # Port A bit 3
        self._c64_clk_out = False   # Port A bit 4
        self._c64_data_out = False  # Port A bit 5

        # Cycle tracking for drive synchronization
        # When the C64 writes to the IEC bus, we need to catch the drive up
        # to the current C64 cycle count before updating bus state
        self._last_drive_sync_cycle = 0

        # Cache of last input state for change detection
        # Avoids recomputing bus state when nothing has changed
        self._last_input_state = None  # Invalid initial value to force first update

    def connect_c64(self, cia2: "CIA2") -> None:
        """Connect C64's CIA2 to the bus.

        Args:
            cia2: C64's CIA2 chip
        """
        self.cia2 = cia2
        log.info("C64 connected to IEC bus")

    def connect_drive(self, drive: "Drive1541") -> None:
        """Connect a drive to the bus.

        Args:
            drive: 1541 drive to connect
        """
        if drive not in self.drives:
            self.drives.append(drive)
            drive.iec_bus = self  # Give drive reference to bus for immediate updates
            log.info(f"Drive {drive.device_number} connected to IEC bus")

    def disconnect_drive(self, drive: "Drive1541") -> None:
        """Disconnect a drive from the bus.

        Args:
            drive: 1541 drive to disconnect
        """
        if drive in self.drives:
            self.drives.remove(drive)
            drive.iec_bus = None
            log.info(f"Drive {drive.device_number} disconnected from IEC bus")

    def sync_drives(self) -> None:
        """Synchronize drive CPUs to the current C64 cycle count.

        This ensures drives are caught up before we sample/change bus state.
        Called automatically by update() but can be called manually for
        tighter synchronization.
        """
        if not self.cia2:
            return

        # Get current C64 cycle count (handle mock CIA2 without cpu attribute)
        cpu = getattr(self.cia2, 'cpu', None)
        if cpu is None:
            return

        c64_cycles = cpu.cycles_executed

        # Calculate cycles elapsed since last sync
        cycles_to_run = c64_cycles - self._last_drive_sync_cycle

        if cycles_to_run > 0:
            for drive in self.drives:
                if drive.cpu is not None:
                    # Run drive CPU for the elapsed cycles
                    drive.tick(cycles_to_run)

            self._last_drive_sync_cycle = c64_cycles

    def update(self) -> None:
        """Update bus state based on all connected devices.

        This implements open-collector logic: the bus line is low if ANY
        device is pulling it low, and high only if ALL devices release it.
        """
        cia2 = self.cia2
        if not cia2:
            return

        # Read C64's output from CIA2 Port A
        c64_port_a = cia2.port_a
        c64_ddr_a = cia2.ddr_a

        # ATN: Only C64 can drive ATN (True = released, False = asserted)
        atn = not (c64_ddr_a & 0x08 and c64_port_a & 0x08)

        # CLK and DATA: Start with C64's contribution
        clk_low = c64_ddr_a & 0x10 and c64_port_a & 0x10
        data_low = c64_ddr_a & 0x20 and c64_port_a & 0x20

        # Process all drive contributions
        # Pre-compute ATN logical state for ATNA XOR check
        atn_asserted = not atn  # True when ATN is asserted (bus LOW)
        for drive in self.drives:
            via1 = drive.via1
            # Combine port output and direction into effective output bits
            output_bits = via1.orb & via1.ddrb

            # CLK OUT is bit 3 - if set, pulls bus LOW
            if output_bits & 0x08:
                clk_low = True

            # DATA OUT is bit 1 - if set, pulls bus LOW
            if output_bits & 0x02:
                data_low = True

            # ATN ACK (bit 4) - XOR: different states pull DATA low
            # Only applies if bit 4 is configured as output (check via1.ddrb)
            if via1.ddrb & 0x10:
                atna_set = bool(output_bits & 0x10)
                # Different logical states = DATA pulled low
                if atna_set != atn_asserted:
                    data_low = True

        clk = not clk_low
        data = not data_low

        # Check if anything changed
        atn_changed = atn != self.atn
        clk_changed = clk != self.clk
        data_changed = data != self.data

        # Store bus state
        self.atn = atn
        self.clk = clk
        self.data = data

        # Update drives - ATN always (for CA1 edge detection), others only if changed
        if atn_changed or clk_changed or data_changed:
            for drive in self.drives:
                drive.set_iec_atn(atn)  # Always call - has CA1 side effects
                if clk_changed:
                    drive.iec_clk = clk
                if data_changed:
                    drive.iec_data = data

    def get_c64_input(self) -> int:
        """Get the bus state for CIA2 Port A input bits.

        Returns:
            Port A input value (bits 6-7: CLK IN, DATA IN)
        """
        # The input bits read the actual bus state
        # Build result directly using bitwise ops for speed
        # CLK on bit 6, DATA on bit 7 - set means line is HIGH (released)
        return 0x3F | (0x40 if self.clk else 0) | (0x80 if self.data else 0)
