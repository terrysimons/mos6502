#!/usr/bin/env python3
"""INC (Increment Memory) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#INC
# Increment Memory by One
#
# M + 1 -> M
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	INC oper	E6	2	5
# zeropage,X	INC oper,X	F6	2	6
# absolute	INC oper	EE	3	6
# absolute,X	INC oper,X	FE	3	7

INC_ZEROPAGE_0xE6 = InstructionOpcode(
    0xE6,
    "mos6502.instructions.arithmetic._inc",
    "inc_zeropage_0xe6"
)

INC_ZEROPAGE_X_0xF6 = InstructionOpcode(
    0xF6,
    "mos6502.instructions.arithmetic._inc",
    "inc_zeropage_x_0xf6"
)

INC_ABSOLUTE_0xEE = InstructionOpcode(
    0xEE,
    "mos6502.instructions.arithmetic._inc",
    "inc_absolute_0xee"
)

INC_ABSOLUTE_X_0xFE = InstructionOpcode(
    0xFE,
    "mos6502.instructions.arithmetic._inc",
    "inc_absolute_x_0xfe"
)


def add_inc_to_instruction_set_enum(instruction_set_class) -> None:
    """Add INC instructions to the InstructionSet enum dynamically."""
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
        (INC_ZEROPAGE_0xE6, "INC_ZEROPAGE_0xE6"),
        (INC_ZEROPAGE_X_0xF6, "INC_ZEROPAGE_X_0xF6"),
        (INC_ABSOLUTE_0xEE, "INC_ABSOLUTE_0xEE"),
        (INC_ABSOLUTE_X_0xFE, "INC_ABSOLUTE_X_0xFE"),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_inc_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register INC instructions in the InstructionSet."""
    add_inc_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    inc_can_modify_flags: Byte = Byte()
    inc_can_modify_flags[flags.N] = 1
    inc_can_modify_flags[flags.Z] = 1

    instruction_map[INC_ZEROPAGE_0xE6] = {
        "addressing": "zeropage",
        "assembler": "INC {oper}",
        "opc": INC_ZEROPAGE_0xE6,
        "bytes": "2",
        "cycles": "5",
        "flags": inc_can_modify_flags,
    }

    instruction_map[INC_ZEROPAGE_X_0xF6] = {
        "addressing": "zeropage,X",
        "assembler": "INC {oper},X",
        "opc": INC_ZEROPAGE_X_0xF6,
        "bytes": "2",
        "cycles": "6",
        "flags": inc_can_modify_flags,
    }

    instruction_map[INC_ABSOLUTE_0xEE] = {
        "addressing": "absolute",
        "assembler": "INC {oper}",
        "opc": INC_ABSOLUTE_0xEE,
        "bytes": "3",
        "cycles": "6",
        "flags": inc_can_modify_flags,
    }

    instruction_map[INC_ABSOLUTE_X_0xFE] = {
        "addressing": "absolute,X",
        "assembler": "INC {oper},X",
        "opc": INC_ABSOLUTE_X_0xFE,
        "bytes": "3",
        "cycles": "7",
        "flags": inc_can_modify_flags,
    }


__all__ = [
    "INC_ZEROPAGE_0xE6",
    "INC_ZEROPAGE_X_0xF6",
    "INC_ABSOLUTE_0xEE",
    "INC_ABSOLUTE_X_0xFE",
    "register_inc_instructions",
]
