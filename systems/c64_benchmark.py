#!/usr/bin/env python3
"""Benchmark C64 CPU execution speed."""
import logging
import time
from pathlib import Path

from c64 import C64
from mos6502 import errors

# Suppress all logging for clean benchmark output
logging.getLogger().setLevel(logging.CRITICAL)
for logger_name in ['c64', 'c64.vic', 'mos6502', 'mos6502.cpu', 'mos6502.cpu.flags',
                     'mos6502.memory', 'mos6502.memory.RAM', 'mos6502.memory.Byte',
                     'mos6502.memory.Word']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)


def benchmark_c64(rom_dir: str, max_cycles: int) -> tuple[float, int]:
    """Benchmark C64 execution.

    Returns:
        (elapsed_seconds, cycles_executed)
    """
    c64 = C64(rom_dir=rom_dir, display_mode="none")
    c64.cpu.reset()  # Clear RAM
    c64.load_roms()  # Load ROMs and initialize PC from reset vector

    start_time = time.perf_counter()
    try:
        c64.run(max_cycles=max_cycles)
    except (errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        pass

    elapsed = time.perf_counter() - start_time
    return elapsed, c64.cpu.cycles_executed


if __name__ == "__main__":
    rom_dir = Path(__file__).parent / "roms"

    if not rom_dir.exists():
        print(f"Error: ROM directory not found at {rom_dir}")
        exit(1)

    print("\nBenchmarking CPU execution speed...\n")

    # Benchmark different cycle counts
    test_cycles = [100_000, 500_000, 1_000_000, 5_000_000]

    for cycles in test_cycles:
        elapsed, executed = benchmark_c64(str(rom_dir), cycles)
        cycles_per_sec = executed / elapsed
        print(f"{executed:,} cycles: {elapsed:.2f}s ({cycles_per_sec:,.0f} cycles/sec)")

    print()
    print("Real C64: 1,022,727 cycles/sec (PAL) or 985,248 cycles/sec (NTSC)")
    print()

    # Estimate boot time
    kernal_cycles = 2_500_000  # Approximate cycles to boot KERNAL
    elapsed, executed = benchmark_c64(str(rom_dir), kernal_cycles)
    print(f"Estimated time to boot C64 KERNAL (~{kernal_cycles/1_000_000:.1f}M cycles): {elapsed:.1f}s")
