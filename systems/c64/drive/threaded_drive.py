"""Threaded 1541 Drive Implementation.

This module provides a threaded version of the 1541 drive that runs
independently from the C64 CPU in its own thread.

Threading Model:
    - The drive runs in a dedicated background thread
    - IEC bus communication uses the ThreadedIECBus for synchronization
    - VIA callbacks update shared IEC state atomically
    - No cycle-accurate synchronization - both CPUs run independently

This provides significant performance improvement when the C64 is not
actively accessing the disk, as the two CPUs can run in parallel.
"""


from mos6502.compat import logging
import threading
import time
from mos6502.compat import TYPE_CHECKING, Optional

from .drive1541 import Drive1541, VIA1_DATA_OUT, VIA1_CLK_OUT, VIA1_ATN_ACK
from .threaded_iec_bus import ThreadedIECBus
from mos6502.errors import CPUCycleExhaustionError

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU

log = logging.getLogger("drive1541")


class ThreadedDrive1541(Drive1541):
    """1541 Drive with independent thread execution.

    This extends Drive1541 to run in its own thread, communicating with
    the C64 only through the ThreadedIECBus shared state.
    """

    # How many cycles to run per iteration of the drive loop
    # Small batch for responsive IEC bus - each instruction is 2-7 cycles
    # so this runs ~2-5 instructions per batch
    CYCLES_PER_BATCH = 10

    # Minimum sleep time between batches (seconds)
    # Disabled (0) for maximum IEC responsiveness
    MIN_SLEEP_TIME = 0

    def __init__(self, device_number: int = 8) -> None:
        """Initialize threaded 1541 drive.

        Args:
            device_number: IEC device number (8-11, default 8)
        """
        super().__init__(device_number)

        # Re-set VIA callbacks to point to our overridden methods
        # (super().__init__ sets them to the base class methods)
        self.via1.port_b_read_callback = self._via1_port_b_read
        self.via1.port_b_write_callback = self._via1_port_b_write

        # Threading state
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._stop_event = threading.Event()

        # Throttling control - disabled by default for reliable IEC timing
        self._throttle_enabled = False

        # Reference to threaded IEC bus (set when connected)
        self._threaded_iec_bus: Optional[ThreadedIECBus] = None

        # Track how many cycles the drive has executed for sync
        self._drive_cycles: int = 0

        # Pre-compute address switch bits (device number 8-11 = bits 5-6)
        # These never change during operation so cache them
        addr_offset = device_number - 8
        self._address_switch_mask = 0
        if addr_offset & 0x01:
            self._address_switch_mask |= 0x20  # Bit 5
        if addr_offset & 0x02:
            self._address_switch_mask |= 0x40  # Bit 6

    def start_thread(self) -> None:
        """Start the drive's execution thread."""
        if self._thread is not None and self._thread.is_alive():
            log.warning("Drive thread already running")
            return

        if self.cpu is None:
            log.error("Cannot start drive thread: no CPU attached")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._drive_thread_main,
            name=f"1541-Drive-{self.device_number}",
            daemon=True
        )
        self._thread.start()
        log.info(f"Started 1541 drive {self.device_number} thread")

    def stop_thread(self, timeout: float = 2.0) -> None:
        """Stop the drive's execution thread.

        Args:
            timeout: Maximum time to wait for thread to stop
        """
        if self._thread is None:
            return

        self._running = False
        self._stop_event.set()

        self._thread.join(timeout=timeout)
        if self._thread.is_alive():
            log.warning(f"Drive {self.device_number} thread did not stop gracefully")
        else:
            log.info(f"Stopped 1541 drive {self.device_number} thread")

        self._thread = None

    def set_throttle(self, enabled: bool) -> None:
        """Enable or disable throttling.

        Args:
            enabled: True to throttle drive speed, False for maximum speed
        """
        self._throttle_enabled = enabled

    def _drive_thread_main(self) -> None:
        """Main loop for the drive thread.

        Runs the drive CPU in sync with the C64 by tracking cycle counts.
        The drive only runs when the C64 has run more cycles, keeping them
        in lockstep like the synchronous mode.

        Uses condition variable to efficiently wait for C64 cycles instead
        of busy-polling with sleep().
        """
        log.debug(f"Drive {self.device_number} thread starting")

        while self._running and not self._stop_event.is_set():
            try:
                # Wait for C64 to run ahead of us (uses condition variable)
                if self._threaded_iec_bus is None:
                    time.sleep(0.001)
                    continue

                # Efficiently wait for cycles using condition variable
                cycles_behind = self._threaded_iec_bus.wait_for_cycles(
                    self._drive_cycles, timeout=0.001
                )

                if cycles_behind > 0:
                    # Update our view of the IEC bus state before executing
                    self._update_iec_input_from_bus()

                    # Run drive for the cycles we're behind (in small batches)
                    cycles_to_run = min(cycles_behind, self.CYCLES_PER_BATCH)

                    # Update VIA timers
                    self.via1.tick(cycles_to_run)
                    self.via2.tick(cycles_to_run)

                    # Update GCR byte-ready timing if motor is running
                    if self.motor_on and self.gcr_disk:
                        self._update_gcr_read(cycles_to_run)

                    # Execute CPU
                    if self.cpu:
                        try:
                            self.cpu.execute(cycles=cycles_to_run)
                        except CPUCycleExhaustionError:
                            pass  # Normal - cycle budget exhausted

                    # Track cycles executed
                    self._drive_cycles += cycles_to_run

                    # Update our IEC output state to the bus
                    self._update_iec_output_to_bus()

            except Exception as e:
                log.error(f"Drive {self.device_number} thread error: {e}")
                import traceback
                traceback.print_exc()

        log.debug(f"Drive {self.device_number} thread stopping")

    def _update_iec_input_from_bus(self) -> None:
        """Update our cached IEC input state from the shared bus."""
        if self._threaded_iec_bus is not None:
            atn, clk, data = self._threaded_iec_bus.get_drive_input(self.device_number)

            # Update cached state (used by VIA1 Port B read callback)
            old_atn = self.iec_atn
            self.iec_atn = atn
            self.iec_clk = clk
            self.iec_data = data

            # Handle ATN edge detection for interrupt
            if old_atn != atn:
                # ATN changed - update VIA1 CA1
                # ATN is connected to CA1 through a 7406 inverter
                self.via1.set_ca1(not atn)

    def _update_iec_output_to_bus(self) -> None:
        """Update our IEC output state to the shared bus."""
        if self._threaded_iec_bus is not None:
            # Read our VIA1 Port B outputs
            # Only consider bits that are configured as outputs (via DDR)
            orb = self.via1.orb
            ddrb = self.via1.ddrb

            # CLK OUT is bit 3, DATA OUT is bit 1, ATNA is bit 4
            clk_out = bool(ddrb & VIA1_CLK_OUT) and bool(orb & VIA1_CLK_OUT)
            data_out = bool(ddrb & VIA1_DATA_OUT) and bool(orb & VIA1_DATA_OUT)
            atna_out = bool(ddrb & VIA1_ATN_ACK) and bool(orb & VIA1_ATN_ACK)

            self._threaded_iec_bus.set_drive_outputs(
                self.device_number, clk_out, data_out, atna_out
            )

    # Override the VIA1 Port B write callback to update bus state immediately
    def _via1_port_b_write(self, value: int) -> None:
        """Handle VIA1 Port B write (IEC bus control).

        In threaded mode, we update the shared bus state immediately.

        Args:
            value: Port B output value (masked by DDR)
        """
        # Update IEC bus immediately
        self._update_iec_output_to_bus()

    # Override the VIA1 Port B read callback to read LIVE bus state
    def _via1_port_b_read(self) -> int:
        """Handle VIA1 Port B read (IEC bus input).

        In threaded mode, we read the LIVE bus state from the shared bus
        to see C64's outputs immediately, not stale cached values.

        Returns:
            Port B input value with current IEC bus state
        """
        # Read live bus state from the threaded bus
        # IMPORTANT: exclude our own device so we don't see our own outputs
        if self._threaded_iec_bus is not None:
            atn, clk, data = self._threaded_iec_bus.get_drive_input(self.device_number)

            # Check for ATN edge and trigger interrupt if changed
            old_atn = self.iec_atn
            if old_atn != atn:
                # ATN changed - update VIA1 CA1 for interrupt
                self.via1.set_ca1(not atn)

            # Update cached state
            self.iec_atn = atn
            self.iec_clk = clk
            self.iec_data = data
        else:
            # Fall back to cached values if no bus connected
            atn = self.iec_atn
            clk = self.iec_clk
            data = self.iec_data

        # Build result efficiently - start with address switch bits (cached, constant)
        # IEC signals are active-low on bus but active-high after 7406 inverter
        # So bus LOW (asserted) -> port bit HIGH
        result = self._address_switch_mask

        # Bit 0: DATA IN - set when DATA asserted (bus LOW)
        if not data:
            result |= 0x01

        # Bit 2: CLK IN - set when CLK asserted (bus LOW)
        if not clk:
            result |= 0x04

        # Bit 7: ATN IN - set when ATN asserted (bus LOW)
        if not atn:
            result |= 0x80

        return result

    # Override tick to do nothing - we manage our own timing in the thread
    def tick(self, cycles: int = 1) -> None:
        """No-op in threaded mode - drive manages its own timing.

        In threaded mode, the drive runs independently and this method
        is not used for synchronization.

        Args:
            cycles: Ignored in threaded mode
        """
        # In threaded mode, the drive thread handles all timing
        pass

    def connect_to_threaded_bus(self, bus: ThreadedIECBus) -> None:
        """Connect to a ThreadedIECBus.

        Args:
            bus: The threaded IEC bus to connect to
        """
        self._threaded_iec_bus = bus
        self.iec_bus = bus  # For compatibility with base class
        bus.connect_drive(self)
