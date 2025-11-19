#!/usr/bin/env python3
"""Instruction set for the mos6502 CPU."""

# Import from individual instruction modules
from mos6502.instructions.brk import BRK_IMPLIED_0x00, register_brk_instructions  # noqa: F401
from mos6502.instructions.nop import NOP_IMPLIED_0xEA, register_nop_instructions  # noqa: F401

# Import from instruction family modules
from mos6502.instructions.flags import register_all_flag_instructions  # noqa: F401
from mos6502.instructions.flags import *  # noqa: F401, F403

# Re-export everything else from _instructions module
from mos6502.instructions._instructions import *  # noqa: F401, F403

__all__ = [
    # Instruction Set
    'InstructionSet',

    # ADC
    'ADC_IMMEDIATE_0x69',
    'ADC_ZEROPAGE_0x65',
    'ADC_ZEROPAGE_X_0x75',
    'ADC_ABSOLUTE_0x6D',
    'ADC_ABSOLUTE_X_0x7D',
    'ADC_ABSOLUTE_Y_0x79',
    'ADC_INDEXED_INDIRECT_X_0x61',
    'ADC_INDIRECT_INDEXED_Y_0x71',

    # AND
    'AND_IMMEDIATE_0x29',
    'AND_ZEROPAGE_0x25',
    'AND_ZEROPAGE_X_0x35',
    'AND_ABSOLUTE_0x2D',
    'AND_ABSOLUTE_X_0x3D',
    'AND_ABSOLUTE_Y_0x39',
    'AND_INDEXED_INDIRECT_X_0x21',
    'AND_INDIRECT_INDEXED_Y_0x31',

    # ASL
    'ASL_ACCUMULATOR_0x0A',
    'ASL_ZEROPAGE_0x06',
    'ASL_ZEROPAGE_X_0x16',
    'ASL_ABSOLUTE_0x0E',
    'ASL_ABSOLUTE_X_0x1E',

    # Branch
    'BBC_RELATIVE_0x90',
    'BCS_RELATIVE_0xB0',
    'BEQ_RELATIVE_0xF0',
    'BIT_ZEROPAGE_0x24',
    'BIT_ABSOLUTE_0x2C',
    'BMI_RELATIVE_0x30',
    'BNE_RELATIVE_0xD0',
    'BPL_RELATIVE_0x10',
    'BRK_IMPLIED_0x00',
    'BVC_RELATIVE_0x50',
    'BVS_RELATIVE_0x70',

    # Clear Flags
    'CLC_IMPLIED_0x18',
    'CLD_IMPLIED_0xD8',
    'CLI_IMPLIED_0x58',
    'CLV_IMPLIED_0xB8',

    # Compare
    'CMP_IMMEDIATE_0xC9',
    'CMP_ZEROPAGE_0xC5',
    'CMP_ZEROPAGE_X_0xD5',
    'CMP_ABSOLUTE_0xCD',
    'CMP_ABSOLUTE_X_0xDD',
    'CMP_ABSOLUTE_Y_0xD9',
    'CMP_INDEXED_INDIRECT_X_0xC1',
    'CMP_INDIRECT_INDEXED_Y_0xD1',
    'CPX_IMMEDIATE_0xE0',
    'CPX_ZEROPAGE_0xE4',
    'CPX_ABSOLUTE_0xEC',
    'CPY_IMMEDIATE_0xC0',
    'CPY_ZEROPAGE_0xC4',
    'CPY_ABSOLUTE_0xCC',

    # Decrement
    'DEC_ZEROPAGE_0xC6',
    'DEC_ZEROPAGE_X_0xD6',
    'DEC_ABSOLUTE_0xCE',
    'DEC_ABSOLUTE_X_0xDE',
    'DEX_IMPLIED_0xCA',
    'DEY_IMPLIED_0x88',

    # EOR
    'EOR_IMMEDIATE_0x49',
    'EOR_ZEROPAGE_0x45',
    'EOR_ZEROPAGE_X_0x55',
    'EOR_ABSOLUTE_0x4D',
    'EOR_ABSOLUTE_X_0x5D',
    'EOR_ABSOLUTE_Y_0x59',
    'EOR_INDEXED_INDIRECT_X_0x41',
    'EOR_INDIRECT_INDEXED_Y_0x51',

    # Increment
    'INC_ZEROPAGE_0xE6',
    'INC_ZEROPAGE_X_0xF6',
    'INC_ABSOLUTE_0xEE',
    'INC_ABSOLUTE_X_0xFE',
    'INX_IMPLIED_0xE8',
    'INY_IMPLIED_0xC8',

    # JMP/JSR/RTS/RTI
    'JMP_ABSOLUTE_0x4C',
    'JMP_INDIRECT_0x6C',
    'JSR_ABSOLUTE_0x20',
    'RTS_IMPLIED_0x60',
    'RTI_IMPLIED_0x40',

    # Load
    'LDA_IMMEDIATE_0xA9',
    'LDA_ZEROPAGE_0xA5',
    'LDA_ZEROPAGE_X_0xB5',
    'LDA_ABSOLUTE_0xAD',
    'LDA_ABSOLUTE_X_0xBD',
    'LDA_ABSOLUTE_Y_0xB9',
    'LDA_INDEXED_INDIRECT_X_0xA1',
    'LDA_INDIRECT_INDEXED_Y_0xB1',
    'LDX_IMMEDIATE_0xA2',
    'LDX_ZEROPAGE_0xA6',
    'LDX_ZEROPAGE_Y_0xB6',
    'LDX_ABSOLUTE_0xAE',
    'LDX_ABSOLUTE_Y_0xBE',
    'LDY_IMMEDIATE_0xA0',
    'LDY_ZEROPAGE_0xA4',
    'LDY_ZEROPAGE_X_0xB4',
    'LDY_ABSOLUTE_0xAC',
    'LDY_ABSOLUTE_X_0xBC',

    # LSR
    'LSR_ACCUMULATOR_0x4A',
    'LSR_ZEROPAGE_0x46',
    'LSR_ZEROPAGE_X_0x56',
    'LSR_ABSOLUTE_0x4E',
    'LSR_ABSOLUTE_X_0x5E',

    # NOP
    'NOP_IMPLIED_0xEA',

    # ORA
    'ORA_IMMEDIATE_0x09',
    'ORA_ZEROPAGE_0x05',
    'ORA_ZEROPAGE_X_0x15',
    'ORA_ABSOLUTE_0x0D',
    'ORA_ABSOLUTE_X_0x1D',
    'ORA_ABSOLUTE_Y_0x19',
    'ORA_INDEXED_INDIRECT_X_0x01',
    'ORA_INDIRECT_INDEXED_Y_0x11',

    # Stack
    'PHA_IMPLIED_0x48',
    'PHP_IMPLIED_0x08',
    'PLA_IMPLIED_0x68',
    'PLP_IMPLIED_0x28',

    # ROL
    'ROL_ACCUMULATOR_0x2A',
    'ROL_ZEROPAGE_0x26',
    'ROL_ZEROPAGE_X_0x36',
    'ROL_ABSOLUTE_0x2E',
    'ROL_ABSOLUTE_X_0x3E',

    # ROR
    'ROR_ACCUMULATOR_0x6A',
    'ROR_ZEROPAGE_0x66',
    'ROR_ZEROPAGE_X_0x76',
    'ROR_ABSOLUTE_0x6E',
    'ROR_ABSOLUTE_X_0x7E',

    # SBC
    'SBC_IMMEDIATE_0xE9',
    'SBC_ZEROPAGE_0xE5',
    'SBC_ZEROPAGE_X_0xF5',
    'SBC_ABSOLUTE_0xED',
    'SBC_ABSOLUTE_X_0xFD',
    'SBC_ABSOLUTE_Y_0xF9',
    'SBC_INDEXED_INDIRECT_X_0xE1',
    'SBC_INDIRECT_INDEXED_Y_0xF1',

    # Set Flags
    'SEC_IMPLIED_0x38',
    'SED_IMPLIED_0xF8',
    'SEI_IMPLIED_0x78',

    # Store
    'STA_ZEROPAGE_0x85',
    'STA_ZEROPAGE_X_0x95',
    'STA_ABSOLUTE_0x8D',
    'STA_ABSOLUTE_X_0x9D',
    'STA_ABSOLUTE_Y_0x99',
    'STA_INDEXED_INDIRECT_X_0x81',
    'STA_INDIRECT_INDEXED_Y_0x91',
    'STX_ZEROPAGE_0x86',
    'STX_ZEROPAGE_Y_0x96',
    'STX_ABSOLUTE_0x8E',
    'STY_ZEROPAGE_0x84',
    'STY_ZEROPAGE_X_0x94',
    'STY_ABSOLUTE_0x8C',

    # Transfer
    'TAX_IMPLIED_0xAA',
    'TAY_IMPLIED_0xA8',
    'TSX_IMPLIED_0xBA',
    'TXA_IMPLIED_0x8A',
    'TXS_IMPLIED_0x9A',
    'TYA_IMPLIED_0x98',
]

# Register instruction modules
register_brk_instructions(InstructionSet, InstructionSet.map)
register_nop_instructions(InstructionSet, InstructionSet.map)
register_all_flag_instructions(InstructionSet, InstructionSet.map)
