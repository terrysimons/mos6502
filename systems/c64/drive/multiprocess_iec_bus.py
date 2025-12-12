"""Multiprocess IEC Serial Bus Emulation.

This module provides a multiprocess version of the IEC bus that allows the
C64 and 1541 drive to run in separate processes, bypassing the Python GIL
for true parallel execution.

Shared Memory Layout (64 bytes):
    Bytes 0:     C64 outputs (ATN, CLK, DATA as bits 0-2)
    Bytes 1:     Drive outputs (CLK, DATA, ATNA as bits 0-2)
    Bytes 2:     Reserved
    Bytes 3:     Control flags (ready, shutdown, disk-change)
    Bytes 4-7:   C64 cycle counter (uint32, little-endian)
    Bytes 8-11:  Drive cycle counter (uint32, little-endian)
    Bytes 12-63: Reserved for future use

Signal Logic:
    - All lines are active-low (0 = asserted, 1 = released)
    - Open-collector: any device can pull a line low
    - Lines go high only when ALL devices release them
"""

from __future__ import annotations

import logging
import struct
from multiprocessing import shared_memory
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..cia2 import CIA2

log = logging.getLogger("iec_bus")

# Shared memory layout offsets
OFFSET_C64_OUTPUTS = 0      # C64 ATN/CLK/DATA output bits
OFFSET_DRIVE_OUTPUTS = 1    # Drive CLK/DATA/ATNA output bits
OFFSET_RESERVED1 = 2        # Reserved
OFFSET_CONTROL_FLAGS = 3    # Control flags
OFFSET_C64_CYCLES = 4       # C64 cycle counter (4 bytes)
OFFSET_DRIVE_CYCLES = 8     # Drive cycle counter (4 bytes)
OFFSET_PENDING_TICKS = 12   # Pending tick cycles for drive to execute (4 bytes)
OFFSET_TICK_DONE = 16       # Flag: drive has finished pending ticks (1 byte)
SHARED_MEMORY_SIZE = 64     # Total size in bytes

# Import multiprocessing Event for synchronization
import multiprocessing

# C64 output bits (byte 0)
C64_ATN_OUT_BIT = 0x01      # Bit 0: ATN output (True = driving low)
C64_CLK_OUT_BIT = 0x02      # Bit 1: CLK output (True = driving low)
C64_DATA_OUT_BIT = 0x04     # Bit 2: DATA output (True = driving low)

# Drive output bits (byte 1)
DRIVE_CLK_OUT_BIT = 0x01    # Bit 0: CLK output (True = driving low)
DRIVE_DATA_OUT_BIT = 0x02   # Bit 1: DATA output (True = driving low)
DRIVE_ATNA_OUT_BIT = 0x04   # Bit 2: ATN ACK output

# Control flags (byte 3)
FLAG_DRIVE_READY = 0x01     # Bit 0: Drive process is ready
FLAG_SHUTDOWN = 0x02        # Bit 1: Shutdown requested
FLAG_DISK_CHANGE = 0x04     # Bit 2: Disk change pending


class SharedIECState:
    """Manages shared memory for IEC bus state between processes.

    This class provides atomic read/write operations for IEC bus signals
    and cycle counters. Single-byte operations are inherently atomic on
    modern CPUs, so no explicit locking is needed for the signal bytes.
    """

    def __init__(self, name: str, create: bool = True) -> None:
        """Initialize shared memory for IEC state.

        Args:
            name: Unique name for the shared memory segment
            create: If True, create new shared memory. If False, attach to existing.
        """
        self._name = name
        self._create = create

        if create:
            # Try to clean up any existing segment with the same name
            try:
                existing = shared_memory.SharedMemory(name=name, create=False)
                existing.close()
                existing.unlink()
                log.debug(f"Cleaned up existing shared memory '{name}'")
            except FileNotFoundError:
                pass  # No existing segment - good

            # Create new shared memory segment
            self._shm = shared_memory.SharedMemory(
                name=name,
                create=True,
                size=SHARED_MEMORY_SIZE
            )
            # Initialize to zeros
            self._shm.buf[:SHARED_MEMORY_SIZE] = bytes(SHARED_MEMORY_SIZE)
            log.debug(f"Created shared memory '{name}' ({SHARED_MEMORY_SIZE} bytes)")
        else:
            # Attach to existing shared memory
            self._shm = shared_memory.SharedMemory(name=name, create=False)
            log.debug(f"Attached to shared memory '{name}'")

    @property
    def name(self) -> str:
        """Get the shared memory segment name."""
        return self._name

    def close(self) -> None:
        """Close the shared memory handle (does not destroy it)."""
        if self._shm is not None:
            self._shm.close()
            self._shm = None

    def unlink(self) -> None:
        """Destroy the shared memory segment (call only from creator)."""
        if self._create:
            try:
                shared_memory.SharedMemory(name=self._name, create=False).unlink()
            except FileNotFoundError:
                pass  # Already unlinked

    # --- C64 Output Methods ---

    def set_c64_outputs(self, atn_out: bool, clk_out: bool, data_out: bool) -> None:
        """Set C64's IEC output state.

        Args:
            atn_out: True if C64 is driving ATN low
            clk_out: True if C64 is driving CLK low
            data_out: True if C64 is driving DATA low
        """
        value = 0
        if atn_out:
            value |= C64_ATN_OUT_BIT
        if clk_out:
            value |= C64_CLK_OUT_BIT
        if data_out:
            value |= C64_DATA_OUT_BIT
        self._shm.buf[OFFSET_C64_OUTPUTS] = value

    def get_c64_outputs(self) -> tuple[bool, bool, bool]:
        """Get C64's IEC output state.

        Returns:
            Tuple of (atn_out, clk_out, data_out)
        """
        value = self._shm.buf[OFFSET_C64_OUTPUTS]
        return (
            bool(value & C64_ATN_OUT_BIT),
            bool(value & C64_CLK_OUT_BIT),
            bool(value & C64_DATA_OUT_BIT)
        )

    # --- Drive Output Methods ---

    def set_drive_outputs(self, clk_out: bool, data_out: bool, atna_out: bool) -> None:
        """Set drive's IEC output state.

        Args:
            clk_out: True if drive is driving CLK low
            data_out: True if drive is driving DATA low
            atna_out: ATN acknowledge bit state
        """
        value = 0
        if clk_out:
            value |= DRIVE_CLK_OUT_BIT
        if data_out:
            value |= DRIVE_DATA_OUT_BIT
        if atna_out:
            value |= DRIVE_ATNA_OUT_BIT
        self._shm.buf[OFFSET_DRIVE_OUTPUTS] = value

    def get_drive_outputs(self) -> tuple[bool, bool, bool]:
        """Get drive's IEC output state.

        Returns:
            Tuple of (clk_out, data_out, atna_out)
        """
        value = self._shm.buf[OFFSET_DRIVE_OUTPUTS]
        return (
            bool(value & DRIVE_CLK_OUT_BIT),
            bool(value & DRIVE_DATA_OUT_BIT),
            bool(value & DRIVE_ATNA_OUT_BIT)
        )

    # --- Bus State Computation ---

    def get_bus_state(self, is_drive: bool = False) -> tuple[bool, bool, bool]:
        """Compute combined bus state using open-collector logic.

        Args:
            is_drive: If True, exclude drive's own outputs from calculation

        Returns:
            Tuple of (atn, clk, data) where True = released/high, False = asserted/low
        """
        c64_atn_out, c64_clk_out, c64_data_out = self.get_c64_outputs()

        # ATN: Only C64 can drive ATN
        atn = not c64_atn_out

        # CLK and DATA: Open-collector - start with C64's contribution
        clk_low = c64_clk_out
        data_low = c64_data_out

        if not is_drive:
            # C64 reading: include drive outputs
            drive_clk_out, drive_data_out, drive_atna_out = self.get_drive_outputs()
            if drive_clk_out:
                clk_low = True
            if drive_data_out:
                data_low = True

            # ATN ACK XOR logic: if ATNA differs from ATN, pull DATA low
            atn_asserted = not atn
            if drive_atna_out != atn_asserted:
                data_low = True

        return (atn, not clk_low, not data_low)

    # --- Cycle Counter Methods ---

    def set_c64_cycles(self, cycles: int) -> None:
        """Update C64 cycle counter.

        Args:
            cycles: Current C64 CPU cycle count
        """
        struct.pack_into('<I', self._shm.buf, OFFSET_C64_CYCLES, cycles & 0xFFFFFFFF)

    def get_c64_cycles(self) -> int:
        """Get C64 cycle counter.

        Returns:
            Current C64 CPU cycle count
        """
        return struct.unpack_from('<I', self._shm.buf, OFFSET_C64_CYCLES)[0]

    def set_drive_cycles(self, cycles: int) -> None:
        """Update drive cycle counter.

        Args:
            cycles: Current drive CPU cycle count
        """
        struct.pack_into('<I', self._shm.buf, OFFSET_DRIVE_CYCLES, cycles & 0xFFFFFFFF)

    def get_drive_cycles(self) -> int:
        """Get drive cycle counter.

        Returns:
            Current drive CPU cycle count
        """
        return struct.unpack_from('<I', self._shm.buf, OFFSET_DRIVE_CYCLES)[0]

    # --- Control Flag Methods ---

    def set_flag(self, flag: int, value: bool) -> None:
        """Set a control flag.

        Args:
            flag: Flag bit constant (FLAG_DRIVE_READY, FLAG_SHUTDOWN, etc.)
            value: True to set, False to clear
        """
        current = self._shm.buf[OFFSET_CONTROL_FLAGS]
        if value:
            self._shm.buf[OFFSET_CONTROL_FLAGS] = current | flag
        else:
            self._shm.buf[OFFSET_CONTROL_FLAGS] = current & ~flag

    def get_flag(self, flag: int) -> bool:
        """Get a control flag.

        Args:
            flag: Flag bit constant

        Returns:
            True if flag is set
        """
        return bool(self._shm.buf[OFFSET_CONTROL_FLAGS] & flag)

    def request_shutdown(self) -> None:
        """Signal drive process to shut down."""
        self.set_flag(FLAG_SHUTDOWN, True)

    def is_shutdown_requested(self) -> bool:
        """Check if shutdown was requested."""
        return self.get_flag(FLAG_SHUTDOWN)

    def set_drive_ready(self, ready: bool = True) -> None:
        """Set the drive ready flag."""
        self.set_flag(FLAG_DRIVE_READY, ready)

    def is_drive_ready(self) -> bool:
        """Check if drive process is ready."""
        return self.get_flag(FLAG_DRIVE_READY)

    # --- Tick Synchronization Methods ---

    def set_pending_ticks(self, cycles: int) -> None:
        """Set number of cycles for drive to execute.

        Args:
            cycles: Number of cycles to run
        """
        struct.pack_into('<I', self._shm.buf, OFFSET_PENDING_TICKS, cycles & 0xFFFFFFFF)
        # Clear done flag when setting new ticks
        self._shm.buf[OFFSET_TICK_DONE] = 0

    def get_pending_ticks(self) -> int:
        """Get pending tick count.

        Returns:
            Number of cycles still pending
        """
        return struct.unpack_from('<I', self._shm.buf, OFFSET_PENDING_TICKS)[0]

    def clear_pending_ticks(self) -> None:
        """Clear pending ticks (drive consumed them)."""
        struct.pack_into('<I', self._shm.buf, OFFSET_PENDING_TICKS, 0)

    def set_tick_done(self) -> None:
        """Signal that drive finished processing ticks."""
        self._shm.buf[OFFSET_TICK_DONE] = 1

    def is_tick_done(self) -> bool:
        """Check if drive finished processing ticks."""
        return self._shm.buf[OFFSET_TICK_DONE] != 0

    def add_ticks(self, cycles: int) -> None:
        """Add cycles to pending ticks (atomic increment).

        Args:
            cycles: Number of cycles to add
        """
        current = self.get_pending_ticks()
        struct.pack_into('<I', self._shm.buf, OFFSET_PENDING_TICKS, (current + cycles) & 0xFFFFFFFF)


class MultiprocessIECBus:
    """IEC Bus implementation for C64 side of multiprocess mode.

    This class provides the same interface as ThreadedIECBus but communicates
    with the drive process via shared memory instead of direct method calls.
    """

    def __init__(self, shared_state: SharedIECState) -> None:
        """Initialize the multiprocess IEC bus.

        Args:
            shared_state: SharedIECState instance for IPC
        """
        self._shared = shared_state
        self.cia2: Optional[CIA2] = None

        # Cached bus state for get_c64_input() speed
        self.atn = True
        self.clk = True
        self.data = True

    def connect_c64(self, cia2: CIA2) -> None:
        """Connect C64's CIA2 to the bus.

        Args:
            cia2: C64's CIA2 chip
        """
        self.cia2 = cia2
        log.info("C64 connected to multiprocess IEC bus")

    def update(self) -> None:
        """Update bus state by reading CIA2 and writing to shared memory.

        This should be called after each C64 instruction to keep the
        drive process informed of C64's IEC outputs.
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

        # Write to shared memory
        self._shared.set_c64_outputs(atn_out, clk_out, data_out)

        # Read bus state (includes drive outputs)
        self.atn, self.clk, self.data = self._shared.get_bus_state(is_drive=False)

    def get_c64_input(self) -> int:
        """Get the bus state for CIA2 Port A input bits.

        Returns:
            Port A input value (bits 6-7: CLK IN, DATA IN)
        """
        # Use cached values from last update() call
        # CLK on bit 6, DATA on bit 7 - set means line is HIGH (released)
        return 0x3F | (0x40 if self.clk else 0) | (0x80 if self.data else 0)

    def set_c64_cycles(self, cycles: int) -> None:
        """Update the C64 cycle counter for drive synchronization.

        Args:
            cycles: Current C64 CPU cycle count
        """
        self._shared.set_c64_cycles(cycles)

    def sync_drives(self) -> None:
        """No-op in multiprocess mode - drive runs independently."""
        pass

    def set_tick_events(self, tick_request: multiprocessing.Event,
                        tick_done: multiprocessing.Event) -> None:
        """Set the Events used for tick synchronization.

        Args:
            tick_request: Event to signal drive that ticks are pending
            tick_done: Event drive sets when ticks are processed
        """
        self._tick_request = tick_request
        self._tick_done = tick_done

    def tick(self, cycles: int) -> None:
        """Send tick cycles to drive and wait for completion.

        This provides synchronous tick-based execution similar to threaded mode.
        The method blocks until the drive has processed the ticks.

        Args:
            cycles: Number of cycles to execute
        """
        # Add cycles to pending ticks
        self._shared.add_ticks(cycles)

        # Signal drive that ticks are pending
        if hasattr(self, '_tick_request') and self._tick_request:
            self._tick_done.clear()
            self._tick_request.set()

            # Wait for drive to process the ticks (with timeout)
            if not self._tick_done.wait(timeout=0.1):
                # Timeout - clear pending and continue
                self._shared.clear_pending_ticks()
        else:
            # Fallback: spin-wait if Events not set up
            max_spins = 10000
            spins = 0
            while self._shared.get_pending_ticks() > 0:
                spins += 1
                if spins >= max_spins:
                    self._shared.clear_pending_ticks()
                    break

        # Read updated bus state after drive processed ticks
        self.atn, self.clk, self.data = self._shared.get_bus_state(is_drive=False)

    @property
    def drives(self) -> list:
        """Get list of connected drives (empty in multiprocess mode)."""
        # In multiprocess mode, drives are in separate processes
        return []
