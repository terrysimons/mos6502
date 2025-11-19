#!/usr/bin/env python3
"""Flag manipulation instructions for the MOS 6502 CPU."""

# Import from individual flag instruction modules
from mos6502.instructions.flags.clc import CLC_IMPLIED_0x18, register_clc_instructions  # noqa: F401

__all__ = [
    # CLC
    'CLC_IMPLIED_0x18',
    'register_clc_instructions',
]


def register_all_flag_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register all flag instructions."""
    register_clc_instructions(instruction_set_class, instruction_map)
