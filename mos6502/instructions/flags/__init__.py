#!/usr/bin/env python3
"""Flag manipulation instructions for the MOS 6502 CPU."""

# Import from individual flag instruction modules
from mos6502.instructions.flags.clc import CLC_IMPLIED_0x18, register_clc_instructions  # noqa: F401
from mos6502.instructions.flags.cld import CLD_IMPLIED_0xD8, register_cld_instructions  # noqa: F401
from mos6502.instructions.flags.cli import CLI_IMPLIED_0x58, register_cli_instructions  # noqa: F401
from mos6502.instructions.flags.clv import CLV_IMPLIED_0xB8, register_clv_instructions  # noqa: F401
from mos6502.instructions.flags.sec import SEC_IMPLIED_0x38, register_sec_instructions  # noqa: F401
from mos6502.instructions.flags.sed import SED_IMPLIED_0xF8, register_sed_instructions  # noqa: F401
from mos6502.instructions.flags.sei import SEI_IMPLIED_0x78, register_sei_instructions  # noqa: F401

__all__ = [
    # CLC
    'CLC_IMPLIED_0x18',
    'register_clc_instructions',
    # CLD
    'CLD_IMPLIED_0xD8',
    'register_cld_instructions',
    # CLI
    'CLI_IMPLIED_0x58',
    'register_cli_instructions',
    # CLV
    'CLV_IMPLIED_0xB8',
    'register_clv_instructions',
    # SEC
    'SEC_IMPLIED_0x38',
    'register_sec_instructions',
    # SED
    'SED_IMPLIED_0xF8',
    'register_sed_instructions',
    # SEI
    'SEI_IMPLIED_0x78',
    'register_sei_instructions',
]


def register_all_flag_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register all flag instructions."""
    register_clc_instructions(instruction_set_class, instruction_map)
    register_cld_instructions(instruction_set_class, instruction_map)
    register_cli_instructions(instruction_set_class, instruction_map)
    register_clv_instructions(instruction_set_class, instruction_map)
    register_sec_instructions(instruction_set_class, instruction_map)
    register_sed_instructions(instruction_set_class, instruction_map)
    register_sei_instructions(instruction_set_class, instruction_map)
