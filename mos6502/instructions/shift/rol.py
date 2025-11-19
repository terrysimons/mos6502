#!/usr/bin/env python3
"""ROL (Rotate Left) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#ROL
# Rotate One Bit Left (Memory or Accumulator)
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# accumulator	ROL A	2A	1	2
# zeropage	ROL oper	26	2	5
# zeropage,X	ROL oper,X	36	2	6
# absolute	ROL oper	2E	3	6
# absolute,X	ROL oper,X	3E	3	7
ROL_ACCUMULATOR_0x2A: Literal[42] = 0x2A
ROL_ZEROPAGE_0x26: Literal[38] = 0x26
ROL_ZEROPAGE_X_0x36: Literal[54] = 0x36
ROL_ABSOLUTE_0x2E: Literal[46] = 0x2E
ROL_ABSOLUTE_X_0x3E: Literal[62] = 0x3E


def add_rol_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ROL instructions to the InstructionSet enum dynamically."""
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
        (ROL_ACCUMULATOR_0x2A, 'ROL_ACCUMULATOR_0x2A'),
        (ROL_ZEROPAGE_0x26, 'ROL_ZEROPAGE_0x26'),
        (ROL_ZEROPAGE_X_0x36, 'ROL_ZEROPAGE_X_0x36'),
        (ROL_ABSOLUTE_0x2E, 'ROL_ABSOLUTE_0x2E'),
        (ROL_ABSOLUTE_X_0x3E, 'ROL_ABSOLUTE_X_0x3E'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_rol_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ROL instructions in the InstructionSet.

    Note: ROL doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_rol_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'ROL_ACCUMULATOR_0x2A',
    'ROL_ZEROPAGE_0x26',
    'ROL_ZEROPAGE_X_0x36',
    'ROL_ABSOLUTE_0x2E',
    'ROL_ABSOLUTE_X_0x3E',
    'register_rol_instructions',
]
