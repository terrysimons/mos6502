"""C64 Runner Mixin.

Mixin for execution (run, run_repl).
"""

from mos6502.compat import logging
from mos6502.core import INFINITE_CYCLES
from mos6502.memory import Byte, Word
from c64.memory import (
    BASIC_ROM_START,
    BASIC_ROM_END,
    KERNAL_ROM_START,
    KERNAL_ROM_END,
)

log = logging.getLogger("c64")


class C64RunnerMixin:
    """Mixin for execution (run, run_repl)."""

    def basic_ready(self) -> bool:
        """Return True if BASIC input loop has been reached."""
        return self._basic_ready

    @property

    def kernal_waiting_for_input(self) -> bool:
        """Return True if KERNAL is waiting for keyboard input.

        The KERNAL keyboard input loop is at $E5CF-$E5D6.
        When PC is in this range, the system is waiting for user input.
        """
        return self._kernal_waiting_for_input

    def _pc_callback(self, new_pc: int) -> None:
        """PC change callback - detects when BASIC is ready or KERNAL is waiting for input.

        This is called by the CPU every time PC changes.
        """
        # Check if PC is in BASIC ROM range
        if BASIC_ROM_START <= new_pc <= BASIC_ROM_END:
            self._basic_ready = True
            if self._stop_on_basic:
                raise StopIteration("BASIC is ready")

        # Check if PC is in KERNAL keyboard input loop ($E5CF-$E5D6)
        # This is the GETIN routine that waits for keyboard input
        if 0xE5CF <= new_pc <= 0xE5D6:
            self._kernal_waiting_for_input = True
            if self._stop_on_kernal_input:
                raise StopIteration("KERNAL waiting for input")
        else:
            # Reset when PC leaves the input loop
            self._kernal_waiting_for_input = False

    def _setup_pc_callback(
        self, stop_on_basic: bool = False, stop_on_kernal_input: bool = False
    ) -> None:
        """Set up the PC callback for BASIC/KERNAL detection.

        Arguments:
            stop_on_basic: If True, raise StopIteration when BASIC is ready
            stop_on_kernal_input: If True, raise StopIteration when KERNAL is waiting for input
        """
        self._stop_on_basic = stop_on_basic
        self._stop_on_kernal_input = stop_on_kernal_input
        self.cpu.pc_callback = self._pc_callback

    def _clear_pc_callback(self) -> None:
        """Remove the PC callback and reset detection flags."""
        self.cpu.pc_callback = None
        self._stop_on_basic = False
        self._stop_on_kernal_input = False

    def _check_pc_region(self) -> None:
        """Monitor PC and enable detailed logging when entering BASIC or KERNAL ROM."""
        region = self.get_pc_region()

        # Track important PC locations
        pc = self.cpu.PC

        # Log when we enter BASIC ROM
        if BASIC_ROM_START <= pc <= BASIC_ROM_END and not hasattr(self, '_logged_basic_entry'):
            self._logged_basic_entry = True
            self._basic_ready = True
            log.info(f"*** ENTERED BASIC ROM at ${pc:04X} ***")

        # Log when stuck at KERNAL idle loop ($E5CF-$E5D2)
        if 0xE5CF <= pc <= 0xE5D2:
            if not hasattr(self, '_e5cf_count'):
                self._e5cf_count = 0
            self._e5cf_count += 1
            if self._e5cf_count % 10000 == 0:
                log.info(f"*** Still in KERNAL idle loop at ${pc:04X} (count={self._e5cf_count}) ***")

        # Enable logging when entering KERNAL for the first time (for debugging)
        if DEBUG_KERNAL and region == "KERNAL" and self.last_pc_region != "KERNAL":
            logging.getLogger("mos6502").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.cpu").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.cpu.flags").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory.RAM").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory.Byte").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory.Word").setLevel(logging.DEBUG)
            log.info(f"*** ENTERING KERNAL ROM at ${self.cpu.PC:04X} - Enabling detailed CPU logging ***")

        # Enable logging when entering BASIC for the first time
        if DEBUG_BASIC and region == "BASIC" and not self.basic_logging_enabled:
            self.basic_logging_enabled = True
            logging.getLogger("mos6502").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.cpu").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.cpu.flags").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory.RAM").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory.Byte").setLevel(logging.DEBUG)
            logging.getLogger("mos6502.memory.Word").setLevel(logging.DEBUG)
            log.info(f"*** ENTERING BASIC ROM at ${self.cpu.PC:04X} - Enabling detailed CPU logging ***")

        self.last_pc_region = region

    def run(
        self,
        max_cycles: int = INFINITE_CYCLES,
        stop_on_basic: bool = False,
        stop_on_kernal_input: bool = False,
        throttle: bool = True,
        stop_on_illegal_instruction: bool = False,
    ) -> None:
        """Run the C64 emulator.

        Arguments:
            max_cycles: Maximum number of CPU cycles to execute
                       (default: INFINITE_CYCLES for continuous execution)
            stop_on_basic: If True, stop execution when BASIC prompt is ready
            stop_on_kernal_input: If True, stop execution when KERNAL is waiting for keyboard input
            throttle: If True, throttle emulation to real-time speed (default: True)
                     Use --no-throttle for benchmarks to run at maximum speed
            stop_on_illegal_instruction: If True, dump crash report on illegal instruction
        """
        # Store for use in error handler
        self._stop_on_illegal_instruction = stop_on_illegal_instruction
        log.info(f"Starting execution at PC=${self.cpu.PC:04X}")
        log.info("Press Ctrl+C to stop")

        # Set up PC callback for BASIC/KERNAL detection if requested
        if stop_on_basic or stop_on_kernal_input:
            self._setup_pc_callback(
                stop_on_basic=stop_on_basic, stop_on_kernal_input=stop_on_kernal_input
            )

        try:
            # Execute with cycle counter display
            # Use threading for concurrent execution - multiprocessing has pickling issues
            # with closures and the GIL doesn't affect us since we're I/O bound on display
            # The frame_complete uses multiprocessing.Event for cross-process safety
            import threading
            import time
            import sys as _sys
            from mos6502.timing import FrameGovernor

            # Record execution start time for speedup calculation
            self._execution_start_time = time.perf_counter()

            # Check if we're in a TTY (terminal) for interactive display
            is_tty = _sys.stdout.isatty()

            # All modes: CPU in background thread, display + input in main thread
            # This ensures responsive input handling regardless of display mode
            pygame_mode = self.display_mode == "pygame" and self.pygame_available

            cpu_done = threading.Event()
            cpu_error = None
            stop_cpu = threading.Event()

            # Create frame governor for real-time throttling
            governor = FrameGovernor(
                fps=self.video_timing.refresh_hz,
                enabled=throttle
            )
            cycles_per_frame = self.video_timing.cycles_per_frame

            def cpu_thread() -> None:
                nonlocal cpu_error
                try:
                    # Execute frame-by-frame with optional throttling
                    # This allows the governor to maintain real-time speed
                    cycles_remaining = max_cycles
                    while cycles_remaining > 0 and not stop_cpu.is_set():
                        # Execute one frame's worth of cycles
                        cycles_this_frame = min(cycles_per_frame, cycles_remaining)
                        try:
                            self.cpu.execute(cycles=cycles_this_frame)
                        except errors.CPUCycleExhaustionError:
                            pass  # Normal - frame completed
                        cycles_remaining -= cycles_this_frame

                        # Throttle to real-time (governor.throttle() returns
                        # immediately if throttling is disabled)
                        governor.throttle()
                except Exception as e:
                    cpu_error = e
                finally:
                    cpu_done.set()

            # Start CPU thread
            cpu_thread_obj = threading.Thread(target=cpu_thread, daemon=True)
            cpu_thread_obj.start()

            # Set up terminal input (works for all modes)
            terminal_input_available = False
            old_settings = None
            try:
                import select
                import termios
                import tty
                if _sys.stdin.isatty():
                    old_settings = termios.tcgetattr(_sys.stdin)
                    tty.setcbreak(_sys.stdin.fileno())
                    terminal_input_available = True
            except ImportError:
                pass  # Terminal input not available (Windows, etc.)

            # Main thread handles display + input
            try:
                last_terminal_render = time.perf_counter()
                TERMINAL_RENDER_INTERVAL = 0.1  # 100ms between terminal renders

                while not cpu_done.is_set():
                    # Check stop conditions
                    if stop_on_basic and self.basic_ready:
                        break
                    if stop_on_kernal_input and self.kernal_waiting_for_input:
                        break

                    # Handle terminal keyboard input (all modes)
                    if terminal_input_available:
                        import select
                        if select.select([_sys.stdin], [], [], 0)[0]:
                            char = _sys.stdin.read(1)
                            if self._handle_terminal_input(char):
                                break  # Ctrl+C pressed

                    # Process any pending key releases (non-blocking)
                    self._process_pending_key_releases()

                    # Pump pygame events every iteration (outside of draw loop)
                    if pygame_mode:
                        self._pump_pygame_events()
                        self._process_pygame_key_buffer()

                    # Mode-specific rendering
                    # Use half frame time as timeout - ensures we check twice per frame
                    # even if CPU is slow, while not wasting CPU on excessive polling
                    frame_timeout = 0.5 / self.video_timing.refresh_hz  # ~10ms PAL, ~8ms NTSC

                    if pygame_mode:
                        # Render when VIC has a new frame ready (both pygame and terminal)
                        if self.vic.frame_complete.is_set():
                            self._render_pygame()
                        else:
                            # Tiny sleep to prevent busy-spinning when no frame ready
                            time.sleep(0.001)  # 1ms
                    else:
                        # Terminal/headless: render when VIC has a new frame ready
                        if self.vic.frame_complete.is_set():
                            self.vic.frame_complete.clear()
                            self._check_pc_region()
                            self._render_terminal()
                        else:
                            time.sleep(0.001)  # 1ms

            finally:
                # Signal CPU thread to stop and wait for it
                stop_cpu.set()
                cpu_done.set()
                cpu_thread_obj.join(timeout=0.5)

                # Stop drive thread if running in threaded mode
                if self.drive_enabled and getattr(self, 'drive_threaded', False):
                    if self.drive8 is not None and hasattr(self.drive8, 'stop_thread'):
                        self.drive8.stop_thread()

                # Restore terminal settings if we changed them
                if old_settings is not None:
                    import termios
                    termios.tcsetattr(_sys.stdin, termios.TCSADRAIN, old_settings)

                # Cleanup pygame if used
                if pygame_mode:
                    try:
                        import pygame
                        pygame.quit()
                    except Exception:
                        pass

                # Log governor stats if throttling was enabled
                if throttle:
                    stats = governor.stats()
                    log.info(f"Governor stats: {stats['frame_count']} frames, "
                            f"avg sleep {stats['avg_sleep_per_frame']*1000:.1f}ms/frame, "
                            f"dropped {stats['frames_dropped']}")

            # Re-raise CPU thread exception if any
            if cpu_error:
                raise cpu_error

        except StopIteration as e:
            # PC callback requested stop (e.g., BASIC is ready or KERNAL waiting for input)
            log.info(f"Execution stopped at PC=${self.cpu.PC:04X} ({e})")
        except errors.CPUCycleExhaustionError as e:
            log.info(f"CPU execution completed: {e}")
        except errors.CPUBreakError as e:
            log.info(f"Program terminated (BRK at PC=${self.cpu.PC:04X})")
        except (KeyboardInterrupt, errors.QuitRequestError) as e:
            if isinstance(e, errors.QuitRequestError):
                log.info(f"\nExecution stopped: {e}")
            else:
                log.info("\nExecution interrupted by user")
            log.info(f"PC=${self.cpu.PC:04X}, Cycles={self.cpu.cycles_executed}")
        except (errors.IllegalCPUInstructionError, RuntimeError) as e:
            # Check if we should dump crash report and stop (vs raising)
            if getattr(self, '_stop_on_illegal_instruction', False) and isinstance(e, errors.IllegalCPUInstructionError):
                self.dump_crash_report(exception=e)
                # Don't re-raise - just stop execution cleanly
            else:
                log.exception(f"Execution error at PC=${self.cpu.PC:04X}")
                # Show context around error
                try:
                    pc_val = int(self.cpu.PC)
                    self.show_disassembly(max(0, pc_val - 10), num_instructions=20)
                    self.dump_memory(max(0, pc_val - 16), min(0xFFFF, pc_val + 16))
                except (IndexError, KeyError, ValueError):
                    log.exception("Could not display context")
                raise
        finally:
            # Record execution end time for speedup calculation
            import time
            self._execution_end_time = time.perf_counter()
            # Clean up PC callback
            self._clear_pc_callback()
            # Show screen buffer on termination
            self.show_screen()
            # Clean up drive subprocess if running
            self.cleanup()

    def run_repl(self, max_cycles: int = INFINITE_CYCLES) -> None:
        """Run the C64 in REPL mode with terminal input.

        This mode renders the C64 screen to the terminal and accepts
        keyboard input, converting ASCII to C64 key presses.

        Note: REPL mode requires Unix-like terminal support (termios, tty).
        It is not available on Windows.

        Arguments:
            max_cycles: Maximum cycles to run (default: infinite)
        """
        import sys as _sys
        import threading
        import time

        try:
            import select
            import termios
            import tty
        except ImportError:
            log.error("REPL mode requires Unix-like terminal support (termios, tty).")
            log.error("This mode is not available on Windows. Use --display terminal instead.")
            return

        if not _sys.stdin.isatty():
            log.error("REPL mode requires an interactive terminal (stdin must be a TTY).")
            return

        # Save terminal settings
        old_settings = termios.tcgetattr(_sys.stdin)

        # Shared state between threads
        stop_event = threading.Event()
        cpu_error = None

        def cpu_thread():
            """Run CPU in background thread."""
            nonlocal cpu_error
            try:
                self.cpu.execute(cycles=max_cycles)
            except errors.CPUCycleExhaustionError:
                pass  # Normal termination when max_cycles reached
            except Exception as e:
                cpu_error = e
                log.error(f"CPU thread error: {e}")
            finally:
                stop_event.set()

        try:
            # Put terminal in cbreak mode (character-at-a-time, no echo)
            tty.setcbreak(_sys.stdin.fileno())

            # Record execution start time for speedup calculation
            self._execution_start_time = time.perf_counter()

            # Start CPU in background thread
            cpu_thread_obj = threading.Thread(target=cpu_thread, daemon=True)
            cpu_thread_obj.start()

            # Main loop: handle input and render
            # Limit render rate to match video timing (PAL ~50Hz, NTSC ~60Hz)
            last_render = 0
            render_interval = self.video_timing.render_interval

            while not stop_event.is_set():
                # Check for input (non-blocking with short timeout)
                if select.select([_sys.stdin], [], [], 0.01)[0]:
                    char = _sys.stdin.read(1)
                    if self._handle_terminal_input(char):
                        break  # Ctrl+C pressed

                # Process any pending key releases
                self._process_pending_key_releases()

                # Render at limited rate to avoid terminal buffer overflow
                now = time.time()
                if now - last_render >= render_interval:
                    self.dirty_tracker.force_redraw()
                    self._render_terminal_repl()
                    last_render = now

        except (KeyboardInterrupt, errors.QuitRequestError):
            pass
        finally:
            # Record execution end time for speedup calculation
            self._execution_end_time = time.perf_counter()

            stop_event.set()
            # Wait for CPU thread to finish
            cpu_thread_obj.join(timeout=0.5)

            # Restore terminal settings
            termios.tcsetattr(_sys.stdin, termios.TCSADRAIN, old_settings)

            # Clear screen and show final state
            _sys.stdout.write("\033[2J\033[H")
            _sys.stdout.flush()
            self.show_screen()

            # Clean up drive subprocess if running
            self.cleanup()

            # Re-raise CPU error if any
            if cpu_error:
                raise cpu_error
