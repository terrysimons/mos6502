"""Multiprocess 1541 Drive Implementation.

This module provides a multiprocess version of the 1541 drive that runs
in a separate Python process, bypassing the GIL for true parallel execution.

Process Model:
    - Main process runs the C64
    - Drive subprocess runs the 1541 independently
    - IEC bus communication via shared memory
    - Commands (disk insert/eject) via multiprocessing.Queue
"""


from mos6502.compat import logging
import multiprocessing
import os
import sys
import time
from mos6502.compat import Path
from mos6502.compat import Optional

# Use fork context on POSIX for better performance
# (spawn has overhead of reimporting modules)
if sys.platform != 'win32':
    mp_context = multiprocessing.get_context('fork')
else:
    mp_context = multiprocessing.get_context('spawn')

Process = mp_context.Process
Queue = mp_context.Queue

from .multiprocess_iec_bus import (
    SharedIECState,
    FLAG_SHUTDOWN,
    FLAG_DRIVE_READY,
)

log = logging.getLogger("drive1541")

# How many cycles to run per tick batch
# Larger values reduce overhead but may delay IEC responses
CYCLES_PER_BATCH = 1000


def drive_process_main(
    shared_mem_name: str,
    rom_path: str,
    rom_path_e000: Optional[str],
    disk_path: Optional[str],
    device_number: int,
    command_queue: Queue,
    tick_request_event,  # multiprocessing.Event
    tick_done_event,     # multiprocessing.Event
) -> None:
    """Main function for drive subprocess.

    This runs in a separate process and manages:
    - Drive CPU execution
    - IEC bus communication via shared memory
    - Disk image loading and persistence

    Args:
        shared_mem_name: Name of shared memory segment for IEC state
        rom_path: Path to 1541 ROM file (C000 or full 16KB)
        rom_path_e000: Optional path to E000 ROM file (for split ROMs)
        disk_path: Optional path to D64 disk image
        device_number: IEC device number (8-11)
        command_queue: Queue for receiving commands from main process
    """
    # Import here to avoid issues with multiprocessing on some platforms
    from .drive1541 import Drive1541, VIA1_DATA_OUT, VIA1_CLK_OUT, VIA1_ATN_ACK
    from mos6502 import CPU, CPUVariant
    from mos6502.errors import CPUCycleExhaustionError

    # Set up logging for subprocess
    subprocess_log = logging.getLogger(f"drive1541.subprocess.{device_number}")
    subprocess_log.info(f"Drive {device_number} subprocess starting (PID: {os.getpid()})")

    try:
        # Attach to shared memory
        shared_state = SharedIECState(name=shared_mem_name, create=False)

        # Create drive instance
        drive = Drive1541(device_number)

        # Create CPU for the drive (1541 uses standard 6502)
        drive_cpu = CPU(CPUVariant.NMOS_6502, False)
        drive.cpu = drive_cpu
        drive_cpu.ram.memory_handler = drive.memory

        # Load ROM
        rom_path_obj = Path(rom_path)
        rom_path_e000_obj = Path(rom_path_e000) if rom_path_e000 else None
        drive.load_rom(rom_path_obj, rom_path_e000_obj)
        subprocess_log.info(f"Loaded ROM: {rom_path_obj.name}")

        # Insert disk if provided
        if disk_path:
            disk_path_obj = Path(disk_path)
            drive.insert_disk(disk_path_obj)
            subprocess_log.info(f"Inserted disk: {disk_path_obj.name}")

        # Reset drive
        drive.reset()

        # Pre-compute address switch bits for Port B reads
        addr_offset = device_number - 8
        address_switch_mask = 0
        if addr_offset & 0x01:
            address_switch_mask |= 0x20  # Bit 5
        if addr_offset & 0x02:
            address_switch_mask |= 0x40  # Bit 6

        # Track cycles
        drive_cycles = 0

        # Cache ATN state for edge detection
        last_atn = True

        # Signal that we're ready
        shared_state.set_drive_ready(True)
        subprocess_log.info(f"Drive {device_number} subprocess ready")

        # Main execution loop - cycle-counter based synchronization
        # Drive runs until it catches up to C64's cycle count
        command_check_counter = 0

        while not shared_state.is_shutdown_requested():
            # Check for commands periodically (every ~1000 iterations)
            command_check_counter += 1
            if command_check_counter >= 1000:
                command_check_counter = 0
                try:
                    while not command_queue.empty():
                        cmd = command_queue.get_nowait()
                        if cmd[0] == "insert_disk":
                            disk_path_obj = Path(cmd[1])
                            drive.insert_disk(disk_path_obj)
                            subprocess_log.info(f"Inserted disk: {disk_path_obj.name}")
                        elif cmd[0] == "eject_disk":
                            drive.eject_disk()
                            subprocess_log.info("Ejected disk")
                        elif cmd[0] == "shutdown":
                            subprocess_log.info("Received shutdown command")
                            shared_state.request_shutdown()
                            break
                except Exception:
                    pass

            # Get C64's current cycle count
            c64_cycles = shared_state.get_c64_cycles()

            # Calculate how many cycles we need to run to catch up
            cycles_behind = c64_cycles - drive_cycles
            if cycles_behind <= 0:
                # We're caught up or ahead - wait briefly for C64 to advance
                tick_request_event.wait(timeout=0.001)
                tick_request_event.clear()
                continue

            # Run a batch of cycles to catch up (limit batch size)
            cycles_to_run = min(cycles_behind, CYCLES_PER_BATCH)

            # Read IEC bus state from shared memory
            c64_atn_out, c64_clk_out, c64_data_out = shared_state.get_c64_outputs()

            # Compute bus state (open-collector logic)
            atn = not c64_atn_out

            # Check for ATN edge and trigger interrupt
            if atn != last_atn:
                drive.via1.set_ca1(not atn)
                last_atn = atn

            # Update drive's cached IEC state
            drive.iec_atn = atn

            # Read our own VIA1 outputs for open-collector logic
            orb = drive.via1.orb
            ddrb = drive.via1.ddrb
            our_clk_out = bool(ddrb & VIA1_CLK_OUT) and bool(orb & VIA1_CLK_OUT)
            our_data_out = bool(ddrb & VIA1_DATA_OUT) and bool(orb & VIA1_DATA_OUT)
            our_atna = bool(ddrb & VIA1_ATN_ACK) and bool(orb & VIA1_ATN_ACK)

            # Combined bus state
            clk = not (c64_clk_out or our_clk_out)
            data = not (c64_data_out or our_data_out)

            # ATN ACK XOR logic
            if our_atna != (not atn):
                data = False

            drive.iec_clk = clk
            drive.iec_data = data

            # Update VIA timers
            drive.via1.tick(cycles_to_run)
            drive.via2.tick(cycles_to_run)

            # Update GCR byte-ready timing if motor is running
            if drive.motor_on and drive.gcr_disk:
                drive._update_gcr_read(cycles_to_run)

            # Execute CPU
            try:
                drive_cpu.execute(cycles=cycles_to_run)
            except CPUCycleExhaustionError:
                pass

            # Track cycles executed
            drive_cycles += cycles_to_run
            shared_state.set_drive_cycles(drive_cycles)

            # Update shared memory with drive outputs
            orb = drive.via1.orb
            ddrb = drive.via1.ddrb
            clk_out = bool(ddrb & VIA1_CLK_OUT) and bool(orb & VIA1_CLK_OUT)
            data_out = bool(ddrb & VIA1_DATA_OUT) and bool(orb & VIA1_DATA_OUT)
            atna_out = bool(ddrb & VIA1_ATN_ACK) and bool(orb & VIA1_ATN_ACK)
            shared_state.set_drive_outputs(clk_out, data_out, atna_out)

        subprocess_log.info(f"Drive {device_number} subprocess exiting normally")

    except Exception as e:
        subprocess_log.error(f"Drive subprocess error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up
        try:
            shared_state.close()
        except Exception:
            pass


class MultiprocessDrive1541:
    """1541 Drive that runs in a separate process.

    This is the main process wrapper that manages the subprocess.
    It provides the same basic interface as Drive1541/ThreadedDrive1541
    but delegates actual execution to a subprocess.
    """

    def __init__(self, device_number: int = 8) -> None:
        """Initialize multiprocess drive wrapper.

        Args:
            device_number: IEC device number (8-11, default 8)
        """
        self.device_number = device_number

        # Process management
        self._process: Optional[Process] = None
        self._shared_state: Optional[SharedIECState] = None
        self._command_queue: Optional[Queue] = None
        self._tick_request_event = None
        self._tick_done_event = None

        # For compatibility with code that checks these
        self.cpu = None  # CPU is in subprocess
        self.iec_bus = None

    def start_process(
        self,
        rom_path: Path,
        rom_path_e000: Optional[Path] = None,
        disk_path: Optional[Path] = None,
        shared_state: Optional[SharedIECState] = None,
    ) -> None:
        """Start the drive subprocess.

        Args:
            rom_path: Path to 1541 ROM file
            rom_path_e000: Optional path to E000 ROM (for split ROMs)
            disk_path: Optional D64 disk image to insert
            shared_state: SharedIECState instance (creates new one if None)
        """
        if self._process is not None and self._process.is_alive():
            log.warning("Drive process already running")
            return

        # Create shared memory if not provided
        if shared_state is None:
            self._shared_state = SharedIECState(
                name=f"iec_bus_{os.getpid()}_{self.device_number}",
                create=True
            )
        else:
            self._shared_state = shared_state

        # Create command queue
        self._command_queue = Queue()

        # Create Events for tick synchronization
        self._tick_request_event = mp_context.Event()
        self._tick_done_event = mp_context.Event()

        # Start subprocess
        self._process = Process(
            target=drive_process_main,
            args=(
                self._shared_state.name,
                str(rom_path),
                str(rom_path_e000) if rom_path_e000 else None,
                str(disk_path) if disk_path else None,
                self.device_number,
                self._command_queue,
                self._tick_request_event,
                self._tick_done_event,
            ),
            name=f"1541-Drive-{self.device_number}",
            daemon=True,
        )
        self._process.start()
        log.info(f"Started 1541 drive {self.device_number} process (PID: {self._process.pid})")

        # Wait for drive to be ready
        timeout = 5.0
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._shared_state.is_drive_ready():
                log.info(f"Drive {self.device_number} process ready")
                return
            time.sleep(0.01)

        log.warning(f"Drive {self.device_number} process did not report ready within {timeout}s")

    def stop_process(self, timeout: float = 2.0) -> None:
        """Stop the drive subprocess gracefully.

        Args:
            timeout: Maximum time to wait for graceful shutdown
        """
        if self._process is None:
            return

        # Signal shutdown via shared memory
        if self._shared_state is not None:
            self._shared_state.request_shutdown()

        # Also send shutdown command via queue
        if self._command_queue is not None:
            try:
                self._command_queue.put(("shutdown",))
            except Exception:
                pass

        # Wait for clean exit
        self._process.join(timeout=timeout)

        if self._process.is_alive():
            log.warning(f"Drive {self.device_number} process did not stop gracefully, terminating")
            self._process.terminate()
            self._process.join(timeout=1.0)

            if self._process.is_alive():
                log.error(f"Drive {self.device_number} process did not terminate, killing")
                self._process.kill()
                self._process.join(timeout=1.0)
        else:
            log.info(f"Stopped 1541 drive {self.device_number} process")

        # Clean up shared memory
        if self._shared_state is not None:
            self._shared_state.close()
            self._shared_state.unlink()
            self._shared_state = None

        self._process = None
        self._command_queue = None

    def insert_disk(self, disk_path: Path) -> None:
        """Send disk insertion command to subprocess.

        Args:
            disk_path: Path to D64 disk image
        """
        if self._command_queue is not None:
            self._command_queue.put(("insert_disk", str(disk_path)))
            log.info(f"Sent insert_disk command: {disk_path.name}")

    def eject_disk(self) -> None:
        """Send disk ejection command to subprocess."""
        if self._command_queue is not None:
            self._command_queue.put(("eject_disk",))
            log.info("Sent eject_disk command")

    def tick(self, cycles: int = 1) -> None:
        """No-op - subprocess manages its own timing.

        Args:
            cycles: Ignored in multiprocess mode
        """
        pass

    def reset(self) -> None:
        """Reset is handled at process start - no-op here."""
        pass

    @property
    def is_running(self) -> bool:
        """Check if the subprocess is running."""
        return self._process is not None and self._process.is_alive()

    def get_shared_state(self) -> Optional[SharedIECState]:
        """Get the shared state object for IEC bus communication."""
        return self._shared_state

    def get_tick_events(self):
        """Get the tick synchronization Events.

        Returns:
            Tuple of (tick_request_event, tick_done_event)
        """
        return self._tick_request_event, self._tick_done_event
