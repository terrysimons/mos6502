#!/usr/bin/env python3
"""Arithmetic instructions for the MOS 6502 CPU."""

# Import from individual arithmetic instruction modules
from mos6502.instructions.arithmetic.adc import (  # noqa: F401
    ADC_ABSOLUTE_0x6D,
    ADC_ABSOLUTE_X_0x7D,
    ADC_ABSOLUTE_Y_0x79,
    ADC_IMMEDIATE_0x69,
    ADC_INDEXED_INDIRECT_X_0x61,
    ADC_INDIRECT_INDEXED_Y_0x71,
    ADC_ZEROPAGE_0x65,
    ADC_ZEROPAGE_X_0x75,
    register_adc_instructions,
)
from mos6502.instructions.arithmetic.dec import (  # noqa: F401
    DEC_ABSOLUTE_0xCE,
    DEC_ABSOLUTE_X_0xDE,
    DEC_ZEROPAGE_0xC6,
    DEC_ZEROPAGE_X_0xD6,
    register_dec_instructions,
)
from mos6502.instructions.arithmetic.dex import DEX_IMPLIED_0xCA, register_dex_instructions  # noqa: F401
from mos6502.instructions.arithmetic.dey import DEY_IMPLIED_0x88, register_dey_instructions  # noqa: F401
from mos6502.instructions.arithmetic.inc import (  # noqa: F401
    INC_ABSOLUTE_0xEE,
    INC_ABSOLUTE_X_0xFE,
    INC_ZEROPAGE_0xE6,
    INC_ZEROPAGE_X_0xF6,
    register_inc_instructions,
)
from mos6502.instructions.arithmetic.inx import INX_IMPLIED_0xE8, register_inx_instructions  # noqa: F401
from mos6502.instructions.arithmetic.iny import INY_IMPLIED_0xC8, register_iny_instructions  # noqa: F401
from mos6502.instructions.arithmetic.sbc import (  # noqa: F401
    SBC_ABSOLUTE_0xED,
    SBC_ABSOLUTE_X_0xFD,
    SBC_ABSOLUTE_Y_0xF9,
    SBC_IMMEDIATE_0xE9,
    SBC_INDEXED_INDIRECT_X_0xE1,
    SBC_INDIRECT_INDEXED_Y_0xF1,
    SBC_ZEROPAGE_0xE5,
    SBC_ZEROPAGE_X_0xF5,
    register_sbc_instructions,
)

__all__ = [
    # ADC
    'ADC_IMMEDIATE_0x69',
    'ADC_ZEROPAGE_0x65',
    'ADC_ZEROPAGE_X_0x75',
    'ADC_ABSOLUTE_0x6D',
    'ADC_ABSOLUTE_X_0x7D',
    'ADC_ABSOLUTE_Y_0x79',
    'ADC_INDEXED_INDIRECT_X_0x61',
    'ADC_INDIRECT_INDEXED_Y_0x71',
    'register_adc_instructions',
    # DEC
    'DEC_ZEROPAGE_0xC6',
    'DEC_ZEROPAGE_X_0xD6',
    'DEC_ABSOLUTE_0xCE',
    'DEC_ABSOLUTE_X_0xDE',
    'register_dec_instructions',
    # DEX
    'DEX_IMPLIED_0xCA',
    'register_dex_instructions',
    # DEY
    'DEY_IMPLIED_0x88',
    'register_dey_instructions',
    # INC
    'INC_ZEROPAGE_0xE6',
    'INC_ZEROPAGE_X_0xF6',
    'INC_ABSOLUTE_0xEE',
    'INC_ABSOLUTE_X_0xFE',
    'register_inc_instructions',
    # INX
    'INX_IMPLIED_0xE8',
    'register_inx_instructions',
    # INY
    'INY_IMPLIED_0xC8',
    'register_iny_instructions',
    # SBC
    'SBC_IMMEDIATE_0xE9',
    'SBC_ZEROPAGE_0xE5',
    'SBC_ZEROPAGE_X_0xF5',
    'SBC_ABSOLUTE_0xED',
    'SBC_ABSOLUTE_X_0xFD',
    'SBC_ABSOLUTE_Y_0xF9',
    'SBC_INDEXED_INDIRECT_X_0xE1',
    'SBC_INDIRECT_INDEXED_Y_0xF1',
    'register_sbc_instructions',
]


def register_all_arithmetic_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register all arithmetic instructions."""
    register_adc_instructions(instruction_set_class, instruction_map)
    register_dec_instructions(instruction_set_class, instruction_map)
    register_dex_instructions(instruction_set_class, instruction_map)
    register_dey_instructions(instruction_set_class, instruction_map)
    register_inc_instructions(instruction_set_class, instruction_map)
    register_inx_instructions(instruction_set_class, instruction_map)
    register_iny_instructions(instruction_set_class, instruction_map)
    register_sbc_instructions(instruction_set_class, instruction_map)
