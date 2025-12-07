"""Thread-Safe IEC Serial Bus Emulation.

This module provides a thread-safe version of the IEC bus that allows the
C64 and 1541 drive to run in separate threads with independent clocks.

The IEC (IEEE-488 derived) serial bus connects the C64 to disk drives and
other peripherals. It uses an open-collector design with active-low signaling.

Threading Model:
    - C64 runs in the main/CPU thread
    - Each 1541 drive runs in its own background thread
    - IEC bus state is protected by a lock for thread-safety
    - Bus state is computed on-demand when either side reads

Bus Signals:
    ATN (Attention): Controlled by C64, signals start of command
    CLK (Clock): Timing for serial data transmission
    DATA: Serial data line

Signal Logic:
    - All lines are active-low (0 = asserted, 1 = released)
    - Open-collector: any device can pull a line low
    - Lines go high only when ALL devices release them

Reference:
- https://www.pagetable.com/?p=1135 (IEC bus timings)
- https://www.c64-wiki.com/wiki/Serial_Port
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from ..cia2 import CIA2
    from .drive1541 import Drive1541

log = logging.getLogger("iec_bus")


class ThreadedIECBus:
    """Thread-safe IEC Serial Bus for multi-threaded emulation.

    This class manages the electrical state of the IEC bus with proper
    synchronization for concurrent access from C64 and drive threads.

    Each device (C64, drives) stores its output state, and the bus state
    is computed on-demand using open-collector logic when any device reads.
    """

    def __init__(self) -> None:
        """Initialize the threaded IEC bus."""
        # Lock for thread-safe access to bus state
        self._lock = threading.Lock()

        # Connected devices (protected by lock for modification)
        self.cia2: Optional[CIA2] = None
        self._drives: Dict[int, Drive1541] = {}  # device_number -> drive

        # C64's output states (written by C64 thread, read by all)
        # These are the inverted port bits - True means driving bus LOW
        self._c64_atn_out = False   # Port A bit 3
        self._c64_clk_out = False   # Port A bit 4
        self._c64_data_out = False  # Port A bit 5

        # Drive output states (written by drive threads, read by all)
        # Key: device_number, Value: (clk_out, data_out, atna_out)
        # These are the inverted VIA bits - True means driving bus LOW
        self._drive_outputs: Dict[int, tuple] = {}

        # Shared cycle counter for synchronization
        # The C64 updates this, drives read it to stay in sync
        self._c64_cycles: int = 0

    @property
    def drives(self):
        """Get list of connected drives (for compatibility)."""
        with self._lock:
            return list(self._drives.values())

    def connect_c64(self, cia2: CIA2) -> None:
        """Connect C64's CIA2 to the bus.

        Args:
            cia2: C64's CIA2 chip
        """
        with self._lock:
            self.cia2 = cia2
        log.info("C64 connected to threaded IEC bus")

    def connect_drive(self, drive: Drive1541) -> None:
        """Connect a drive to the bus.

        Args:
            drive: 1541 drive to connect
        """
        with self._lock:
            if drive.device_number not in self._drives:
                self._drives[drive.device_number] = drive
                self._drive_outputs[drive.device_number] = (False, False, False)
                drive.iec_bus = self
        log.info(f"Drive {drive.device_number} connected to threaded IEC bus")

    def disconnect_drive(self, drive: Drive1541) -> None:
        """Disconnect a drive from the bus.

        Args:
            drive: 1541 drive to disconnect
        """
        with self._lock:
            if drive.device_number in self._drives:
                del self._drives[drive.device_number]
                del self._drive_outputs[drive.device_number]
                drive.iec_bus = None
        log.info(f"Drive {drive.device_number} disconnected from threaded IEC bus")

    def set_c64_outputs(self, atn_out: bool, clk_out: bool, data_out: bool) -> None:
        """Set C64's IEC output states (called from C64 thread).

        Args:
            atn_out: True if C64 is driving ATN low
            clk_out: True if C64 is driving CLK low
            data_out: True if C64 is driving DATA low
        """
        with self._lock:
            self._c64_atn_out = atn_out
            self._c64_clk_out = clk_out
            self._c64_data_out = data_out

    def set_c64_cycles(self, cycles: int) -> None:
        """Update the C64 cycle counter for drive synchronization.

        Args:
            cycles: Current C64 CPU cycle count
        """
        self._c64_cycles = cycles  # Atomic on most platforms, no lock needed

    def get_c64_cycles(self) -> int:
        """Get the current C64 cycle count.

        Returns:
            Current C64 CPU cycle count
        """
        return self._c64_cycles

    def set_drive_outputs(self, device_number: int, clk_out: bool, data_out: bool,
                          atna_out: bool) -> None:
        """Set a drive's IEC output states (called from drive thread).

        Args:
            device_number: Drive's device number (8-11)
            clk_out: True if drive is driving CLK low
            data_out: True if drive is driving DATA low
            atna_out: ATN acknowledge bit state
        """
        with self._lock:
            if device_number in self._drive_outputs:
                self._drive_outputs[device_number] = (clk_out, data_out, atna_out)

    def get_bus_state(self, exclude_device: int = None) -> tuple:
        """Compute current bus state using open-collector logic.

        This reads the CURRENT state from drive VIA registers, not cached values,
        to ensure the C64 sees the most up-to-date drive outputs.

        Args:
            exclude_device: Optional device number to exclude from bus state calculation.
                           Used when a drive reads the bus - it shouldn't see its own outputs.

        Returns:
            Tuple of (atn, clk, data) where True = released/high, False = asserted/low
        """
        with self._lock:
            # ATN: Only C64 can drive ATN
            atn = not self._c64_atn_out

            # CLK: Both C64 and drives can drive this
            clk_low = self._c64_clk_out

            # DATA: Both C64 and drives can drive this
            data_low = self._c64_data_out

            # Read LIVE state from each drive's VIA registers
            # This is critical for the IEC handshake protocol to work!
            for device_num, drive in self._drives.items():
                # Skip the requesting drive - it shouldn't see its own outputs
                if device_num == exclude_device:
                    continue

                # Read directly from VIA1 registers for real-time state
                orb = drive.via1.orb
                ddrb = drive.via1.ddrb

                # Drive CLK OUT is VIA1 Port B bit 3, also inverted
                if ddrb & 0x08:  # If configured as output
                    if orb & 0x08:  # If driving low
                        clk_low = True

                # Drive DATA OUT is VIA1 Port B bit 1, inverted
                if ddrb & 0x02:  # If configured as output
                    if orb & 0x02:  # If driving low
                        data_low = True

                # ATN ACK (bit 4) - XORed with ATN before affecting DATA
                if ddrb & 0x10:  # If configured as output
                    atna_bit = bool(orb & 0x10)
                    atn_logical = not atn  # True when ATN is asserted
                    # Different logical states = DATA pulled low
                    if atna_bit != atn_logical:
                        data_low = True

            clk = not clk_low
            data = not data_low

            return (atn, clk, data)

    def get_c64_input(self) -> int:
        """Get the bus state for CIA2 Port A input bits.

        Returns:
            Port A input value (bits 6-7: CLK IN, DATA IN)
        """
        _, clk, data = self.get_bus_state()

        result = 0xFF
        if not clk:
            result &= ~0x40  # CLK is low
        if not data:
            result &= ~0x80  # DATA is low

        return result

    def get_drive_input(self, device_number: int) -> tuple:
        """Get bus state for a drive's VIA1 Port B input bits.

        The drive should see the C64's outputs and other drives' outputs,
        but NOT its own outputs (it already knows what it's outputting).

        Args:
            device_number: Drive's device number

        Returns:
            Tuple of (atn, clk, data) where True = released/high, False = asserted/low
        """
        return self.get_bus_state(exclude_device=device_number)

    def update(self) -> None:
        """Update bus state and notify all drives.

        This mirrors the original IECBus.update() behavior:
        1. Read C64's outputs from CIA2
        2. Compute bus state using open-collector logic
        3. Update all drives with current bus state
        """
        if self.cia2 is None:
            return

        # Read C64's output from CIA2 Port A
        c64_port_a = self.cia2.port_a
        c64_ddr_a = self.cia2.ddr_a

        # Only consider bits that are configured as outputs
        atn_out = bool(c64_ddr_a & 0x08) and bool(c64_port_a & 0x08)
        clk_out = bool(c64_ddr_a & 0x10) and bool(c64_port_a & 0x10)
        data_out = bool(c64_ddr_a & 0x20) and bool(c64_port_a & 0x20)

        self.set_c64_outputs(atn_out, clk_out, data_out)

        # Compute current bus state and update all drives
        # This is critical - drives need their cached IEC state updated!
        atn, clk, data = self.get_bus_state()

        with self._lock:
            for drive in self._drives.values():
                drive.set_iec_atn(atn)
                drive.set_iec_clk(clk)
                drive.set_iec_data(data)

    def sync_drives(self) -> None:
        """No-op in threaded mode - drives run independently."""
        pass


# Convenience constants for VIA1 Port B bits
VIA1_DATA_IN = 0x01   # Bit 0
VIA1_DATA_OUT = 0x02  # Bit 1
VIA1_CLK_IN = 0x04    # Bit 2
VIA1_CLK_OUT = 0x08   # Bit 3
VIA1_ATNA_OUT = 0x10  # Bit 4
VIA1_ADDR_SW1 = 0x20  # Bit 5
VIA1_ADDR_SW2 = 0x40  # Bit 6
VIA1_ATN_IN = 0x80    # Bit 7
