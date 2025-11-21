#!/usr/bin/env python3
"""CMP (Compare Accumulator) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#CMP
# Compare Accumulator with Memory
#
# A - M (affects flags only, doesn't store result)
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	CMP #oper	C9	2	2
# zeropage	CMP oper	C5	2	3
# zeropage,X	CMP oper,X	D5	2	4
# absolute	CMP oper	CD	3	4
# absolute,X	CMP oper,X	DD	3	4*
# absolute,Y	CMP oper,Y	D9	3	4*
# (indirect,X)	CMP (oper,X)	C1	2	6
# (indirect),Y	CMP (oper),Y	D1	2	5*

CMP_IMMEDIATE_0xC9 = InstructionOpcode(
    0xC9,
    "mos6502.instructions.compare._cmp",
    "cmp_immediate_0xc9"
)

CMP_ZEROPAGE_0xC5 = InstructionOpcode(
    0xC5,
    "mos6502.instructions.compare._cmp",
    "cmp_zeropage_0xc5"
)

CMP_ZEROPAGE_X_0xD5 = InstructionOpcode(
    0xD5,
    "mos6502.instructions.compare._cmp",
    "cmp_zeropage_x_0xd5"
)

CMP_ABSOLUTE_0xCD = InstructionOpcode(
    0xCD,
    "mos6502.instructions.compare._cmp",
    "cmp_absolute_0xcd"
)

CMP_ABSOLUTE_X_0xDD = InstructionOpcode(
    0xDD,
    "mos6502.instructions.compare._cmp",
    "cmp_absolute_x_0xdd"
)

CMP_ABSOLUTE_Y_0xD9 = InstructionOpcode(
    0xD9,
    "mos6502.instructions.compare._cmp",
    "cmp_absolute_y_0xd9"
)

CMP_INDEXED_INDIRECT_X_0xC1 = InstructionOpcode(
    0xC1,
    "mos6502.instructions.compare._cmp",
    "cmp_indexed_indirect_x_0xc1"
)

CMP_INDIRECT_INDEXED_Y_0xD1 = InstructionOpcode(
    0xD1,
    "mos6502.instructions.compare._cmp",
    "cmp_indirect_indexed_y_0xd1"
)


def add_cmp_to_instruction_set_enum(instruction_set_class) -> None:
    """Add CMP instructions to the InstructionSet enum dynamically."""
    class PseudoEnumMember(int):
        def __new__(cls, value, name):
            obj = int.__new__(cls, value)
            obj._name = name
            obj._value_ = value
            return obj

        @property
        def name(self):
            return self._name

        @property
        def value(self):
            return self._value_

    for value, name in [
        (CMP_IMMEDIATE_0xC9, "CMP_IMMEDIATE_0xC9"),
        (CMP_ZEROPAGE_0xC5, "CMP_ZEROPAGE_0xC5"),
        (CMP_ZEROPAGE_X_0xD5, "CMP_ZEROPAGE_X_0xD5"),
        (CMP_ABSOLUTE_0xCD, "CMP_ABSOLUTE_0xCD"),
        (CMP_ABSOLUTE_X_0xDD, "CMP_ABSOLUTE_X_0xDD"),
        (CMP_ABSOLUTE_Y_0xD9, "CMP_ABSOLUTE_Y_0xD9"),
        (CMP_INDEXED_INDIRECT_X_0xC1, "CMP_INDEXED_INDIRECT_X_0xC1"),
        (CMP_INDIRECT_INDEXED_Y_0xD1, "CMP_INDIRECT_INDEXED_Y_0xD1"),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_cmp_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register CMP instructions in the InstructionSet."""
    add_cmp_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    cmp_can_modify_flags: Byte = Byte()
    cmp_can_modify_flags[flags.N] = 1
    cmp_can_modify_flags[flags.Z] = 1
    cmp_can_modify_flags[flags.C] = 1

    instruction_map[CMP_IMMEDIATE_0xC9] = {
        "addressing": "immediate",
        "assembler": "CMP #{oper}",
        "opc": CMP_IMMEDIATE_0xC9,
        "bytes": "2",
        "cycles": "2",
        "flags": cmp_can_modify_flags,
    }

    instruction_map[CMP_ZEROPAGE_0xC5] = {
        "addressing": "zeropage",
        "assembler": "CMP {oper}",
        "opc": CMP_ZEROPAGE_0xC5,
        "bytes": "2",
        "cycles": "3",
        "flags": cmp_can_modify_flags,
    }

    instruction_map[CMP_ZEROPAGE_X_0xD5] = {
        "addressing": "zeropage,X",
        "assembler": "CMP {oper},X",
        "opc": CMP_ZEROPAGE_X_0xD5,
        "bytes": "2",
        "cycles": "4",
        "flags": cmp_can_modify_flags,
    }

    instruction_map[CMP_ABSOLUTE_0xCD] = {
        "addressing": "absolute",
        "assembler": "CMP {oper}",
        "opc": CMP_ABSOLUTE_0xCD,
        "bytes": "3",
        "cycles": "4",
        "flags": cmp_can_modify_flags,
    }

    instruction_map[CMP_ABSOLUTE_X_0xDD] = {
        "addressing": "absolute,X",
        "assembler": "CMP {oper},X",
        "opc": CMP_ABSOLUTE_X_0xDD,
        "bytes": "3",
        "cycles": "4*",
        "flags": cmp_can_modify_flags,
    }

    instruction_map[CMP_ABSOLUTE_Y_0xD9] = {
        "addressing": "absolute,Y",
        "assembler": "CMP {oper},Y",
        "opc": CMP_ABSOLUTE_Y_0xD9,
        "bytes": "3",
        "cycles": "4*",
        "flags": cmp_can_modify_flags,
    }

    instruction_map[CMP_INDEXED_INDIRECT_X_0xC1] = {
        "addressing": "(indirect,X)",
        "assembler": "CMP ({oper},X)",
        "opc": CMP_INDEXED_INDIRECT_X_0xC1,
        "bytes": "2",
        "cycles": "6",
        "flags": cmp_can_modify_flags,
    }

    instruction_map[CMP_INDIRECT_INDEXED_Y_0xD1] = {
        "addressing": "(indirect),Y",
        "assembler": "CMP ({oper}),Y",
        "opc": CMP_INDIRECT_INDEXED_Y_0xD1,
        "bytes": "2",
        "cycles": "5*",
        "flags": cmp_can_modify_flags,
    }


__all__ = [
    "CMP_IMMEDIATE_0xC9",
    "CMP_ZEROPAGE_0xC5",
    "CMP_ZEROPAGE_X_0xD5",
    "CMP_ABSOLUTE_0xCD",
    "CMP_ABSOLUTE_X_0xDD",
    "CMP_ABSOLUTE_Y_0xD9",
    "CMP_INDEXED_INDIRECT_X_0xC1",
    "CMP_INDIRECT_INDEXED_Y_0xD1",
    "register_cmp_instructions",
]
