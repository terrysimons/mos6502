#!/usr/bin/env python3
"""Benchmark C64 CPU execution speed."""
import argparse
from mos6502.compat import logging
import sys
import time
from mos6502.compat import Path
from mos6502.compat import Optional, Tuple

from c64 import C64, PAL, NTSC, c64_to_ansi_fg, c64_to_ansi_bg, ANSI_RESET
from mos6502 import errors
from mos6502.core import INFINITE_CYCLES
from mos6502.timing import FrameGovernor

# BASIC ROM address range
BASIC_ROM_START = 0xA000
BASIC_ROM_END = 0xBFFF

# Suppress all logging for clean benchmark output
logging.getLogger().setLevel(logging.CRITICAL)
for logger_name in ['c64', 'c64.vic', 'mos6502', 'mos6502.cpu', 'mos6502.cpu.flags',
                     'mos6502.memory', 'mos6502.memory.RAM', 'mos6502.memory.Byte',
                     'mos6502.memory.Word', 'iec_bus', 'drive1541', 'via6522']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)


def benchmark_c64(rom_dir: str, max_cycles: int, video_chip: str = "6569", verbose_cycles: bool = False, throttle: bool = False) -> Tuple[float, int]:
    """Benchmark C64 execution.

    Args:
        rom_dir: Path to ROM directory
        max_cycles: Maximum cycles to execute
        video_chip: VIC-II chip variant ("6569", "6567R8", "6567R56A", "PAL", "NTSC")
        verbose_cycles: Enable per-cycle CPU logging
        throttle: If True, throttle to real-time speed

    Returns:
        (elapsed_seconds, cycles_executed)
    """
    c64 = C64(rom_dir=rom_dir, display_mode="headless", video_chip=video_chip, verbose_cycles=verbose_cycles)
    c64.cpu.reset()

    # Record start time for speed stats
    c64._execution_start_time = time.perf_counter()

    if throttle:
        # Use frame governor to throttle to real-time
        governor = FrameGovernor(
            fps=c64.video_timing.refresh_hz,
            enabled=True
        )
        cycles_per_frame = c64.video_timing.cycles_per_frame
        cycles_remaining = max_cycles

        while cycles_remaining > 0:
            cycles_this_frame = min(cycles_per_frame, cycles_remaining)
            try:
                c64.cpu.execute(cycles=cycles_this_frame)
            except errors.CPUCycleExhaustionError:
                pass
            cycles_remaining -= cycles_this_frame
            governor.throttle()
    else:
        # Run at maximum speed
        try:
            c64.cpu.execute(cycles=max_cycles)
        except errors.CPUCycleExhaustionError:
            pass

    # Record end time and use get_speed_stats()
    c64._execution_end_time = time.perf_counter()
    stats = c64.get_speed_stats()

    return stats["elapsed_seconds"], stats["cycles_executed"]


def benchmark_boot(rom_dir: str, video_chip: str = "6569", debug: bool = False, verbose_cycles: bool = False, throttle: bool = False) -> Tuple[float, int, int, str]:
    """Benchmark C64 boot time until BASIC is ready.

    Args:
        rom_dir: Path to ROM directory
        video_chip: VIC-II chip variant ("6569", "6567R8", "6567R56A", "PAL", "NTSC")
        debug: If True, print debug info about PC locations
        verbose_cycles: Enable per-cycle CPU logging
        throttle: If True, throttle to real-time speed

    Returns:
        (elapsed_seconds, cycles_executed, entry_address, screen_capture)
    """
    c64 = C64(rom_dir=rom_dir, display_mode="headless", video_chip=video_chip, verbose_cycles=verbose_cycles)
    c64.cpu.reset()

    # State for detecting when we first enter BASIC ROM
    basic_entry_pc = [0]
    stop_requested = [False]

    # Set up callback to detect first BASIC ROM entry
    # For throttled mode, we use a flag; for non-throttled, we raise StopIteration
    def detect_basic_throttled(pc: int) -> None:
        if basic_entry_pc[0] == 0 and BASIC_ROM_START <= pc <= BASIC_ROM_END:
            basic_entry_pc[0] = pc
            stop_requested[0] = True

    def detect_basic_immediate(pc: int) -> None:
        if basic_entry_pc[0] == 0 and BASIC_ROM_START <= pc <= BASIC_ROM_END:
            basic_entry_pc[0] = pc
            raise StopIteration

    start_time = time.perf_counter()

    if throttle:
        # Use frame governor to throttle to real-time
        c64.cpu.pc_callback = detect_basic_throttled
        governor = FrameGovernor(
            fps=c64.video_timing.refresh_hz,
            enabled=True
        )
        cycles_per_frame = c64.video_timing.cycles_per_frame

        # Run until BASIC entry detected
        while not stop_requested[0]:
            try:
                c64.cpu.execute(cycles=cycles_per_frame)
            except errors.CPUCycleExhaustionError:
                pass
            governor.throttle()
    else:
        # Run at maximum speed until BASIC entry
        c64.cpu.pc_callback = detect_basic_immediate
        try:
            c64.cpu.execute(cycles=INFINITE_CYCLES)
        except (errors.CPUCycleExhaustionError, StopIteration):
            pass

    boot_cycles = c64.cpu.cycles_executed

    # Run additional cycles to let screen render the BASIC prompt
    extra_cycles = 100_000
    c64.cpu.pc_callback = None  # Disable callback

    if throttle:
        cycles_remaining = extra_cycles
        while cycles_remaining > 0:
            cycles_this_frame = min(cycles_per_frame, cycles_remaining)
            try:
                c64.cpu.execute(cycles=cycles_this_frame)
            except errors.CPUCycleExhaustionError:
                pass
            cycles_remaining -= cycles_this_frame
            governor.throttle()
    else:
        try:
            c64.cpu.execute(cycles=extra_cycles)
        except errors.CPUCycleExhaustionError:
            pass

    elapsed = time.perf_counter() - start_time

    # Capture screen state
    screen_capture = capture_screen(c64)

    return elapsed, boot_cycles, basic_entry_pc[0], screen_capture


def capture_screen(c64: C64) -> str:
    """Capture the C64 screen as a colorized text string with border (44x29)."""
    screen_start = 0x0400
    color_ram_start = 0xD800
    cols = 40
    rows = 25

    # Get border color from VIC register $D020
    border_color = int(c64.cpu.ram[0xD020]) & 0x0F
    border_ansi = c64_to_ansi_bg(border_color)

    # Get background color from VIC register $D021
    bg_color = int(c64.cpu.ram[0xD021]) & 0x0F
    bg_ansi = c64_to_ansi_bg(bg_color)

    lines = []

    # Top border (2 rows)
    lines.append(border_ansi + " " * 44 + ANSI_RESET)
    lines.append(border_ansi + " " * 44 + ANSI_RESET)

    # Screen rows with left/right borders
    for row in range(rows):
        line = border_ansi + "  " + ANSI_RESET + bg_ansi  # Left border + bg
        for col in range(cols):
            screen_addr = screen_start + (row * cols) + col
            color_addr = color_ram_start + (row * cols) + col

            petscii = int(c64.cpu.ram[screen_addr])
            fg_color = int(c64.cpu.ram[color_addr]) & 0x0F

            char = c64.petscii_to_ascii(petscii)
            line += c64_to_ansi_fg(fg_color) + char

        line += ANSI_RESET + border_ansi + "  " + ANSI_RESET  # Right border
        lines.append(line)

    # Bottom border (2 rows)
    lines.append(border_ansi + " " * 44 + ANSI_RESET)
    lines.append(border_ansi + " " * 44 + ANSI_RESET)

    return "\n".join(lines)


def benchmark_disk_load(
    rom_dir: str,
    disk_path: Path,
    video_chip: str = "6569",
    drive_rom: Optional[Path] = None,
    sync_drive: bool = False,
    throttle: bool = False
) -> Tuple[float, int, str]:
    """Benchmark loading from disk (LOAD"*",8,1 then RUN).

    Args:
        rom_dir: Path to ROM directory
        disk_path: Path to D64 disk image
        video_chip: VIC-II chip variant
        drive_rom: Optional path to 1541 ROM
        sync_drive: Use synchronous IEC bus (vs threaded)
        throttle: If True, throttle to real-time speed

    Returns:
        (elapsed_seconds, cycles_executed, screen_capture)
    """
    c64 = C64(rom_dir=rom_dir, display_mode="headless", video_chip=video_chip)
    c64.cpu.reset()

    # Attach drive with disk
    use_threaded = not sync_drive
    if not c64.attach_drive(drive_rom_path=drive_rom, disk_path=disk_path, threaded=use_threaded):
        raise RuntimeError("Failed to attach drive - check ROM path")

    # First boot to BASIC
    print("Booting to BASIC...", flush=True)
    def detect_basic_immediate(pc: int) -> None:
        if BASIC_ROM_START <= pc <= BASIC_ROM_END:
            raise StopIteration

    c64.cpu.pc_callback = detect_basic_immediate

    # Boot to BASIC
    if throttle:
        stop_requested = [False]
        def detect_basic_throttled(pc: int) -> None:
            if BASIC_ROM_START <= pc <= BASIC_ROM_END:
                stop_requested[0] = True
        c64.cpu.pc_callback = detect_basic_throttled
        governor = FrameGovernor(fps=c64.video_timing.refresh_hz, enabled=True)
        cycles_per_frame = c64.video_timing.cycles_per_frame
        while not stop_requested[0]:
            try:
                c64.cpu.execute(cycles=cycles_per_frame)
            except errors.CPUCycleExhaustionError:
                pass
            governor.throttle()
    else:
        try:
            c64.cpu.execute(cycles=INFINITE_CYCLES)
        except (errors.CPUCycleExhaustionError, StopIteration):
            pass

    print(f"Booted after {c64.cpu.cycles_executed:,} cycles", flush=True)
    c64.cpu.pc_callback = None

    # Let screen render and wait for KERNAL to be ready for input
    print("Letting screen settle...", flush=True)
    try:
        c64.cpu.execute(cycles=100_000)
    except errors.CPUCycleExhaustionError:
        pass

    # Inject LOAD"*",8 command (max 10 chars in keyboard buffer)
    # We'll inject LOAD"*",8 first, then RUN after load completes
    print("Injecting LOAD command...", flush=True)
    c64.inject_keyboard_buffer('LOAD"*",8\r')

    # Now benchmark the actual disk load
    print("Starting disk load benchmark...", flush=True)
    start_time = time.perf_counter()
    start_cycles = c64.cpu.cycles_executed

    # Run for a fixed number of cycles to let the load complete
    # A typical load takes several million cycles
    load_cycles = 50_000_000  # ~50 seconds of C64 time at 1MHz

    if throttle:
        governor = FrameGovernor(fps=c64.video_timing.refresh_hz, enabled=True)
        cycles_per_frame = c64.video_timing.cycles_per_frame
        cycles_remaining = load_cycles
        while cycles_remaining > 0:
            cycles_this_frame = min(cycles_per_frame, cycles_remaining)
            try:
                c64.cpu.execute(cycles=cycles_this_frame)
            except errors.CPUCycleExhaustionError:
                pass
            cycles_remaining -= cycles_this_frame
            governor.throttle()
    else:
        try:
            c64.cpu.execute(cycles=load_cycles)
        except errors.CPUCycleExhaustionError:
            pass

    print("Load complete", flush=True)
    elapsed = time.perf_counter() - start_time
    cycles_executed = c64.cpu.cycles_executed - start_cycles

    # Capture screen
    screen_capture = capture_screen(c64)

    return elapsed, cycles_executed, screen_capture


def main():
    parser = argparse.ArgumentParser(description="Benchmark C64 emulator performance")
    C64.args(parser)  # Add C64 arguments (--rom-dir, --video, --disk, --sync-drive, etc.)
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output for boot detection",
    )
    args = parser.parse_args()

    if not args.rom_dir.exists():
        print(f"Error: ROM directory not found at {args.rom_dir}")
        exit(1)

    # Get video chip from args (C64.args adds --video-chip which becomes args.video_chip)
    video_chip = args.video_chip

    # Determine timing based on video chip
    if video_chip.upper() in ("6569", "PAL"):
        timing = PAL
    else:
        timing = NTSC

    throttle = args.throttle
    throttle_status = "enabled" if throttle else "disabled"
    region = "PAL" if timing.chip_name == "6569" else "NTSC"

    # Detect Python implementation
    impl = sys.implementation.name.capitalize()  # "Cpython" or "Pypy"
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    # Check if disk benchmark mode
    disk_path = getattr(args, 'disk', None)
    sync_drive = getattr(args, 'sync_drive', False)
    drive_rom = getattr(args, 'drive_rom', None)

    if disk_path:
        # Disk load benchmark mode
        drive_mode = "synchronous" if sync_drive else "threaded"
        print(f"\nDisk Load Benchmark ({impl} {py_version}, VIC-II {timing.chip_name} {region}, {drive_mode} drive, throttle {throttle_status})")
        print(f"Disk: {disk_path}")
        print()

        elapsed, cycles_executed, screen = benchmark_disk_load(
            rom_dir=str(args.rom_dir),
            disk_path=disk_path,
            video_chip=video_chip,
            drive_rom=drive_rom,
            sync_drive=sync_drive,
            throttle=throttle
        )

        cycles_per_sec = cycles_executed / elapsed if elapsed > 0 else 0
        speed_ratio = cycles_per_sec / timing.cpu_freq

        print(f"Executed {cycles_executed:,} cycles in {elapsed:.2f}s")
        print(f"Speed: {cycles_per_sec:,.0f} cycles/sec ({speed_ratio:.1%} of real C64)")
        print()
        print("Screen after load:")
        print(screen)
        return

    # Standard CPU benchmark (no disk)
    print(f"\nBenchmarking C64 CPU execution speed ({impl} {py_version}, VIC-II {timing.chip_name} {region}, throttle {throttle_status})...\n")

    # Benchmark different cycle counts
    test_cycles = [
        100_000, 500_000, 1_000_000, 5_000_000,
        10_000_000, 20_000_000, 50_000_000,
        100_000_000, 200_000_000, 400_000_000, 800_000_000, 1_600_000_000,
    ]

    verbose_cycles = getattr(args, 'verbose_cycles', False)

    for cycles in test_cycles:
        elapsed, executed = benchmark_c64(str(args.rom_dir), cycles, video_chip, verbose_cycles, throttle=throttle)
        cycles_per_sec = executed / elapsed
        speed_ratio = cycles_per_sec / timing.cpu_freq
        print(f"{executed:,} cycles: {elapsed:.2f}s ({cycles_per_sec:,.0f} cycles/sec, {speed_ratio:.1%})")

    print()
    print(f"Real C64 ({timing.chip_name}): {timing.cpu_freq:,} cycles/sec")
    print()

    # Boot time benchmark - run until BASIC prompt is ready
    print("Boot benchmark (running until BASIC prompt)...")
    elapsed, executed, entry_pc, screen = benchmark_boot(str(args.rom_dir), video_chip, debug=args.debug, verbose_cycles=verbose_cycles, throttle=throttle)
    cycles_per_sec = executed / elapsed if elapsed > 0 else 0
    speed_ratio = cycles_per_sec / timing.cpu_freq
    print(f"Cycles to boot to BASIC @ ${entry_pc:04X}: {executed:,} ({elapsed:.2f}s, {cycles_per_sec:,.0f} cycles/sec, {speed_ratio:.1%})")

    # Print screen capture
    print()
    print("Screen at BASIC entry:")
    print(screen)


if __name__ == "__main__":
    main()
