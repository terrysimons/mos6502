#!/usr/bin/env python3
"""Benchmark C64 CPU execution speed."""
import argparse
import logging
import time
from pathlib import Path

from c64 import C64, PAL, NTSC, c64_to_ansi_fg, c64_to_ansi_bg, ANSI_RESET
from mos6502 import errors
from mos6502.core import INFINITE_CYCLES

# BASIC ROM address range
BASIC_ROM_START = 0xA000
BASIC_ROM_END = 0xBFFF

# Suppress all logging for clean benchmark output
logging.getLogger().setLevel(logging.CRITICAL)
for logger_name in ['c64', 'c64.vic', 'mos6502', 'mos6502.cpu', 'mos6502.cpu.flags',
                     'mos6502.memory', 'mos6502.memory.RAM', 'mos6502.memory.Byte',
                     'mos6502.memory.Word']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)


def benchmark_c64(rom_dir: str, max_cycles: int, video_mode: str = "pal", verbose_cycles: bool = False) -> tuple[float, int]:
    """Benchmark C64 execution.

    Args:
        rom_dir: Path to ROM directory
        max_cycles: Maximum cycles to execute
        video_mode: "pal" or "ntsc"
        verbose_cycles: Enable per-cycle CPU logging

    Returns:
        (elapsed_seconds, cycles_executed)
    """
    c64 = C64(rom_dir=rom_dir, display_mode="headless", video_mode=video_mode, verbose_cycles=verbose_cycles)
    c64.cpu.reset()

    start_time = time.perf_counter()
    try:
        c64.cpu.execute(cycles=max_cycles)
    except errors.CPUCycleExhaustionError:
        pass

    elapsed = time.perf_counter() - start_time
    return elapsed, c64.cpu.cycles_executed


def benchmark_boot(rom_dir: str, video_mode: str = "pal", debug: bool = False, verbose_cycles: bool = False) -> tuple[float, int, int, str]:
    """Benchmark C64 boot time until BASIC is ready.

    Args:
        rom_dir: Path to ROM directory
        video_mode: "pal" or "ntsc"
        debug: If True, print debug info about PC locations
        verbose_cycles: Enable per-cycle CPU logging

    Returns:
        (elapsed_seconds, cycles_executed, entry_address, screen_capture)
    """
    c64 = C64(rom_dir=rom_dir, display_mode="headless", video_mode=video_mode, verbose_cycles=verbose_cycles)
    c64.cpu.reset()

    # State for detecting when we first enter BASIC ROM
    basic_entry_pc = [0]

    # Set up callback to detect first BASIC ROM entry
    def detect_basic(pc: int) -> None:
        if basic_entry_pc[0] == 0 and BASIC_ROM_START <= pc <= BASIC_ROM_END:
            basic_entry_pc[0] = pc
            raise StopIteration

    c64.cpu.pc_callback = detect_basic

    start_time = time.perf_counter()
    try:
        c64.cpu.execute(cycles=INFINITE_CYCLES)
    except (errors.CPUCycleExhaustionError, StopIteration):
        pass

    boot_cycles = c64.cpu.cycles_executed

    # Run additional cycles to let screen render the BASIC prompt
    extra_cycles = 100_000
    c64.cpu.pc_callback = None  # Disable callback
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


def main():
    parser = argparse.ArgumentParser(description="Benchmark C64 emulator performance")
    C64.args(parser)  # Add C64 arguments (--rom-dir, --video, etc.)
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output for boot detection",
    )
    args = parser.parse_args()

    if not args.rom_dir.exists():
        print(f"Error: ROM directory not found at {args.rom_dir}")
        exit(1)

    timing = PAL if args.video == "pal" else NTSC

    print(f"\nBenchmarking CPU execution speed ({args.video.upper()} mode)...\n")

    # Benchmark different cycle counts
    test_cycles = [100_000, 500_000, 1_000_000, 5_000_000]

    verbose_cycles = getattr(args, 'verbose_cycles', False)

    for cycles in test_cycles:
        elapsed, executed = benchmark_c64(str(args.rom_dir), cycles, args.video, verbose_cycles)
        cycles_per_sec = executed / elapsed
        speed_ratio = cycles_per_sec / timing.cpu_freq
        print(f"{executed:,} cycles: {elapsed:.2f}s ({cycles_per_sec:,.0f} cycles/sec, {speed_ratio:.1%})")

    print()
    print(f"Real C64 ({args.video.upper()}): {timing.cpu_freq:,} cycles/sec")
    print()

    # Boot time benchmark - run until BASIC prompt is ready
    print("Boot benchmark (running until BASIC prompt)...")
    elapsed, executed, entry_pc, screen = benchmark_boot(str(args.rom_dir), args.video, debug=args.debug, verbose_cycles=verbose_cycles)
    cycles_per_sec = executed / elapsed if elapsed > 0 else 0
    speed_ratio = cycles_per_sec / timing.cpu_freq
    print(f"Cycles to boot to BASIC @ ${entry_pc:04X}: {executed:,} ({elapsed:.2f}s, {cycles_per_sec:,.0f} cycles/sec, {speed_ratio:.1%})")

    # Print screen capture
    print()
    print("Screen at BASIC entry:")
    print(screen)


if __name__ == "__main__":
    main()
