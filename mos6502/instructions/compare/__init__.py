#!/usr/bin/env python3
"""Compare instructions for the MOS 6502 CPU."""

# Import from individual compare instruction modules
from mos6502.instructions.compare._cmp import (
    CMP_ABSOLUTE_0xCD,
    CMP_ABSOLUTE_X_0xDD,
    CMP_ABSOLUTE_Y_0xD9,
    CMP_IMMEDIATE_0xC9,
    CMP_INDEXED_INDIRECT_X_0xC1,
    CMP_INDIRECT_INDEXED_Y_0xD1,
    CMP_ZEROPAGE_0xC5,
    CMP_ZEROPAGE_X_0xD5,
    register_cmp_instructions,
)
from mos6502.instructions.compare._cpx import (
    CPX_ABSOLUTE_0xEC,
    CPX_IMMEDIATE_0xE0,
    CPX_ZEROPAGE_0xE4,
    register_cpx_instructions,
)
from mos6502.instructions.compare._cpy import (
    CPY_ABSOLUTE_0xCC,
    CPY_IMMEDIATE_0xC0,
    CPY_ZEROPAGE_0xC4,
    register_cpy_instructions,
)

__all__ = [
    # CMP
    "CMP_IMMEDIATE_0xC9",
    "CMP_ZEROPAGE_0xC5",
    "CMP_ZEROPAGE_X_0xD5",
    "CMP_ABSOLUTE_0xCD",
    "CMP_ABSOLUTE_X_0xDD",
    "CMP_ABSOLUTE_Y_0xD9",
    "CMP_INDEXED_INDIRECT_X_0xC1",
    "CMP_INDIRECT_INDEXED_Y_0xD1",
    "register_cmp_instructions",
    # CPX
    "CPX_IMMEDIATE_0xE0",
    "CPX_ZEROPAGE_0xE4",
    "CPX_ABSOLUTE_0xEC",
    "register_cpx_instructions",
    # CPY
    "CPY_IMMEDIATE_0xC0",
    "CPY_ZEROPAGE_0xC4",
    "CPY_ABSOLUTE_0xCC",
    "register_cpy_instructions",
]


def register_all_compare_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register all compare instructions."""
    register_cmp_instructions(instruction_set_class, instruction_map)
    register_cpx_instructions(instruction_set_class, instruction_map)
    register_cpy_instructions(instruction_set_class, instruction_map)
