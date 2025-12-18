"""C64 Drive Mixin.

Mixin for 1541 disk drive operations.
"""

from mos6502.compat import logging, Path, Optional
from mos6502 import CPU, CPUVariant

# Drive module imports are conditional (not available on Pico)
_DRIVE_AVAILABLE = False
try:
    from c64.drive import (
        Drive1541,
        IECBus,
        ThreadedDrive1541,
        ThreadedIECBus,
        MultiprocessDrive1541,
        MultiprocessIECBus,
        SharedIECState,
        _THREADED_AVAILABLE,
        _MULTIPROCESS_AVAILABLE,
    )
    _DRIVE_AVAILABLE = True
except ImportError:
    Drive1541 = None
    IECBus = None
    ThreadedDrive1541 = None
    ThreadedIECBus = None
    MultiprocessDrive1541 = None
    MultiprocessIECBus = None
    SharedIECState = None
    _THREADED_AVAILABLE = False
    _MULTIPROCESS_AVAILABLE = False

log = logging.getLogger("c64")


class C64DriveMixin:
    """Mixin for 1541 disk drive operations."""

    def attach_drive(self, drive_rom_path: Optional[Path] = None, disk_path: Optional[Path] = None,
                      runner: str = "synchronous") -> bool:
        """Attach a 1541 disk drive to the IEC bus.

        Supports multiple ROM formats:
        - Single 16KB ROM (1541-II style): 1541.rom, 1541-II.251968-03.bin, etc.
        - Two 8KB ROMs (original 1541): 1541-c000.bin + 1541-e000.bin

        Args:
            drive_rom_path: Path to 1541 DOS ROM (default: auto-detect in rom_dir)
            disk_path: Optional D64 disk image to insert
            runner: Drive execution mode:
                    - "synchronous" (default): Cycle-accurate emulation
                    - "threaded": Uses ThreadedIECBus for atomic state
                    - "multiprocess": Drive runs in separate process (bypasses GIL)

        Returns:
            True if drive attached successfully, False otherwise
        """
        # Drive module is optional (not available on Pico)
        if not _DRIVE_AVAILABLE:
            log.warning("Drive module not available - disk drive support disabled")
            return False
        rom_path = drive_rom_path
        rom_path_e000 = None

        if rom_path is None:
            # Try to find 1541 ROM(s) in rom_dir
            # Priority 1: Single 16KB ROM files (most common)
            rom_16k_names = [
                "1541.rom",
                "1541-II.rom",
                "1541-II.251968-03.bin",  # Most compatible 1541-II ROM
                "1541C.251968-01.bin",
                "1541C.251968-02.bin",
                "1541-II.355640-01.bin",
                "dos1541",
                "dos1541.rom",
            ]
            for name in rom_16k_names:
                candidate = self.rom_dir / name
                if candidate.exists():
                    rom_path = candidate
                    break

            # Priority 2: Two 8KB ROM files (original 1541 style)
            if rom_path is None:
                # Look for C000 ROM
                c000_names = [
                    "1541-c000.325302-01.bin",
                    "1541-c000.bin",
                    "1540-c000.325302-01.bin",
                ]
                # Look for E000 ROM (multiple revisions available)
                e000_names = [
                    "1541-e000.901229-05.bin",  # Short-board, most common
                    "1541-e000.901229-03.bin",  # Long-board with autoboot
                    "1541-e000.901229-02.bin",
                    "1541-e000.901229-01.bin",
                    "1541-e000.bin",
                ]

                for c000_name in c000_names:
                    c000_candidate = self.rom_dir / c000_name
                    if c000_candidate.exists():
                        # Found C000 ROM, now look for E000 ROM
                        for e000_name in e000_names:
                            e000_candidate = self.rom_dir / e000_name
                            if e000_candidate.exists():
                                rom_path = c000_candidate
                                rom_path_e000 = e000_candidate
                                break
                        if rom_path_e000 is not None:
                            break

        if rom_path is None or not rom_path.exists():
            log.warning(f"1541 ROM not found in {self.rom_dir}. Drive disabled.")
            log.warning("  Expected: 1541.rom (16KB) or 1541-c000.bin + 1541-e000.bin (8KB each)")
            return False

        # Track the runner mode
        self.drive_runner = runner

        # Validate runner mode is available (threaded/multiprocess not available on MicroPython)
        if runner == "multiprocess" and not _MULTIPROCESS_AVAILABLE:
            log.warning("Multiprocess drive mode not available, falling back to synchronous")
            runner = "synchronous"
            self.drive_runner = runner
        elif runner == "threaded" and not _THREADED_AVAILABLE:
            log.warning("Threaded drive mode not available, falling back to synchronous")
            runner = "synchronous"
            self.drive_runner = runner

        if runner == "multiprocess":
            # Multiprocess mode: Drive runs in separate process (bypasses GIL)
            import os
            import time

            # Create shared memory for IEC state (use PID + time for uniqueness)
            unique_id = f"{os.getpid()}_{int(time.time() * 1000) % 1000000}"
            self._iec_shared_state = SharedIECState(
                name=f"iec_bus_{unique_id}",
                create=True
            )

            # Create multiprocess IEC bus
            self.iec_bus = MultiprocessIECBus(self._iec_shared_state)
            self.iec_bus.connect_c64(self.cia2)
            self.cia2.set_iec_bus(self.iec_bus)

            # Create and start drive subprocess
            self.drive8 = MultiprocessDrive1541(device_number=8)
            self.drive8.start_process(
                rom_path=rom_path,
                rom_path_e000=rom_path_e000,
                disk_path=disk_path,
                shared_state=self._iec_shared_state,
            )

            # Wire up tick synchronization Events
            tick_request, tick_done = self.drive8.get_tick_events()
            self.iec_bus.set_tick_events(tick_request, tick_done)

            self.drive_enabled = True

            # Set up synchronous tick-based execution
            # Similar to threaded mode but with batching to reduce IPC overhead
            self._mp_accumulated_cycles = 0
            self._mp_batch_size = 100  # Cycles per IPC call (balance timing vs overhead)

            def sync_multiprocess(cpu, cycles):
                """Accumulate cycles and sync with drive subprocess."""
                if self.drive8 and self._iec_shared_state:
                    # Update IEC bus state
                    self.iec_bus.update()

                    # Accumulate cycles
                    self._mp_accumulated_cycles += cycles

                    # When batch is full, sync with drive
                    if self._mp_accumulated_cycles >= self._mp_batch_size:
                        batch = self._mp_accumulated_cycles
                        self._mp_accumulated_cycles = 0

                        # Update C64 cycle counter
                        self._iec_shared_state.set_c64_cycles(cpu.cycles_executed)

                        # Wait for drive to catch up to our cycle count
                        tick_request, tick_done = self.drive8.get_tick_events()
                        target_cycles = cpu.cycles_executed

                        # Signal drive and wait for it to process
                        import time
                        max_wait = 0.1  # seconds
                        start = time.time()
                        while time.time() - start < max_wait:
                            tick_request.set()
                            drive_cycles = self._iec_shared_state.get_drive_cycles()
                            if drive_cycles >= target_cycles - 50:
                                break
                            time.sleep(0.00001)  # 10us

                        # Read bus state after drive processed
                        self.iec_bus.atn, self.iec_bus.clk, self.iec_bus.data = \
                            self._iec_shared_state.get_bus_state(is_drive=False)

            self.cpu.post_tick_callback = sync_multiprocess
            log.info(f"1541 drive 8 attached in MULTIPROCESS mode (ROM: {rom_path.name})")
            return True

        elif runner == "threaded":
            # Threaded mode: Uses ThreadedIECBus for atomic state updates
            self.iec_bus = ThreadedIECBus()
            self.iec_bus.connect_c64(self.cia2)
            self.cia2.set_iec_bus(self.iec_bus)

            # Create threaded drive 8
            self.drive8 = ThreadedDrive1541(device_number=8)
        else:
            # Synchronous mode: Cycle-accurate but slower
            self.iec_bus = IECBus()
            self.iec_bus.connect_c64(self.cia2)
            self.cia2.set_iec_bus(self.iec_bus)

            # Create standard drive 8
            self.drive8 = Drive1541(device_number=8)

        # Create a separate CPU for the drive (for threaded/synchronous modes)
        # The 1541 uses a full 6502 (not 6510)
        drive_cpu = CPU(cpu_variant=CPUVariant.NMOS_6502, verbose_cycles=False)
        self.drive8.cpu = drive_cpu

        # Set up drive CPU memory handler
        drive_cpu.ram.memory_handler = self.drive8.memory

        # Load 1541 ROM (supports both 16KB single file and 8KB+8KB split)
        try:
            self.drive8.load_rom(rom_path, rom_path_e000)
        except Exception as e:
            log.error(f"Failed to load 1541 ROM: {e}")
            self.drive8 = None
            self.iec_bus = None
            return False

        # Connect drive to IEC bus
        if runner == "threaded":
            self.drive8.connect_to_threaded_bus(self.iec_bus)
        else:
            self.iec_bus.connect_drive(self.drive8)

        # Insert disk if provided
        if disk_path is not None:
            try:
                self.drive8.insert_disk(disk_path)
            except Exception as e:
                log.error(f"Failed to insert disk: {e}")

        # Reset drive to initialize
        self.drive8.reset()

        self.drive_enabled = True

        if runner == "threaded":
            # Threaded mode: Uses ThreadedIECBus for thread-safe state
            # but still runs drive in lockstep via post_tick_callback
            # The threading benefit is that bus state updates are atomic

            def sync_drive_on_tick_threaded(cpu, cycles):
                """Sync drive CPU and IEC bus after each C64 cycle consumption."""
                if self.drive8 and self.drive8.cpu:
                    # Update IEC bus state so drive sees current C64 outputs
                    self.iec_bus.update()

                    # Run drive for the same number of cycles (1:1 sync)
                    # Call the base class tick() directly since ThreadedDrive1541.tick() is a no-op
                    Drive1541.tick(self.drive8, cycles)

                    # Update IEC bus again so C64 sees drive's response
                    self.iec_bus.update()

            self.cpu.post_tick_callback = sync_drive_on_tick_threaded
            # Note: Not starting drive thread - running synchronously with ThreadedIECBus
            log.info(f"1541 drive 8 attached with ThreadedIECBus (ROM: {rom_path.name})")
        else:
            # Synchronous mode: Set up cycle-accurate IEC synchronization
            # using post_tick_callback. The tick() function is called every
            # time the CPU spends cycles, which is the natural place to
            # synchronize connected hardware.
            #
            # The IEC serial bus is bit-banged and requires tight timing between
            # the C64 and 1541 CPUs. By hooking into tick(), we ensure the drive
            # runs in lockstep with every cycle the C64 spends.

            def sync_drive_on_tick(cpu, cycles):
                """Sync drive CPU and IEC bus after each C64 cycle consumption."""
                if self.drive8 and self.drive8.cpu:
                    # Update IEC bus state so drive sees current C64 outputs
                    self.iec_bus.update()

                    # Run drive for the same number of cycles
                    # The drive's tick() method handles its own cycle budget
                    self.drive8.tick(cycles)

                    # Update IEC bus again so C64 sees drive's response
                    self.iec_bus.update()

            self.cpu.post_tick_callback = sync_drive_on_tick
            log.info(f"1541 drive 8 attached in SYNCHRONOUS mode (ROM: {rom_path.name})")

        return True

    def insert_disk(self, disk_path: Path) -> bool:
        """Insert a D64 disk image into drive 8.

        Args:
            disk_path: Path to D64 disk image

        Returns:
            True if disk inserted successfully
        """
        if not self.drive_enabled or self.drive8 is None:
            log.error("No drive attached. Use --disk or attach_drive() first.")
            return False

        try:
            self.drive8.insert_disk(disk_path)
            return True
        except Exception as e:
            log.error(f"Failed to insert disk: {e}")
            return False

    def eject_disk(self) -> None:
        """Eject the disk from drive 8."""
        if self.drive8 is not None:
            self.drive8.eject_disk()

    def cleanup(self) -> None:
        """Clean up resources (drive subprocess, shared memory, etc.)."""
        # Stop multiprocess drive if running
        if self.drive8 is not None:
            # Check class types carefully - they may be None if drive module unavailable
            if MultiprocessDrive1541 is not None and isinstance(self.drive8, MultiprocessDrive1541):
                self.drive8.stop_process()
            elif ThreadedDrive1541 is not None and isinstance(self.drive8, ThreadedDrive1541):
                self.drive8.stop_thread()

        # Clean up shared memory
        if hasattr(self, '_iec_shared_state') and self._iec_shared_state is not None:
            try:
                self._iec_shared_state.close()
                self._iec_shared_state.unlink()
            except Exception:
                pass
            self._iec_shared_state = None

    def get_drive_pc_region(self) -> str:
        """Determine which memory region the drive's PC is currently in.

        1541 memory map:
        - $0000-$07FF: RAM (2KB)
        - $1800-$1BFF: VIA1
        - $1C00-$1FFF: VIA2
        - $C000-$FFFF: ROM (DOS)

        Returns:
            String describing the region: "RAM", "VIA1", "VIA2", "DOS", or "???"
        """
        if not self.drive8 or not self.drive8.cpu:
            return "???"

        pc = self.drive8.cpu.PC

        if pc < 0x0800:
            return "RAM"
        elif 0x1800 <= pc < 0x1C00:
            return "VIA1"
        elif 0x1C00 <= pc < 0x2000:
            return "VIA2"
        elif pc >= 0xC000:
            return "DOS"
        else:
            return "???"
