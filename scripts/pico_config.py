#!/usr/bin/env python3
"""Shared configuration for Pico build scripts.

This module contains common settings used by both:
- build_pico.py (builds .mpy files for mpremote deployment)
- build_firmware.py (builds frozen MicroPython firmware)
"""

from pathlib import Path

# Project root
ROOT = Path(__file__).parent.parent

# Source directories
MOS6502_SRC = ROOT / "mos6502"
C64_SRC = ROOT / "systems" / "c64"

# Output directories
DIST_PICO = ROOT / "dist" / "pico"
DIST_FIRMWARE = ROOT / "dist" / "firmware"

# Default ROM directory
ROM_DIR = ROOT / "systems" / "roms"

# Main script for Pico
PICO_MAIN = ROOT / "scripts" / "pico_main.py"

# mpy-cross optimization level
MPY_OPT = "-O3"  # Strip docstrings, assertions, and line numbers

# Pico 2 board variants
# For RISC-V, we use the same board but set PICO_PLATFORM
PICO2_BOARDS = {
    "arm": {"board": "RPI_PICO2", "platform": None},
    "riscv": {"board": "RPI_PICO2", "platform": "rp2350-riscv"},
}

# Files/patterns to exclude from Pico build (keep in source, skip for deployment)
PICO_EXCLUDE = [
    # Threaded/multiprocess drive code - not needed on Pico (uses synchronous)
    "drive/threaded_drive.py",
    "drive/threaded_iec_bus.py",
    "drive/multiprocess_drive.py",
    "drive/multiprocess_iec_bus.py",
    # Benchmark module - not useful on Pico
    "benchmark.py",
    # Unimplemented cartridge types - only needed for test cart generation
    # Keep implemented: type_00, type_01, type_03, type_04, type_05, type_10, type_13, type_15, type_17, type_19
    "cartridges/type_02_",
    "cartridges/type_06_",
    "cartridges/type_07_",
    "cartridges/type_08_",
    "cartridges/type_09_",
    "cartridges/type_11_",
    "cartridges/type_12_",
    "cartridges/type_14_",
    "cartridges/type_16_",
    "cartridges/type_18_",
    "cartridges/type_20_",
    "cartridges/type_21_",
    "cartridges/type_22_",
    "cartridges/type_23_",
    "cartridges/type_24_",
    "cartridges/type_25_",
    "cartridges/type_26_",
    "cartridges/type_27_",
    "cartridges/type_28_",
    "cartridges/type_29_",
    "cartridges/type_30_",
    "cartridges/type_31_",
    "cartridges/type_32_",
    "cartridges/type_33_",
    "cartridges/type_34_",
    "cartridges/type_35_",
    "cartridges/type_36_",
    "cartridges/type_37_",
    "cartridges/type_38_",
    "cartridges/type_39_",
    "cartridges/type_40_",
    "cartridges/type_41_",
    "cartridges/type_42_",
    "cartridges/type_43_",
    "cartridges/type_44_",
    "cartridges/type_45_",
    "cartridges/type_46_",
    "cartridges/type_47_",
    "cartridges/type_48_",
    "cartridges/type_49_",
    "cartridges/type_50_",
    "cartridges/type_51_",
    "cartridges/type_52_",
    "cartridges/type_53_",
    "cartridges/type_54_",
    "cartridges/type_55_",
    "cartridges/type_56_",
    "cartridges/type_57_",
    "cartridges/type_58_",
    "cartridges/type_59_",
    "cartridges/type_60_",
    "cartridges/type_61_",
    "cartridges/type_62_",
    "cartridges/type_63_",
    "cartridges/type_64_",
    "cartridges/type_65_",
    "cartridges/type_66_",
    "cartridges/type_67_",
    "cartridges/type_68_",
    "cartridges/type_69_",
    "cartridges/type_70_",
    "cartridges/type_71_",
    "cartridges/type_72_",
    "cartridges/type_73_",
    "cartridges/type_74_",
    "cartridges/type_75_",
    "cartridges/type_76_",
    "cartridges/type_77_",
    "cartridges/type_78_",
    "cartridges/type_79_",
    "cartridges/type_80_",
    "cartridges/type_81_",
    "cartridges/type_82_",
    "cartridges/type_83_",
    "cartridges/type_84_",
    "cartridges/type_85_",
    # Also exclude rom_builder - only needed for test cart generation
    "cartridges/rom_builder.py",
    # Exclude drive module entirely for Pico - saves 28K and memory
    "drive/",
]


def is_excluded(rel_path: Path) -> bool:
    """Check if a file should be excluded from Pico build.

    Arguments:
        rel_path: Path relative to the source directory

    Returns:
        True if the file should be excluded
    """
    rel_str = str(rel_path)
    for pattern in PICO_EXCLUDE:
        if rel_str.endswith(pattern) or pattern in rel_str:
            return True
    return False
