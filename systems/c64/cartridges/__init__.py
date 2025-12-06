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

# Base classes, enums, and data structures
from .base import (
    # ABC and runtime classes
    Cartridge,
    CartridgeType,
    CartridgeTestResults,
    MapperRequirements,
    MapperTest,
    # Test cartridge generation (Protocol and dataclasses)
    CartridgeInterface,
    CartridgeVariant,
    CartridgeImage,
    # Constants
    MAPPER_REQUIREMENTS,
    # Functions
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

# Test ROM builder for generating test cartridges
from .rom_builder import TestROMBuilder

# Implemented cartridge types (registered in CARTRIDGE_TYPES)
from .type_00_normal import StaticROMCartridge
from .type_01_action_replay import ActionReplayCartridge
from .type_03_final_cartridge_iii import FinalCartridgeIIICartridge
from .type_04_simons_basic import SimonsBasicCartridge
from .type_05_ocean import OceanType1Cartridge
from .type_10_epyx_fastload import EpyxFastloadCartridge
from .type_13_final_cartridge_i import FinalCartridgeICartridge
from .type_15_c64gs import C64GSCartridge
from .type_17_dinamic import DinamicCartridge
from .type_19_magic_desk import MagicDeskCartridge
from .error import ErrorCartridge

# Unimplemented cartridge types (NOT registered - generate error carts for testing)
from .type_02_kcs_power import KcsPowerCartridge
from .type_06_expert import ExpertCartridge
from .type_07_fun_play import FunPlayPowerPlayCartridge
from .type_08_super_games import SuperGamesCartridge
from .type_09_atomic_power import AtomicPowerCartridge
from .type_11_westermann import WestermannLearningCartridge
from .type_12_rex_utility import RexUtilityCartridge
from .type_14_magic_formel import MagicFormelCartridge
from .type_16_warpspeed import WarpspeedCartridge
from .type_18_zaxxon import ZaxxonSuperZaxxonCartridge
from .type_20_super_snapshot_v5 import SuperSnapshotV5Cartridge
from .type_21_comal80 import Comal80Cartridge
from .type_22_structured_basic import StructuredBasicCartridge
from .type_23_ross import RossCartridge
from .type_24_dela_ep64 import DelaEp64Cartridge
from .type_25_dela_ep7x8 import DelaEp7X8Cartridge
from .type_26_dela_ep256 import DelaEp256Cartridge
from .type_27_rex_ep256 import RexEp256Cartridge
from .type_28_mikro_assembler import MikroAssemblerCartridge
from .type_29_final_cartridge_plus import FinalCartridgePlusCartridge
from .type_30_action_replay_4 import ActionReplay4Cartridge
from .type_31_stardos import StardosCartridge
from .type_32_easyflash import EasyflashCartridge
from .type_33_easyflash_xbank import EasyflashXBankCartridge
from .type_34_capture import CaptureCartridge
from .type_35_action_replay_3 import ActionReplay3Cartridge
from .type_36_retro_replay import RetroReplayCartridge
from .type_37_mmc64 import Mmc64Cartridge
from .type_38_mmc_replay import MmcReplayCartridge
from .type_39_ide64 import Ide64Cartridge
from .type_40_super_snapshot_v4 import SuperSnapshotV4Cartridge
from .type_41_ieee488 import Ieee488Cartridge
from .type_42_game_killer import GameKillerCartridge
from .type_43_prophet64 import Prophet64Cartridge
from .type_44_exos import ExosCartridge
from .type_45_freeze_frame import FreezeFrameCartridge
from .type_46_freeze_machine import FreezeMachineCartridge
from .type_47_snapshot64 import Snapshot64Cartridge
from .type_48_super_explode_v5 import SuperExplodeV5Cartridge
from .type_49_magic_voice import MagicVoiceCartridge
from .type_50_action_replay_2 import ActionReplay2Cartridge
from .type_51_mach5 import Mach5Cartridge
from .type_52_diashow_maker import DiashowMakerCartridge
from .type_53_pagefox import PagefoxCartridge
from .type_54_kingsoft import KingsoftBusinessBasicCartridge
from .type_55_silver_rock_128 import SilverRock128Cartridge
from .type_56_formel64 import Formel64Cartridge
from .type_57_rgcd import RgcdCartridge
from .type_58_rrnet_mk3 import RrNetMk3Cartridge
from .type_59_easy_calc import EasyCalcResultCartridge
from .type_60_gmod2 import Gmod2Cartridge
from .type_61_max_basic import MaxBasicCartridge
from .type_62_gmod3 import Gmod3Cartridge
from .type_63_zippcode48 import ZippCode48Cartridge
from .type_64_blackbox_v8 import BlackboxV8Cartridge
from .type_65_blackbox_v3 import BlackboxV3Cartridge
from .type_66_blackbox_v4 import BlackboxV4Cartridge
from .type_67_rex_ram_floppy import RexRamFloppyCartridge
from .type_68_bis_plus import BisPlusCartridge
from .type_69_sd_box import SdBoxCartridge
from .type_70_multimax import MultimaxCartridge
from .type_71_blackbox_v9 import BlackboxV9Cartridge
from .type_72_lt_kernal import LtKernalCartridge
from .type_73_cmd_ramlink import CmdRamlinkCartridge
from .type_74_drean import DreanCartridge
from .type_75_ieee_flash_64 import IeeeFlash64Cartridge
from .type_76_turtle_graphics_ii import TurtleGraphicsIiCartridge
from .type_77_freeze_frame_mk2 import FreezeFrameMk2Cartridge
from .type_78_partner64 import Partner64Cartridge
from .type_79_hyper_basic_mk2 import HyperBasicMk2Cartridge
from .type_80_universal_1 import UniversalCartridge1Cartridge
from .type_81_universal_15 import UniversalCartridge15Cartridge
from .type_82_universal_2 import UniversalCartridge2Cartridge
from .type_83_bmp_turbo_2000 import BmpDataTurbo2000Cartridge
from .type_84_profi_dos import ProfiDosCartridge
from .type_85_magic_desk_16 import MagicDesk16Cartridge

# Registry and factory
from .registry import CARTRIDGE_TYPES, create_cartridge

# Map of unimplemented cartridge types for test cart generation
UNIMPLEMENTED_CARTRIDGE_TYPES: dict[int, type[Cartridge]] = {
    2: KcsPowerCartridge,
    6: ExpertCartridge,
    7: FunPlayPowerPlayCartridge,
    8: SuperGamesCartridge,
    9: AtomicPowerCartridge,
    11: WestermannLearningCartridge,
    12: RexUtilityCartridge,
    14: MagicFormelCartridge,
    16: WarpspeedCartridge,
    18: ZaxxonSuperZaxxonCartridge,
    20: SuperSnapshotV5Cartridge,
    21: Comal80Cartridge,
    22: StructuredBasicCartridge,
    23: RossCartridge,
    24: DelaEp64Cartridge,
    25: DelaEp7X8Cartridge,
    26: DelaEp256Cartridge,
    27: RexEp256Cartridge,
    28: MikroAssemblerCartridge,
    29: FinalCartridgePlusCartridge,
    30: ActionReplay4Cartridge,
    31: StardosCartridge,
    32: EasyflashCartridge,
    33: EasyflashXBankCartridge,
    34: CaptureCartridge,
    35: ActionReplay3Cartridge,
    36: RetroReplayCartridge,
    37: Mmc64Cartridge,
    38: MmcReplayCartridge,
    39: Ide64Cartridge,
    40: SuperSnapshotV4Cartridge,
    41: Ieee488Cartridge,
    42: GameKillerCartridge,
    43: Prophet64Cartridge,
    44: ExosCartridge,
    45: FreezeFrameCartridge,
    46: FreezeMachineCartridge,
    47: Snapshot64Cartridge,
    48: SuperExplodeV5Cartridge,
    49: MagicVoiceCartridge,
    50: ActionReplay2Cartridge,
    51: Mach5Cartridge,
    52: DiashowMakerCartridge,
    53: PagefoxCartridge,
    54: KingsoftBusinessBasicCartridge,
    55: SilverRock128Cartridge,
    56: Formel64Cartridge,
    57: RgcdCartridge,
    58: RrNetMk3Cartridge,
    59: EasyCalcResultCartridge,
    60: Gmod2Cartridge,
    61: MaxBasicCartridge,
    62: Gmod3Cartridge,
    63: ZippCode48Cartridge,
    64: BlackboxV8Cartridge,
    65: BlackboxV3Cartridge,
    66: BlackboxV4Cartridge,
    67: RexRamFloppyCartridge,
    68: BisPlusCartridge,
    69: SdBoxCartridge,
    70: MultimaxCartridge,
    71: BlackboxV9Cartridge,
    72: LtKernalCartridge,
    73: CmdRamlinkCartridge,
    74: DreanCartridge,
    75: IeeeFlash64Cartridge,
    76: TurtleGraphicsIiCartridge,
    77: FreezeFrameMk2Cartridge,
    78: Partner64Cartridge,
    79: HyperBasicMk2Cartridge,
    80: UniversalCartridge1Cartridge,
    81: UniversalCartridge15Cartridge,
    82: UniversalCartridge2Cartridge,
    83: BmpDataTurbo2000Cartridge,
    84: ProfiDosCartridge,
    85: MagicDesk16Cartridge,
}


__all__ = [
    # Enums and types
    "CartridgeType",
    "MapperRequirements",
    "MapperTest",
    "CartridgeTestResults",
    # Test cartridge generation
    "CartridgeInterface",
    "CartridgeVariant",
    "CartridgeImage",
    "TestROMBuilder",
    # Constants
    "MAPPER_REQUIREMENTS",
    "CARTRIDGE_TYPES",
    "UNIMPLEMENTED_CARTRIDGE_TYPES",
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
    # Implemented cartridge classes
    "StaticROMCartridge",
    "ActionReplayCartridge",
    "FinalCartridgeIIICartridge",
    "SimonsBasicCartridge",
    "OceanType1Cartridge",
    "EpyxFastloadCartridge",
    "FinalCartridgeICartridge",
    "C64GSCartridge",
    "DinamicCartridge",
    "MagicDeskCartridge",
    "ErrorCartridge",
    # Unimplemented cartridge classes (for test cart generation)
    "KcsPowerCartridge",
    "ExpertCartridge",
    "FunPlayPowerPlayCartridge",
    "SuperGamesCartridge",
    "AtomicPowerCartridge",
    "WestermannLearningCartridge",
    "RexUtilityCartridge",
    "MagicFormelCartridge",
    "WarpspeedCartridge",
    "ZaxxonSuperZaxxonCartridge",
    "SuperSnapshotV5Cartridge",
    "Comal80Cartridge",
    "StructuredBasicCartridge",
    "RossCartridge",
    "DelaEp64Cartridge",
    "DelaEp7X8Cartridge",
    "DelaEp256Cartridge",
    "RexEp256Cartridge",
    "MikroAssemblerCartridge",
    "FinalCartridgePlusCartridge",
    "ActionReplay4Cartridge",
    "StardosCartridge",
    "EasyflashCartridge",
    "EasyflashXBankCartridge",
    "CaptureCartridge",
    "ActionReplay3Cartridge",
    "RetroReplayCartridge",
    "Mmc64Cartridge",
    "MmcReplayCartridge",
    "Ide64Cartridge",
    "SuperSnapshotV4Cartridge",
    "Ieee488Cartridge",
    "GameKillerCartridge",
    "Prophet64Cartridge",
    "ExosCartridge",
    "FreezeFrameCartridge",
    "FreezeMachineCartridge",
    "Snapshot64Cartridge",
    "SuperExplodeV5Cartridge",
    "MagicVoiceCartridge",
    "ActionReplay2Cartridge",
    "Mach5Cartridge",
    "DiashowMakerCartridge",
    "PagefoxCartridge",
    "KingsoftBusinessBasicCartridge",
    "SilverRock128Cartridge",
    "Formel64Cartridge",
    "RgcdCartridge",
    "RrNetMk3Cartridge",
    "EasyCalcResultCartridge",
    "Gmod2Cartridge",
    "MaxBasicCartridge",
    "Gmod3Cartridge",
    "ZippCode48Cartridge",
    "BlackboxV8Cartridge",
    "BlackboxV3Cartridge",
    "BlackboxV4Cartridge",
    "RexRamFloppyCartridge",
    "BisPlusCartridge",
    "SdBoxCartridge",
    "MultimaxCartridge",
    "BlackboxV9Cartridge",
    "LtKernalCartridge",
    "CmdRamlinkCartridge",
    "DreanCartridge",
    "IeeeFlash64Cartridge",
    "TurtleGraphicsIiCartridge",
    "FreezeFrameMk2Cartridge",
    "Partner64Cartridge",
    "HyperBasicMk2Cartridge",
    "UniversalCartridge1Cartridge",
    "UniversalCartridge15Cartridge",
    "UniversalCartridge2Cartridge",
    "BmpDataTurbo2000Cartridge",
    "ProfiDosCartridge",
    "MagicDesk16Cartridge",
]
