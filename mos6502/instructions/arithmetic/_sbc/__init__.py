#!/usr/bin/env python3
"""SBC (Subtract with Carry) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#SBC
# Subtract Memory from Accumulator with Borrow
#
# A - M - C̄ -> A
# N	Z	C	I	D	V
# +	+	+	-	-	+
# addressing	assembler	opc	bytes	cycles
# immediate	SBC #oper	E9	2	2
# zeropage	SBC oper	E5	2	3
# zeropage,X	SBC oper,X	F5	2	4
# absolute	SBC oper	ED	3	4
# absolute,X	SBC oper,X	FD	3	4*
# absolute,Y	SBC oper,Y	F9	3	4*
# (indirect,X)	SBC (oper,X)	E1	2	6
# (indirect),Y	SBC (oper),Y	F1	2	5*

SBC_IMMEDIATE_0xE9 = InstructionOpcode(
    0xE9,
    "mos6502.instructions.arithmetic._sbc",
    "sbc_immediate_0xe9"
)

SBC_ZEROPAGE_0xE5 = InstructionOpcode(
    0xE5,
    "mos6502.instructions.arithmetic._sbc",
    "sbc_zeropage_0xe5"
)

SBC_ZEROPAGE_X_0xF5 = InstructionOpcode(
    0xF5,
    "mos6502.instructions.arithmetic._sbc",
    "sbc_zeropage_x_0xf5"
)

SBC_ABSOLUTE_0xED = InstructionOpcode(
    0xED,
    "mos6502.instructions.arithmetic._sbc",
    "sbc_absolute_0xed"
)

SBC_ABSOLUTE_X_0xFD = InstructionOpcode(
    0xFD,
    "mos6502.instructions.arithmetic._sbc",
    "sbc_absolute_x_0xfd"
)

SBC_ABSOLUTE_Y_0xF9 = InstructionOpcode(
    0xF9,
    "mos6502.instructions.arithmetic._sbc",
    "sbc_absolute_y_0xf9"
)

SBC_INDEXED_INDIRECT_X_0xE1 = InstructionOpcode(
    0xE1,
    "mos6502.instructions.arithmetic._sbc",
    "sbc_indexed_indirect_x_0xe1"
)

SBC_INDIRECT_INDEXED_Y_0xF1 = InstructionOpcode(
    0xF1,
    "mos6502.instructions.arithmetic._sbc",
    "sbc_indirect_indexed_y_0xf1"
)


def add_sbc_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SBC instructions to the InstructionSet enum dynamically."""
    class PseudoEnumMember(int):
        def __new__(cls, value, name) -> "InstructionSet":
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
        (SBC_IMMEDIATE_0xE9, "SBC_IMMEDIATE_0xE9"),
        (SBC_ZEROPAGE_0xE5, "SBC_ZEROPAGE_0xE5"),
        (SBC_ZEROPAGE_X_0xF5, "SBC_ZEROPAGE_X_0xF5"),
        (SBC_ABSOLUTE_0xED, "SBC_ABSOLUTE_0xED"),
        (SBC_ABSOLUTE_X_0xFD, "SBC_ABSOLUTE_X_0xFD"),
        (SBC_ABSOLUTE_Y_0xF9, "SBC_ABSOLUTE_Y_0xF9"),
        (SBC_INDEXED_INDIRECT_X_0xE1, "SBC_INDEXED_INDIRECT_X_0xE1"),
        (SBC_INDIRECT_INDEXED_Y_0xF1, "SBC_INDIRECT_INDEXED_Y_0xF1"),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_sbc_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SBC instructions in the InstructionSet."""
    add_sbc_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    sbc_can_modify_flags: Byte = Byte()
    sbc_can_modify_flags[flags.N] = 1
    sbc_can_modify_flags[flags.Z] = 1
    sbc_can_modify_flags[flags.C] = 1
    sbc_can_modify_flags[flags.V] = 1

    instruction_map[SBC_IMMEDIATE_0xE9] = {
        "addressing": "immediate",
        "assembler": "SBC #{oper}",
        "opc": SBC_IMMEDIATE_0xE9,
        "bytes": "2",
        "cycles": "2",
        "flags": sbc_can_modify_flags,
    }

    instruction_map[SBC_ZEROPAGE_0xE5] = {
        "addressing": "zeropage",
        "assembler": "SBC {oper}",
        "opc": SBC_ZEROPAGE_0xE5,
        "bytes": "2",
        "cycles": "3",
        "flags": sbc_can_modify_flags,
    }

    instruction_map[SBC_ZEROPAGE_X_0xF5] = {
        "addressing": "zeropage,X",
        "assembler": "SBC {oper},X",
        "opc": SBC_ZEROPAGE_X_0xF5,
        "bytes": "2",
        "cycles": "4",
        "flags": sbc_can_modify_flags,
    }

    instruction_map[SBC_ABSOLUTE_0xED] = {
        "addressing": "absolute",
        "assembler": "SBC {oper}",
        "opc": SBC_ABSOLUTE_0xED,
        "bytes": "3",
        "cycles": "4",
        "flags": sbc_can_modify_flags,
    }

    instruction_map[SBC_ABSOLUTE_X_0xFD] = {
        "addressing": "absolute,X",
        "assembler": "SBC {oper},X",
        "opc": SBC_ABSOLUTE_X_0xFD,
        "bytes": "3",
        "cycles": "4*",
        "flags": sbc_can_modify_flags,
    }

    instruction_map[SBC_ABSOLUTE_Y_0xF9] = {
        "addressing": "absolute,Y",
        "assembler": "SBC {oper},Y",
        "opc": SBC_ABSOLUTE_Y_0xF9,
        "bytes": "3",
        "cycles": "4*",
        "flags": sbc_can_modify_flags,
    }

    instruction_map[SBC_INDEXED_INDIRECT_X_0xE1] = {
        "addressing": "(indirect,X)",
        "assembler": "SBC ({oper},X)",
        "opc": SBC_INDEXED_INDIRECT_X_0xE1,
        "bytes": "2",
        "cycles": "6",
        "flags": sbc_can_modify_flags,
    }

    instruction_map[SBC_INDIRECT_INDEXED_Y_0xF1] = {
        "addressing": "(indirect),Y",
        "assembler": "SBC ({oper}),Y",
        "opc": SBC_INDIRECT_INDEXED_Y_0xF1,
        "bytes": "2",
        "cycles": "5*",
        "flags": sbc_can_modify_flags,
    }


__all__ = [
    "SBC_IMMEDIATE_0xE9",
    "SBC_ZEROPAGE_0xE5",
    "SBC_ZEROPAGE_X_0xF5",
    "SBC_ABSOLUTE_0xED",
    "SBC_ABSOLUTE_X_0xFD",
    "SBC_ABSOLUTE_Y_0xF9",
    "SBC_INDEXED_INDIRECT_X_0xE1",
    "SBC_INDIRECT_INDEXED_Y_0xF1",
    "register_sbc_instructions",
]
