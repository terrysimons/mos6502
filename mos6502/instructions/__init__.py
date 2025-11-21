#!/usr/bin/env python3
"""Instruction set for the mos6502 CPU."""
import enum
from typing import NoReturn

from mos6502.errors import IllegalCPUInstructionError


class InstructionOpcode(int):
    """Instruction opcode that carries its variant metadata.

    This class extends int to carry package and function names for variant dispatch,
    while remaining fully compatible with existing code that expects plain integers.

    Example:
    -------
        NOP_IMPLIED_0xEA = InstructionOpcode(
            0xEA,
            "mos6502.instructions.nop",
            "nop_implied_0xea"
        )
    """

    def __new__(cls, value: int, package: str, function: str):
        """Create instruction opcode with metadata.

        Arguments:
        ---------
            value: The opcode value (e.g., 0xEA)
            package: Package name (e.g., "mos6502.instructions.nop")
            function: Function name (e.g., "nop_implied_0xea")
        """
        obj = int.__new__(cls, value)
        obj.package = package  # type: ignore
        obj.function = function  # type: ignore
        return obj

# Import from individual instruction modules
from mos6502.instructions._bit import BIT_ZEROPAGE_0x24, BIT_ABSOLUTE_0x2C, register_bit_instructions
from mos6502.instructions._brk import BRK_IMPLIED_0x00, register_brk_instructions
# Illegal instructions
from mos6502.instructions.illegal._lax import (
    LAX_ZEROPAGE_0xA7,
    LAX_ZEROPAGE_Y_0xB7,
    LAX_INDEXED_INDIRECT_X_0xA3,
    LAX_INDIRECT_INDEXED_Y_0xB3,
    LAX_ABSOLUTE_0xAF,
    LAX_ABSOLUTE_Y_0xBF,
    LAX_IMMEDIATE_0xAB,
    register_lax_instructions,
)
from mos6502.instructions.illegal._sax import (
    SAX_ZEROPAGE_0x87,
    SAX_ZEROPAGE_Y_0x97,
    SAX_INDEXED_INDIRECT_X_0x83,
    SAX_ABSOLUTE_0x8F,
    register_sax_instructions,
)
from mos6502.instructions.illegal._dcp import (
    DCP_ZEROPAGE_0xC7,
    DCP_ZEROPAGE_X_0xD7,
    DCP_INDEXED_INDIRECT_X_0xC3,
    DCP_INDIRECT_INDEXED_Y_0xD3,
    DCP_ABSOLUTE_0xCF,
    DCP_ABSOLUTE_X_0xDF,
    DCP_ABSOLUTE_Y_0xDB,
    register_dcp_instructions,
)
from mos6502.instructions.illegal._isc import (
    ISC_ZEROPAGE_0xE7,
    ISC_ZEROPAGE_X_0xF7,
    ISC_INDEXED_INDIRECT_X_0xE3,
    ISC_INDIRECT_INDEXED_Y_0xF3,
    ISC_ABSOLUTE_0xEF,
    ISC_ABSOLUTE_X_0xFF,
    ISC_ABSOLUTE_Y_0xFB,
    register_isc_instructions,
)
from mos6502.instructions.illegal._slo import (
    SLO_ZEROPAGE_0x07,
    SLO_ZEROPAGE_X_0x17,
    SLO_INDEXED_INDIRECT_X_0x03,
    SLO_INDIRECT_INDEXED_Y_0x13,
    SLO_ABSOLUTE_0x0F,
    SLO_ABSOLUTE_X_0x1F,
    SLO_ABSOLUTE_Y_0x1B,
    register_slo_instructions,
)
from mos6502.instructions.illegal._rla import (
    RLA_ZEROPAGE_0x27,
    RLA_ZEROPAGE_X_0x37,
    RLA_INDEXED_INDIRECT_X_0x23,
    RLA_INDIRECT_INDEXED_Y_0x33,
    RLA_ABSOLUTE_0x2F,
    RLA_ABSOLUTE_X_0x3F,
    RLA_ABSOLUTE_Y_0x3B,
    register_rla_instructions,
)
from mos6502.instructions.illegal._sre import (
    SRE_ZEROPAGE_0x47,
    SRE_ZEROPAGE_X_0x57,
    SRE_INDEXED_INDIRECT_X_0x43,
    SRE_INDIRECT_INDEXED_Y_0x53,
    SRE_ABSOLUTE_0x4F,
    SRE_ABSOLUTE_X_0x5F,
    SRE_ABSOLUTE_Y_0x5B,
    register_sre_instructions,
)
from mos6502.instructions.illegal._rra import (
    RRA_ZEROPAGE_0x67,
    RRA_ZEROPAGE_X_0x77,
    RRA_INDEXED_INDIRECT_X_0x63,
    RRA_INDIRECT_INDEXED_Y_0x73,
    RRA_ABSOLUTE_0x6F,
    RRA_ABSOLUTE_X_0x7F,
    RRA_ABSOLUTE_Y_0x7B,
    register_rra_instructions,
)
from mos6502.instructions.illegal._anc import (
    ANC_IMMEDIATE_0x0B,
    ANC_IMMEDIATE_0x2B,
    register_anc_instructions,
)
from mos6502.instructions.illegal._alr import (
    ALR_IMMEDIATE_0x4B,
    register_alr_instructions,
)
from mos6502.instructions.illegal._arr import (
    ARR_IMMEDIATE_0x6B,
    register_arr_instructions,
)
from mos6502.instructions.illegal._sbx import (
    SBX_IMMEDIATE_0xCB,
    register_sbx_instructions,
)
from mos6502.instructions.illegal._las import (
    LAS_ABSOLUTE_Y_0xBB,
    register_las_instructions,
)
from mos6502.instructions.load._lda import (
    LDA_IMMEDIATE_0xA9,
    LDA_ZEROPAGE_0xA5,
    LDA_ZEROPAGE_X_0xB5,
    LDA_ABSOLUTE_0xAD,
    LDA_ABSOLUTE_X_0xBD,
    LDA_ABSOLUTE_Y_0xB9,
    LDA_INDEXED_INDIRECT_X_0xA1,
    LDA_INDIRECT_INDEXED_Y_0xB1,
    register_lda_instructions,
)
from mos6502.instructions.load._ldx import (
    LDX_IMMEDIATE_0xA2,
    LDX_ZEROPAGE_0xA6,
    LDX_ZEROPAGE_Y_0xB6,
    LDX_ABSOLUTE_0xAE,
    LDX_ABSOLUTE_Y_0xBE,
    register_ldx_instructions,
)
from mos6502.instructions.load._ldy import (
    LDY_IMMEDIATE_0xA0,
    LDY_ZEROPAGE_0xA4,
    LDY_ZEROPAGE_X_0xB4,
    LDY_ABSOLUTE_0xAC,
    LDY_ABSOLUTE_X_0xBC,
    register_ldy_instructions,
)
from mos6502.instructions.store._sta import (
    STA_ZEROPAGE_0x85,
    STA_ZEROPAGE_X_0x95,
    STA_ABSOLUTE_0x8D,
    STA_ABSOLUTE_X_0x9D,
    STA_ABSOLUTE_Y_0x99,
    STA_INDEXED_INDIRECT_X_0x81,
    STA_INDIRECT_INDEXED_Y_0x91,
    register_sta_instructions,
)
from mos6502.instructions.store._stx import (
    STX_ZEROPAGE_0x86,
    STX_ZEROPAGE_Y_0x96,
    STX_ABSOLUTE_0x8E,
    register_stx_instructions,
)
from mos6502.instructions.store._sty import (
    STY_ZEROPAGE_0x84,
    STY_ZEROPAGE_X_0x94,
    STY_ABSOLUTE_0x8C,
    register_sty_instructions,
)
from mos6502.instructions.compare._cmp import (
    CMP_IMMEDIATE_0xC9,
    CMP_ZEROPAGE_0xC5,
    CMP_ZEROPAGE_X_0xD5,
    CMP_ABSOLUTE_0xCD,
    CMP_ABSOLUTE_X_0xDD,
    CMP_ABSOLUTE_Y_0xD9,
    CMP_INDEXED_INDIRECT_X_0xC1,
    CMP_INDIRECT_INDEXED_Y_0xD1,
    register_cmp_instructions,
)
from mos6502.instructions.compare._cpx import (
    CPX_IMMEDIATE_0xE0,
    CPX_ZEROPAGE_0xE4,
    CPX_ABSOLUTE_0xEC,
    register_cpx_instructions,
)
from mos6502.instructions.compare._cpy import (
    CPY_IMMEDIATE_0xC0,
    CPY_ZEROPAGE_0xC4,
    CPY_ABSOLUTE_0xCC,
    register_cpy_instructions,
)
from mos6502.instructions.logic import (  # noqa: F401
    AND_IMMEDIATE_0x29,
    AND_ZEROPAGE_0x25,
    AND_ZEROPAGE_X_0x35,
    AND_ABSOLUTE_0x2D,
    AND_ABSOLUTE_X_0x3D,
    AND_ABSOLUTE_Y_0x39,
    AND_INDEXED_INDIRECT_X_0x21,
    AND_INDIRECT_INDEXED_Y_0x31,
    EOR_IMMEDIATE_0x49,
    EOR_ZEROPAGE_0x45,
    EOR_ZEROPAGE_X_0x55,
    EOR_ABSOLUTE_0x4D,
    EOR_ABSOLUTE_X_0x5D,
    EOR_ABSOLUTE_Y_0x59,
    EOR_INDEXED_INDIRECT_X_0x41,
    EOR_INDIRECT_INDEXED_Y_0x51,
    ORA_IMMEDIATE_0x09,
    ORA_ZEROPAGE_0x05,
    ORA_ZEROPAGE_X_0x15,
    ORA_ABSOLUTE_0x0D,
    ORA_ABSOLUTE_X_0x1D,
    ORA_ABSOLUTE_Y_0x19,
    ORA_INDEXED_INDIRECT_X_0x01,
    ORA_INDIRECT_INDEXED_Y_0x11,
    register_and_instructions,
    register_eor_instructions,
    register_ora_instructions,
)
from mos6502.instructions.arithmetic._adc import (
    ADC_IMMEDIATE_0x69,
    ADC_ZEROPAGE_0x65,
    ADC_ZEROPAGE_X_0x75,
    ADC_ABSOLUTE_0x6D,
    ADC_ABSOLUTE_X_0x7D,
    ADC_ABSOLUTE_Y_0x79,
    ADC_INDEXED_INDIRECT_X_0x61,
    ADC_INDIRECT_INDEXED_Y_0x71,
    register_adc_instructions,
)
from mos6502.instructions.arithmetic._sbc import (
    SBC_IMMEDIATE_0xE9,
    SBC_ZEROPAGE_0xE5,
    SBC_ZEROPAGE_X_0xF5,
    SBC_ABSOLUTE_0xED,
    SBC_ABSOLUTE_X_0xFD,
    SBC_ABSOLUTE_Y_0xF9,
    SBC_INDEXED_INDIRECT_X_0xE1,
    SBC_INDIRECT_INDEXED_Y_0xF1,
    register_sbc_instructions,
)
from mos6502.instructions.arithmetic._inc import (
    INC_ZEROPAGE_0xE6,
    INC_ZEROPAGE_X_0xF6,
    INC_ABSOLUTE_0xEE,
    INC_ABSOLUTE_X_0xFE,
    register_inc_instructions,
)
from mos6502.instructions.arithmetic._dec import (
    DEC_ZEROPAGE_0xC6,
    DEC_ZEROPAGE_X_0xD6,
    DEC_ABSOLUTE_0xCE,
    DEC_ABSOLUTE_X_0xDE,
    register_dec_instructions,
)
from mos6502.instructions.arithmetic._dex import DEX_IMPLIED_0xCA, register_dex_instructions
from mos6502.instructions.arithmetic._dey import DEY_IMPLIED_0x88, register_dey_instructions
from mos6502.instructions.arithmetic._inx import INX_IMPLIED_0xE8, register_inx_instructions
from mos6502.instructions.arithmetic._iny import INY_IMPLIED_0xC8, register_iny_instructions
from mos6502.instructions.shift._asl import (
    ASL_ACCUMULATOR_0x0A,
    ASL_ZEROPAGE_0x06,
    ASL_ZEROPAGE_X_0x16,
    ASL_ABSOLUTE_0x0E,
    ASL_ABSOLUTE_X_0x1E,
    register_asl_instructions,
)
from mos6502.instructions.shift._lsr import (
    LSR_ACCUMULATOR_0x4A,
    LSR_ZEROPAGE_0x46,
    LSR_ZEROPAGE_X_0x56,
    LSR_ABSOLUTE_0x4E,
    LSR_ABSOLUTE_X_0x5E,
    register_lsr_instructions,
)
from mos6502.instructions.shift._rol import (
    ROL_ACCUMULATOR_0x2A,
    ROL_ZEROPAGE_0x26,
    ROL_ZEROPAGE_X_0x36,
    ROL_ABSOLUTE_0x2E,
    ROL_ABSOLUTE_X_0x3E,
    register_rol_instructions,
)
from mos6502.instructions.shift._ror import (
    ROR_ACCUMULATOR_0x6A,
    ROR_ZEROPAGE_0x66,
    ROR_ZEROPAGE_X_0x76,
    ROR_ABSOLUTE_0x6E,
    ROR_ABSOLUTE_X_0x7E,
    register_ror_instructions,
)
from mos6502.instructions.subroutines._jmp import JMP_ABSOLUTE_0x4C, JMP_INDIRECT_0x6C, register_jmp_instructions
from mos6502.instructions.subroutines._jsr import JSR_ABSOLUTE_0x20, register_jsr_instructions
from mos6502.instructions.subroutines._rti import RTI_IMPLIED_0x40, register_rti_instructions
from mos6502.instructions.subroutines._rts import RTS_IMPLIED_0x60, register_rts_instructions
from mos6502.instructions._nop import NOP_IMPLIED_0xEA, register_nop_instructions

# Import from instruction family modules
# from mos6502.instructions.arithmetic import register_all_arithmetic_instructions  # MIGRATED to adc/sbc/inc/dec packages
# from mos6502.instructions.arithmetic import *  # MIGRATED to adc/sbc/inc/dec packages
from mos6502.instructions.branch import register_all_branch_instructions
from mos6502.instructions.branch import *  # noqa: F403
# from mos6502.instructions.compare import register_all_compare_instructions  # MIGRATED to cmp/cpx/cpy packages
# from mos6502.instructions.compare import *  # MIGRATED to cmp/cpx/cpy packages
from mos6502.instructions.flags import register_all_flag_instructions
from mos6502.instructions.flags import *  # noqa: F403
# from mos6502.instructions.load import register_all_load_instructions  # MIGRATED to lda/ldx/ldy packages
# from mos6502.instructions.load import *  # MIGRATED to lda/ldx/ldy packages
from mos6502.instructions.logic import register_all_logic_instructions
from mos6502.instructions.logic import *  # noqa: F403
# from mos6502.instructions.shift import register_all_shift_instructions  # MIGRATED to asl/lsr/rol/ror packages
# from mos6502.instructions.shift import *  # MIGRATED to asl/lsr/rol/ror packages
from mos6502.instructions.stack import register_all_stack_instructions
from mos6502.instructions.stack import *  # noqa: F403
# from mos6502.instructions.store import register_all_store_instructions  # MIGRATED to sta/stx/sty packages
# from mos6502.instructions.store import *  # MIGRATED to sta/stx/sty packages
from mos6502.instructions.transfer import register_all_transfer_instructions
from mos6502.instructions.transfer import *  # noqa: F403

__all__ = [
    # Instruction Set
    "InstructionSet",

    # ADC
    "ADC_IMMEDIATE_0x69",
    "ADC_ZEROPAGE_0x65",
    "ADC_ZEROPAGE_X_0x75",
    "ADC_ABSOLUTE_0x6D",
    "ADC_ABSOLUTE_X_0x7D",
    "ADC_ABSOLUTE_Y_0x79",
    "ADC_INDEXED_INDIRECT_X_0x61",
    "ADC_INDIRECT_INDEXED_Y_0x71",

    # AND
    "AND_IMMEDIATE_0x29",
    "AND_ZEROPAGE_0x25",
    "AND_ZEROPAGE_X_0x35",
    "AND_ABSOLUTE_0x2D",
    "AND_ABSOLUTE_X_0x3D",
    "AND_ABSOLUTE_Y_0x39",
    "AND_INDEXED_INDIRECT_X_0x21",
    "AND_INDIRECT_INDEXED_Y_0x31",

    # ASL
    "ASL_ACCUMULATOR_0x0A",
    "ASL_ZEROPAGE_0x06",
    "ASL_ZEROPAGE_X_0x16",
    "ASL_ABSOLUTE_0x0E",
    "ASL_ABSOLUTE_X_0x1E",

    # Branch
    "BBC_RELATIVE_0x90",
    "BCS_RELATIVE_0xB0",
    "BEQ_RELATIVE_0xF0",
    "BIT_ZEROPAGE_0x24",
    "BIT_ABSOLUTE_0x2C",
    "BMI_RELATIVE_0x30",
    "BNE_RELATIVE_0xD0",
    "BPL_RELATIVE_0x10",
    "BRK_IMPLIED_0x00",
    "BVC_RELATIVE_0x50",
    "BVS_RELATIVE_0x70",

    # Clear Flags
    "CLC_IMPLIED_0x18",
    "CLD_IMPLIED_0xD8",
    "CLI_IMPLIED_0x58",
    "CLV_IMPLIED_0xB8",

    # Compare
    "CMP_IMMEDIATE_0xC9",
    "CMP_ZEROPAGE_0xC5",
    "CMP_ZEROPAGE_X_0xD5",
    "CMP_ABSOLUTE_0xCD",
    "CMP_ABSOLUTE_X_0xDD",
    "CMP_ABSOLUTE_Y_0xD9",
    "CMP_INDEXED_INDIRECT_X_0xC1",
    "CMP_INDIRECT_INDEXED_Y_0xD1",
    "CPX_IMMEDIATE_0xE0",
    "CPX_ZEROPAGE_0xE4",
    "CPX_ABSOLUTE_0xEC",
    "CPY_IMMEDIATE_0xC0",
    "CPY_ZEROPAGE_0xC4",
    "CPY_ABSOLUTE_0xCC",

    # Decrement
    "DEC_ZEROPAGE_0xC6",
    "DEC_ZEROPAGE_X_0xD6",
    "DEC_ABSOLUTE_0xCE",
    "DEC_ABSOLUTE_X_0xDE",
    "DEX_IMPLIED_0xCA",
    "DEY_IMPLIED_0x88",

    # EOR
    "EOR_IMMEDIATE_0x49",
    "EOR_ZEROPAGE_0x45",
    "EOR_ZEROPAGE_X_0x55",
    "EOR_ABSOLUTE_0x4D",
    "EOR_ABSOLUTE_X_0x5D",
    "EOR_ABSOLUTE_Y_0x59",
    "EOR_INDEXED_INDIRECT_X_0x41",
    "EOR_INDIRECT_INDEXED_Y_0x51",

    # Increment
    "INC_ZEROPAGE_0xE6",
    "INC_ZEROPAGE_X_0xF6",
    "INC_ABSOLUTE_0xEE",
    "INC_ABSOLUTE_X_0xFE",
    "INX_IMPLIED_0xE8",
    "INY_IMPLIED_0xC8",

    # JMP/JSR/RTS/RTI
    "JMP_ABSOLUTE_0x4C",
    "JMP_INDIRECT_0x6C",
    "JSR_ABSOLUTE_0x20",
    "RTS_IMPLIED_0x60",
    "RTI_IMPLIED_0x40",

    # Load
    "LDA_IMMEDIATE_0xA9",
    "LDA_ZEROPAGE_0xA5",
    "LDA_ZEROPAGE_X_0xB5",
    "LDA_ABSOLUTE_0xAD",
    "LDA_ABSOLUTE_X_0xBD",
    "LDA_ABSOLUTE_Y_0xB9",
    "LDA_INDEXED_INDIRECT_X_0xA1",
    "LDA_INDIRECT_INDEXED_Y_0xB1",
    "LDX_IMMEDIATE_0xA2",
    "LDX_ZEROPAGE_0xA6",
    "LDX_ZEROPAGE_Y_0xB6",
    "LDX_ABSOLUTE_0xAE",
    "LDX_ABSOLUTE_Y_0xBE",
    "LDY_IMMEDIATE_0xA0",
    "LDY_ZEROPAGE_0xA4",
    "LDY_ZEROPAGE_X_0xB4",
    "LDY_ABSOLUTE_0xAC",
    "LDY_ABSOLUTE_X_0xBC",

    # Illegal: LAX
    "LAX_ZEROPAGE_0xA7",
    "LAX_ZEROPAGE_Y_0xB7",
    "LAX_INDEXED_INDIRECT_X_0xA3",
    "LAX_INDIRECT_INDEXED_Y_0xB3",
    "LAX_ABSOLUTE_0xAF",
    "LAX_ABSOLUTE_Y_0xBF",
    "LAX_IMMEDIATE_0xAB",

    # Illegal: SAX
    "SAX_ZEROPAGE_0x87",
    "SAX_ZEROPAGE_Y_0x97",
    "SAX_INDEXED_INDIRECT_X_0x83",
    "SAX_ABSOLUTE_0x8F",

    # Illegal: DCP
    "DCP_ZEROPAGE_0xC7",
    "DCP_ZEROPAGE_X_0xD7",
    "DCP_INDEXED_INDIRECT_X_0xC3",
    "DCP_INDIRECT_INDEXED_Y_0xD3",
    "DCP_ABSOLUTE_0xCF",
    "DCP_ABSOLUTE_X_0xDF",
    "DCP_ABSOLUTE_Y_0xDB",

    # Illegal: ISC
    "ISC_ZEROPAGE_0xE7",
    "ISC_ZEROPAGE_X_0xF7",
    "ISC_INDEXED_INDIRECT_X_0xE3",
    "ISC_INDIRECT_INDEXED_Y_0xF3",
    "ISC_ABSOLUTE_0xEF",
    "ISC_ABSOLUTE_X_0xFF",
    "ISC_ABSOLUTE_Y_0xFB",

    # Illegal: SLO
    "SLO_ZEROPAGE_0x07",
    "SLO_ZEROPAGE_X_0x17",
    "SLO_INDEXED_INDIRECT_X_0x03",
    "SLO_INDIRECT_INDEXED_Y_0x13",
    "SLO_ABSOLUTE_0x0F",
    "SLO_ABSOLUTE_X_0x1F",
    "SLO_ABSOLUTE_Y_0x1B",

    # Illegal: RLA
    "RLA_ZEROPAGE_0x27",
    "RLA_ZEROPAGE_X_0x37",
    "RLA_INDEXED_INDIRECT_X_0x23",
    "RLA_INDIRECT_INDEXED_Y_0x33",
    "RLA_ABSOLUTE_0x2F",
    "RLA_ABSOLUTE_X_0x3F",
    "RLA_ABSOLUTE_Y_0x3B",

    # Illegal: SRE
    "SRE_ZEROPAGE_0x47",
    "SRE_ZEROPAGE_X_0x57",
    "SRE_INDEXED_INDIRECT_X_0x43",
    "SRE_INDIRECT_INDEXED_Y_0x53",
    "SRE_ABSOLUTE_0x4F",
    "SRE_ABSOLUTE_X_0x5F",
    "SRE_ABSOLUTE_Y_0x5B",

    # Illegal: RRA
    "RRA_ZEROPAGE_0x67",
    "RRA_ZEROPAGE_X_0x77",
    "RRA_INDEXED_INDIRECT_X_0x63",
    "RRA_INDIRECT_INDEXED_Y_0x73",
    "RRA_ABSOLUTE_0x6F",
    "RRA_ABSOLUTE_X_0x7F",
    "RRA_ABSOLUTE_Y_0x7B",

    # Illegal: ANC
    "ANC_IMMEDIATE_0x0B",
    "ANC_IMMEDIATE_0x2B",

    # Illegal: ALR
    "ALR_IMMEDIATE_0x4B",

    # Illegal: ARR
    "ARR_IMMEDIATE_0x6B",

    # Illegal: SBX
    "SBX_IMMEDIATE_0xCB",

    # Illegal: LAS
    "LAS_ABSOLUTE_Y_0xBB",

    # LSR
    "LSR_ACCUMULATOR_0x4A",
    "LSR_ZEROPAGE_0x46",
    "LSR_ZEROPAGE_X_0x56",
    "LSR_ABSOLUTE_0x4E",
    "LSR_ABSOLUTE_X_0x5E",

    # NOP
    "NOP_IMPLIED_0xEA",

    # ORA
    "ORA_IMMEDIATE_0x09",
    "ORA_ZEROPAGE_0x05",
    "ORA_ZEROPAGE_X_0x15",
    "ORA_ABSOLUTE_0x0D",
    "ORA_ABSOLUTE_X_0x1D",
    "ORA_ABSOLUTE_Y_0x19",
    "ORA_INDEXED_INDIRECT_X_0x01",
    "ORA_INDIRECT_INDEXED_Y_0x11",

    # Stack
    "PHA_IMPLIED_0x48",
    "PHP_IMPLIED_0x08",
    "PLA_IMPLIED_0x68",
    "PLP_IMPLIED_0x28",

    # ROL
    "ROL_ACCUMULATOR_0x2A",
    "ROL_ZEROPAGE_0x26",
    "ROL_ZEROPAGE_X_0x36",
    "ROL_ABSOLUTE_0x2E",
    "ROL_ABSOLUTE_X_0x3E",

    # ROR
    "ROR_ACCUMULATOR_0x6A",
    "ROR_ZEROPAGE_0x66",
    "ROR_ZEROPAGE_X_0x76",
    "ROR_ABSOLUTE_0x6E",
    "ROR_ABSOLUTE_X_0x7E",

    # SBC
    "SBC_IMMEDIATE_0xE9",
    "SBC_ZEROPAGE_0xE5",
    "SBC_ZEROPAGE_X_0xF5",
    "SBC_ABSOLUTE_0xED",
    "SBC_ABSOLUTE_X_0xFD",
    "SBC_ABSOLUTE_Y_0xF9",
    "SBC_INDEXED_INDIRECT_X_0xE1",
    "SBC_INDIRECT_INDEXED_Y_0xF1",

    # Set Flags
    "SEC_IMPLIED_0x38",
    "SED_IMPLIED_0xF8",
    "SEI_IMPLIED_0x78",

    # Store
    "STA_ZEROPAGE_0x85",
    "STA_ZEROPAGE_X_0x95",
    "STA_ABSOLUTE_0x8D",
    "STA_ABSOLUTE_X_0x9D",
    "STA_ABSOLUTE_Y_0x99",
    "STA_INDEXED_INDIRECT_X_0x81",
    "STA_INDIRECT_INDEXED_Y_0x91",
    "STX_ZEROPAGE_0x86",
    "STX_ZEROPAGE_Y_0x96",
    "STX_ABSOLUTE_0x8E",
    "STY_ZEROPAGE_0x84",
    "STY_ZEROPAGE_X_0x94",
    "STY_ABSOLUTE_0x8C",

    # Transfer
    "TAX_IMPLIED_0xAA",
    "TAY_IMPLIED_0xA8",
    "TSX_IMPLIED_0xBA",
    "TXA_IMPLIED_0x8A",
    "TXS_IMPLIED_0x9A",
    "TYA_IMPLIED_0x98",
]


# InstructionSet enum class
class InstructionSet(enum.IntEnum):
    """Instruction set for the mos6502 CPU.

    Note: This enum is populated dynamically by the registration functions below.
    Members are added via the PseudoEnumMember pattern in each instruction module.

    The _UNINITIALIZED member exists solely to satisfy Python's requirement that
    IntEnum classes have at least one member at definition time.
    """

    _UNINITIALIZED = -1  # Placeholder to allow dynamic member addition

    @classmethod
    def _missing_(cls: type["InstructionSet"], value: int) -> NoReturn:
        raise IllegalCPUInstructionError(f"{value} ({value:02X}) is not a valid {cls}.")


# Initialize instruction map
InstructionSet.map = {}

# Register instruction modules
register_bit_instructions(InstructionSet, InstructionSet.map)
register_brk_instructions(InstructionSet, InstructionSet.map)
register_jmp_instructions(InstructionSet, InstructionSet.map)
register_jsr_instructions(InstructionSet, InstructionSet.map)
register_lda_instructions(InstructionSet, InstructionSet.map)
register_ldx_instructions(InstructionSet, InstructionSet.map)
register_ldy_instructions(InstructionSet, InstructionSet.map)
register_sta_instructions(InstructionSet, InstructionSet.map)
register_stx_instructions(InstructionSet, InstructionSet.map)
register_sty_instructions(InstructionSet, InstructionSet.map)
register_cmp_instructions(InstructionSet, InstructionSet.map)
register_cpx_instructions(InstructionSet, InstructionSet.map)
register_cpy_instructions(InstructionSet, InstructionSet.map)
register_all_logic_instructions(InstructionSet, InstructionSet.map)
register_adc_instructions(InstructionSet, InstructionSet.map)
register_sbc_instructions(InstructionSet, InstructionSet.map)
register_inc_instructions(InstructionSet, InstructionSet.map)
register_dec_instructions(InstructionSet, InstructionSet.map)
register_dex_instructions(InstructionSet, InstructionSet.map)
register_dey_instructions(InstructionSet, InstructionSet.map)
register_inx_instructions(InstructionSet, InstructionSet.map)
register_iny_instructions(InstructionSet, InstructionSet.map)
register_asl_instructions(InstructionSet, InstructionSet.map)
register_lsr_instructions(InstructionSet, InstructionSet.map)
register_rol_instructions(InstructionSet, InstructionSet.map)
register_ror_instructions(InstructionSet, InstructionSet.map)
register_nop_instructions(InstructionSet, InstructionSet.map)
register_rti_instructions(InstructionSet, InstructionSet.map)
register_rts_instructions(InstructionSet, InstructionSet.map)
# Illegal instructions
register_lax_instructions(InstructionSet, InstructionSet.map)
register_sax_instructions(InstructionSet, InstructionSet.map)
register_dcp_instructions(InstructionSet, InstructionSet.map)
register_isc_instructions(InstructionSet, InstructionSet.map)
register_slo_instructions(InstructionSet, InstructionSet.map)
register_rla_instructions(InstructionSet, InstructionSet.map)
register_sre_instructions(InstructionSet, InstructionSet.map)
register_rra_instructions(InstructionSet, InstructionSet.map)
register_anc_instructions(InstructionSet, InstructionSet.map)
register_alr_instructions(InstructionSet, InstructionSet.map)
register_arr_instructions(InstructionSet, InstructionSet.map)
register_sbx_instructions(InstructionSet, InstructionSet.map)
register_las_instructions(InstructionSet, InstructionSet.map)
# register_all_arithmetic_instructions(InstructionSet, InstructionSet.map)  # MIGRATED to adc/sbc/inc/dec packages
register_all_branch_instructions(InstructionSet, InstructionSet.map)  # MIGRATED to individual branch packages
# register_all_compare_instructions(InstructionSet, InstructionSet.map)  # MIGRATED to cmp/cpx/cpy packages
register_all_flag_instructions(InstructionSet, InstructionSet.map)  # MIGRATED to individual flag packages
# register_all_load_instructions(InstructionSet, InstructionSet.map)  # MIGRATED to lda/ldx/ldy packages
# register_all_shift_instructions(InstructionSet, InstructionSet.map)  # MIGRATED to asl/lsr/rol/ror packages
register_all_stack_instructions(InstructionSet, InstructionSet.map)  # MIGRATED to individual stack packages
# register_all_store_instructions(InstructionSet, InstructionSet.map)  # MIGRATED to sta/stx/sty packages
register_all_transfer_instructions(InstructionSet, InstructionSet.map)  # MIGRATED to individual transfer packages


# Build opcode lookup map for variant dispatch
# This maps int opcode values to InstructionOpcode objects with metadata
def _build_opcode_lookup() -> dict[int, InstructionOpcode]:
    """Build lookup map from opcode values to InstructionOpcode objects.

    This allows converting fetched instruction bytes to InstructionOpcode objects
    that carry variant dispatch metadata, enabling cleaner match/case statements.
    """
    import sys
    lookup = {}

    # Get all InstructionOpcode instances from this module
    current_module = sys.modules[__name__]
    for name in dir(current_module):
        obj = getattr(current_module, name)
        if isinstance(obj, InstructionOpcode):
            lookup[int(obj)] = obj

    return lookup


# Build the lookup map after all instructions are imported
OPCODE_LOOKUP = _build_opcode_lookup()
