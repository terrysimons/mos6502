"""Cartridge hardware emulation for C64.

This module provides classes that emulate the hardware behavior of various
C64 cartridge types. Each cartridge type has different banking logic that
is implemented in external hardware on the cartridge PCB.

The CRT file format encodes the cartridge type in the header, which tells
emulators which banking logic to use. Raw .bin files don't have this
information, so they're assumed to be standard (type 0) cartridges.

Memory regions controlled by cartridges:
    ROML: $8000-$9FFF (8KB) - Active when EXROM=0
    ROMH: $A000-$BFFF (8KB) - Active when EXROM=0 and GAME=0
    IO1:  $DE00-$DEFF - Cartridge I/O area 1 (optional, used for bank switching)
    IO2:  $DF00-$DFFF - Cartridge I/O area 2 (optional)

EXROM and GAME are active-low signals from the cartridge that control
the C64's PLA memory mapping:
    EXROM=1, GAME=1: No cartridge (default)
    EXROM=0, GAME=1: 8KB mode (ROML visible)
    EXROM=0, GAME=0: 16KB mode (ROML and ROMH visible)
    EXROM=1, GAME=0: Ultimax mode (ROMH at $E000, replaces KERNAL)

References:
    CRT file format and hardware type IDs:
        - VICE CRT format specification: https://vice-emu.sourceforge.io/vice_17.html#SEC391
        - CRT ID list: http://rr.c64.org/wiki/CRT_ID

    The hardware type list (0-85) comes from the VICE emulator specification,
    which is the de facto standard for C64 cartridge emulation.
"""

# Base classes and enums
from .base import (
    Cartridge,
    CartridgeType,
    CartridgeTestResults,
    MapperRequirements,
    MapperTest,
    MAPPER_REQUIREMENTS,
    generate_mapper_tests,
    parse_color_markup,
    create_error_cartridge_rom,
    # Memory region constants
    ROML_START,
    ROML_END,
    ROML_SIZE,
    ROMH_START,
    ROMH_END,
    ROMH_SIZE,
    ULTIMAX_ROMH_START,
    ULTIMAX_ROMH_END,
    ULTIMAX_ROMH_SIZE,
    IO1_START,
    IO1_END,
    IO2_START,
    IO2_END,
)

# Cartridge implementations
from .type_00_normal import StaticROMCartridge
from .type_01_action_replay import ActionReplayCartridge
from .type_04_simons_basic import SimonsBasicCartridge
from .type_05_ocean import OceanType1Cartridge
from .type_10_epyx_fastload import EpyxFastloadCartridge
from .type_15_c64gs import C64GSCartridge
from .type_17_dinamic import DinamicCartridge
from .type_19_magic_desk import MagicDeskCartridge
from .error import ErrorCartridge

# Registry and factory
from .registry import CARTRIDGE_TYPES, create_cartridge


__all__ = [
    # Enums and types
    "CartridgeType",
    "MapperRequirements",
    "MapperTest",
    "CartridgeTestResults",
    # Constants
    "MAPPER_REQUIREMENTS",
    "CARTRIDGE_TYPES",
    "ROML_START",
    "ROML_END",
    "ROML_SIZE",
    "ROMH_START",
    "ROMH_END",
    "ROMH_SIZE",
    "ULTIMAX_ROMH_START",
    "ULTIMAX_ROMH_END",
    "ULTIMAX_ROMH_SIZE",
    "IO1_START",
    "IO1_END",
    "IO2_START",
    "IO2_END",
    # Functions
    "generate_mapper_tests",
    "parse_color_markup",
    "create_error_cartridge_rom",
    "create_cartridge",
    # Base class
    "Cartridge",
    # Cartridge implementations
    "StaticROMCartridge",
    "ActionReplayCartridge",
    "SimonsBasicCartridge",
    "OceanType1Cartridge",
    "EpyxFastloadCartridge",
    "C64GSCartridge",
    "DinamicCartridge",
    "MagicDeskCartridge",
    "ErrorCartridge",
]
