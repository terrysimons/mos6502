#!/usr/bin/env python3
"""Load instructions for the MOS 6502 CPU."""

# Import from individual load instruction modules
from mos6502.instructions.load._lda import (  # noqa: F401
    LDA_ABSOLUTE_0xAD,
    LDA_ABSOLUTE_X_0xBD,
    LDA_ABSOLUTE_Y_0xB9,
    LDA_IMMEDIATE_0xA9,
    LDA_INDEXED_INDIRECT_X_0xA1,
    LDA_INDIRECT_INDEXED_Y_0xB1,
    LDA_ZEROPAGE_0xA5,
    LDA_ZEROPAGE_X_0xB5,
    register_lda_instructions,
)
from mos6502.instructions.load._ldx import (  # noqa: F401
    LDX_ABSOLUTE_0xAE,
    LDX_ABSOLUTE_Y_0xBE,
    LDX_IMMEDIATE_0xA2,
    LDX_ZEROPAGE_0xA6,
    LDX_ZEROPAGE_Y_0xB6,
    register_ldx_instructions,
)
from mos6502.instructions.load._ldy import (  # noqa: F401
    LDY_ABSOLUTE_0xAC,
    LDY_ABSOLUTE_X_0xBC,
    LDY_IMMEDIATE_0xA0,
    LDY_ZEROPAGE_0xA4,
    LDY_ZEROPAGE_X_0xB4,
    register_ldy_instructions,
)

__all__ = [
    # LDA
    'LDA_IMMEDIATE_0xA9',
    'LDA_ZEROPAGE_0xA5',
    'LDA_ZEROPAGE_X_0xB5',
    'LDA_ABSOLUTE_0xAD',
    'LDA_ABSOLUTE_X_0xBD',
    'LDA_ABSOLUTE_Y_0xB9',
    'LDA_INDEXED_INDIRECT_X_0xA1',
    'LDA_INDIRECT_INDEXED_Y_0xB1',
    'register_lda_instructions',
    # LDX
    'LDX_IMMEDIATE_0xA2',
    'LDX_ZEROPAGE_0xA6',
    'LDX_ZEROPAGE_Y_0xB6',
    'LDX_ABSOLUTE_0xAE',
    'LDX_ABSOLUTE_Y_0xBE',
    'register_ldx_instructions',
    # LDY
    'LDY_IMMEDIATE_0xA0',
    'LDY_ZEROPAGE_0xA4',
    'LDY_ZEROPAGE_X_0xB4',
    'LDY_ABSOLUTE_0xAC',
    'LDY_ABSOLUTE_X_0xBC',
    'register_ldy_instructions',
]


def register_all_load_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register all load instructions."""
    register_lda_instructions(instruction_set_class, instruction_map)
    register_ldx_instructions(instruction_set_class, instruction_map)
    register_ldy_instructions(instruction_set_class, instruction_map)
