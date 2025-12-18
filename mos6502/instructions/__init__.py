#!/usr/bin/env python3
"""Instruction set for the mos6502 CPU."""
from mos6502.compat import enum
from mos6502.compat import make_dataclass
from mos6502.compat import Literal, NoReturn, List, Dict

from mos6502.errors import IllegalCPUInstructionError


# Addressing mode type alias for documentation and IDE support
AddressingMode = Literal[
    "implied",
    "accumulator",
    "immediate",
    "zeropage",
    "zeropage,X",
    "zeropage,Y",
    "absolute",
    "absolute,X",
    "absolute,Y",
    "(indirect,X)",
    "(indirect),Y",
    "indirect",
    "relative",
]


# Use make_dataclass(frozen, slots) with positional args - kwargs don't work in MicroPython frozen modules
@make_dataclass(True, True)
class CPUInstruction:
    """Metadata for a 6502 CPU instruction opcode.

    This dataclass provides structured, validated metadata for each instruction,
    replacing the untyped dictionaries previously used in instruction_map.

    Attributes
    ----------
        opcode: The instruction opcode byte (0x00-0xFF)
        mnemonic: The instruction mnemonic (e.g., "LDA", "STA", "ADC")
        addressing: The addressing mode used by this opcode variant
        assembler: Format string for disassembly (e.g., "LDA #{oper}")
        bytes: Number of bytes this instruction occupies (1-3)
        base_cycles: Base cycle count for this instruction
        affected_flags: String of flag letters affected (e.g., "NZ", "NVZC")
        package: Python package path for variant dispatch
        function: Function name for variant dispatch
        page_boundary_penalty: True if crossing page boundary adds a cycle

    """

    # Explicit field order for MicroPython compatibility (annotations may not work)
    _field_order_ = ('opcode', 'mnemonic', 'addressing', 'assembler', 'bytes',
                     'base_cycles', 'affected_flags', 'package', 'function',
                     'page_boundary_penalty')
    _field_defaults_ = {'page_boundary_penalty': False}

    opcode: int
    mnemonic: str
    addressing: AddressingMode
    assembler: str
    bytes: int
    base_cycles: int
    affected_flags: str
    package: str
    function: str
    page_boundary_penalty: bool = False

    def __post_init__(self) -> None:
        """Validate instruction metadata after initialization."""
        if not 0x00 <= self.opcode <= 0xFF:
            msg = f"Opcode must be 0x00-0xFF, got: 0x{self.opcode:02X}"
            raise ValueError(msg)

        if not 1 <= self.bytes <= 3:
            msg = f"Bytes must be 1-3, got: {self.bytes}"
            raise ValueError(msg)

        if not 1 <= self.base_cycles <= 8:
            msg = f"Base cycles must be 1-8, got: {self.base_cycles}"
            raise ValueError(msg)

        valid_flags = set("NVBDIZC")
        invalid = set(self.affected_flags) - valid_flags
        if invalid:
            msg = f"Invalid flag characters: {invalid}"
            raise ValueError(msg)

    @property
    def name(self) -> str:
        """Generate canonical name like LDA_IMMEDIATE_0xA9."""
        addr_map = {
            "implied": "IMPLIED",
            "accumulator": "ACCUMULATOR",
            "immediate": "IMMEDIATE",
            "zeropage": "ZEROPAGE",
            "zeropage,X": "ZEROPAGE_X",
            "zeropage,Y": "ZEROPAGE_Y",
            "absolute": "ABSOLUTE",
            "absolute,X": "ABSOLUTE_X",
            "absolute,Y": "ABSOLUTE_Y",
            "(indirect,X)": "INDEXED_INDIRECT_X",
            "(indirect),Y": "INDIRECT_INDEXED_Y",
            "indirect": "INDIRECT",
            "relative": "RELATIVE",
        }
        addr_name = addr_map.get(self.addressing, self.addressing.upper())
        return f"{self.mnemonic}_{addr_name}_0x{self.opcode:02X}"

    @property
    def cycles_display(self) -> str:
        """Return cycles as display string (e.g., '4' or '4*' for page penalty)."""
        if self.page_boundary_penalty:
            return f"{self.base_cycles}*"
        return str(self.base_cycles)

    @property
    def affects_n(self) -> bool:
        """True if instruction affects Negative flag."""
        return "N" in self.affected_flags

    @property
    def affects_v(self) -> bool:
        """True if instruction affects Overflow flag."""
        return "V" in self.affected_flags

    @property
    def affects_z(self) -> bool:
        """True if instruction affects Zero flag."""
        return "Z" in self.affected_flags

    @property
    def affects_c(self) -> bool:
        """True if instruction affects Carry flag."""
        return "C" in self.affected_flags

    @property
    def affects_i(self) -> bool:
        """True if instruction affects Interrupt Disable flag."""
        return "I" in self.affected_flags

    @property
    def affects_d(self) -> bool:
        """True if instruction affects Decimal flag."""
        return "D" in self.affected_flags

    def to_legacy_dict(self) -> dict:
        """Convert to legacy instruction_map dictionary format."""
        from mos6502 import flags as flag_bits
        from mos6502.memory import Byte

        flags_byte = Byte()
        if self.affects_n:
            flags_byte[flag_bits.N] = 1
        if self.affects_v:
            flags_byte[flag_bits.V] = 1
        if self.affects_z:
            flags_byte[flag_bits.Z] = 1
        if self.affects_c:
            flags_byte[flag_bits.C] = 1
        if self.affects_i:
            flags_byte[flag_bits.I] = 1
        if self.affects_d:
            flags_byte[flag_bits.D] = 1

        return {
            "addressing": self.addressing,
            "assembler": self.assembler,
            "opc": self.opcode,
            "bytes": str(self.bytes),
            "cycles": self.cycles_display,
            "flags": flags_byte,
        }

    def __int__(self) -> int:
        """Allow using CPUInstruction where an int opcode is expected."""
        return self.opcode

    def __hash__(self) -> int:
        """Hash by opcode for use in sets and as dict keys."""
        return hash(self.opcode)


class PseudoEnumMember:
    """Allows dynamic addition of members to IntEnum classes.

    Note: Does not inherit from int for MicroPython compatibility.
    Implements __int__, __eq__, __hash__, and __index__ to behave like an int.
    """

    __slots__ = ('_value_', '_name')

    def __init__(self, value: int, name: str) -> None:
        """Create a pseudo-enum member with the given value and name."""
        self._value_ = value
        self._name = name

    @property
    def name(self) -> str:
        """Return the member name."""
        return self._name

    @property
    def value(self) -> int:
        """Return the member value."""
        return self._value_

    def __int__(self) -> int:
        """Return the integer value."""
        return self._value_

    def __eq__(self, other: object) -> bool:
        """Compare equality with int or another PseudoEnumMember."""
        if isinstance(other, int):
            return self._value_ == other
        if isinstance(other, PseudoEnumMember):
            return self._value_ == other._value_
        return NotImplemented

    def __hash__(self) -> int:
        """Hash by value for use in sets and as dict keys."""
        return hash(self._value_)

    def __index__(self) -> int:
        """Allow use in slices and hex()."""
        return self._value_

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<{self._name}: {self._value_}>"


def register_instruction(
    instruction: CPUInstruction,
    instruction_set_class: type,
    instruction_map: dict,
) -> None:
    """Register a single instruction in the InstructionSet enum and map."""
    member = PseudoEnumMember(instruction.opcode, instruction.name)
    instruction_set_class._value2member_map_[instruction.opcode] = member
    setattr(instruction_set_class, instruction.name, instruction.opcode)
    instruction_map[instruction.opcode] = instruction.to_legacy_dict()


def register_instructions(
    instructions: List[CPUInstruction],
    instruction_set_class: type,
    instruction_map: dict,
) -> None:
    """Register multiple instructions in the InstructionSet enum and map."""
    for instruction in instructions:
        register_instruction(instruction, instruction_set_class, instruction_map)


class InstructionOpcode:
    """Instruction opcode that carries its variant metadata.

    This class stores the opcode value and carries package and function names
    for variant dispatch, while remaining compatible with code that expects integers.

    Note: Does not inherit from int for MicroPython compatibility.
    Implements __int__, __eq__, __hash__, and __index__ to behave like an int.

    Example:
    -------
        NOP_IMPLIED_0xEA = InstructionOpcode(
            0xEA,
            "mos6502.instructions.nop",
            "nop_implied_0xea"
        )
    """

    __slots__ = ('_value', 'package', 'function')

    def __init__(self, value: int, package: str, function: str) -> None:
        """Create instruction opcode with metadata.

        Arguments:
        ---------
            value: The opcode value (e.g., 0xEA)
            package: Package name (e.g., "mos6502.instructions.nop")
            function: Function name (e.g., "nop_implied_0xea")
        """
        self._value = value
        self.package = package
        self.function = function

    def __int__(self) -> int:
        """Return the integer opcode value."""
        return self._value

    def __eq__(self, other: object) -> bool:
        """Compare equality with int or another InstructionOpcode."""
        if isinstance(other, int):
            return self._value == other
        if isinstance(other, InstructionOpcode):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        """Hash by opcode value for use in sets and as dict keys."""
        return hash(self._value)

    def __index__(self) -> int:
        """Allow use in slices and hex()."""
        return self._value

    def __repr__(self) -> str:
        """Return string representation."""
        return f"InstructionOpcode(0x{self._value:02X}, {self.package!r}, {self.function!r})"

# Import from individual instruction modules
from mos6502.instructions._bit import BIT_ZEROPAGE_0x24, BIT_ABSOLUTE_0x2C, register_bit_instructions
from mos6502.instructions._brk import BRK_IMPLIED_0x00, register_brk_instructions
# Illegal instructions - optional for MicroPython/Pico (memory constrained)
# These imports are wrapped in try/except so they gracefully fail on Pico
# where the illegal instruction modules are not deployed to save memory.
_ILLEGAL_INSTRUCTIONS_AVAILABLE = False
try:
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
    from mos6502.instructions.illegal._sbc_illegal import (
        SBC_IMMEDIATE_0xEB,
        register_sbc_illegal_instructions,
    )
    from mos6502.instructions.illegal._ane import (
        ANE_IMMEDIATE_0x8B,
        register_ane_instructions,
    )
    from mos6502.instructions.illegal._sha import (
        SHA_INDIRECT_INDEXED_Y_0x93,
        SHA_ABSOLUTE_Y_0x9F,
        register_sha_instructions,
    )
    from mos6502.instructions.illegal._shx import (
        SHX_ABSOLUTE_Y_0x9E,
        register_shx_instructions,
    )
    from mos6502.instructions.illegal._shy import (
        SHY_ABSOLUTE_X_0x9C,
        register_shy_instructions,
    )
    from mos6502.instructions.illegal._tas import (
        TAS_ABSOLUTE_Y_0x9B,
        register_tas_instructions,
    )
    from mos6502.instructions.illegal._jam import (
        JAM_IMPLIED_0x02,
        JAM_IMPLIED_0x12,
        JAM_IMPLIED_0x22,
        JAM_IMPLIED_0x32,
        JAM_IMPLIED_0x42,
        JAM_IMPLIED_0x52,
        JAM_IMPLIED_0x62,
        JAM_IMPLIED_0x72,
        JAM_IMPLIED_0x92,
        JAM_IMPLIED_0xB2,
        JAM_IMPLIED_0xD2,
        JAM_IMPLIED_0xF2,
        register_jam_instructions,
    )
    from mos6502.instructions.illegal._nop_illegal import (
        # 1-byte implied
        NOP_IMPLIED_0x1A,
        NOP_IMPLIED_0x3A,
        NOP_IMPLIED_0x5A,
        NOP_IMPLIED_0x7A,
        NOP_IMPLIED_0xDA,
        NOP_IMPLIED_0xFA,
        # 2-byte immediate
        NOP_IMMEDIATE_0x80,
        NOP_IMMEDIATE_0x82,
        NOP_IMMEDIATE_0x89,
        NOP_IMMEDIATE_0xC2,
        NOP_IMMEDIATE_0xE2,
        # 2-byte zero page
        NOP_ZEROPAGE_0x04,
        NOP_ZEROPAGE_0x44,
        NOP_ZEROPAGE_0x64,
        # 2-byte zero page,X
        NOP_ZEROPAGE_X_0x14,
        NOP_ZEROPAGE_X_0x34,
        NOP_ZEROPAGE_X_0x54,
        NOP_ZEROPAGE_X_0x74,
        NOP_ZEROPAGE_X_0xD4,
        NOP_ZEROPAGE_X_0xF4,
        # 3-byte absolute
        NOP_ABSOLUTE_0x0C,
        # 3-byte absolute,X
        NOP_ABSOLUTE_X_0x1C,
        NOP_ABSOLUTE_X_0x3C,
        NOP_ABSOLUTE_X_0x5C,
        NOP_ABSOLUTE_X_0x7C,
        NOP_ABSOLUTE_X_0xDC,
        NOP_ABSOLUTE_X_0xFC,
        register_nop_illegal_instructions,
    )
    _ILLEGAL_INSTRUCTIONS_AVAILABLE = True
except ImportError:
    # Illegal instructions not available (MicroPython/Pico deployment)
    pass
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
    # Core classes and helpers
    "CPUInstruction",
    "PseudoEnumMember",
    "register_instruction",
    "register_instructions",
    "InstructionOpcode",
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
    "BCC_RELATIVE_0x90",
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

    # Illegal: SBC duplicate
    "SBC_IMMEDIATE_0xEB",

    # Illegal: ANE (XAA) - Highly Unstable
    "ANE_IMMEDIATE_0x8B",

    # Illegal: SHA (AHX) - Unstable
    "SHA_INDIRECT_INDEXED_Y_0x93",
    "SHA_ABSOLUTE_Y_0x9F",

    # Illegal: SHX (SXA) - Unstable
    "SHX_ABSOLUTE_Y_0x9E",

    # Illegal: SHY (SYA) - Unstable
    "SHY_ABSOLUTE_X_0x9C",

    # Illegal: TAS (XAS, SHS) - Unstable
    "TAS_ABSOLUTE_Y_0x9B",

    # Illegal: JAM (KIL, HLT) - Halts CPU
    "JAM_IMPLIED_0x02",
    "JAM_IMPLIED_0x12",
    "JAM_IMPLIED_0x22",
    "JAM_IMPLIED_0x32",
    "JAM_IMPLIED_0x42",
    "JAM_IMPLIED_0x52",
    "JAM_IMPLIED_0x62",
    "JAM_IMPLIED_0x72",
    "JAM_IMPLIED_0x92",
    "JAM_IMPLIED_0xB2",
    "JAM_IMPLIED_0xD2",
    "JAM_IMPLIED_0xF2",

    # Illegal: NOP variants
    "NOP_IMPLIED_0x1A",
    "NOP_IMPLIED_0x3A",
    "NOP_IMPLIED_0x5A",
    "NOP_IMPLIED_0x7A",
    "NOP_IMPLIED_0xDA",
    "NOP_IMPLIED_0xFA",
    "NOP_IMMEDIATE_0x80",
    "NOP_IMMEDIATE_0x82",
    "NOP_IMMEDIATE_0x89",
    "NOP_IMMEDIATE_0xC2",
    "NOP_IMMEDIATE_0xE2",
    "NOP_ZEROPAGE_0x04",
    "NOP_ZEROPAGE_0x44",
    "NOP_ZEROPAGE_0x64",
    "NOP_ZEROPAGE_X_0x14",
    "NOP_ZEROPAGE_X_0x34",
    "NOP_ZEROPAGE_X_0x54",
    "NOP_ZEROPAGE_X_0x74",
    "NOP_ZEROPAGE_X_0xD4",
    "NOP_ZEROPAGE_X_0xF4",
    "NOP_ABSOLUTE_0x0C",
    "NOP_ABSOLUTE_X_0x1C",
    "NOP_ABSOLUTE_X_0x3C",
    "NOP_ABSOLUTE_X_0x5C",
    "NOP_ABSOLUTE_X_0x7C",
    "NOP_ABSOLUTE_X_0xDC",
    "NOP_ABSOLUTE_X_0xFC",

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


# Initialize instruction map and _value2member_map_ (needed for MicroPython compatibility)
InstructionSet.map = {}
InstructionSet._value2member_map_ = {}

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
# Illegal instructions - only register if available (not on MicroPython/Pico)
if _ILLEGAL_INSTRUCTIONS_AVAILABLE:
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
    register_nop_illegal_instructions(InstructionSet, InstructionSet.map)
    register_sbc_illegal_instructions(InstructionSet, InstructionSet.map)
    register_ane_instructions(InstructionSet, InstructionSet.map)
    register_sha_instructions(InstructionSet, InstructionSet.map)
    register_shx_instructions(InstructionSet, InstructionSet.map)
    register_shy_instructions(InstructionSet, InstructionSet.map)
    register_tas_instructions(InstructionSet, InstructionSet.map)
    register_jam_instructions(InstructionSet, InstructionSet.map)
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
def _build_opcode_lookup() -> Dict[int, InstructionOpcode]:
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
