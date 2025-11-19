#!/usr/bin/env python3
"""ROR (Rotate Right) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#ROR
# Rotate One Bit Right (Memory or Accumulator)
#
# C -> [76543210] -> C
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# accumulator	ROR A	6A	1	2
# zeropage	ROR oper	66	2	5
# zeropage,X	ROR oper,X	76	2	6
# absolute	ROR oper	6E	3	6
# absolute,X	ROR oper,X	7E	3	7
ROR_ACCUMULATOR_0x6A: Literal[106] = 0x6A
ROR_ZEROPAGE_0x66: Literal[102] = 0x66
ROR_ZEROPAGE_X_0x76: Literal[118] = 0x76
ROR_ABSOLUTE_0x6E: Literal[110] = 0x6E
ROR_ABSOLUTE_X_0x7E: Literal[126] = 0x7E


def add_ror_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ROR instructions to the InstructionSet enum dynamically."""
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
        (ROR_ACCUMULATOR_0x6A, 'ROR_ACCUMULATOR_0x6A'),
        (ROR_ZEROPAGE_0x66, 'ROR_ZEROPAGE_0x66'),
        (ROR_ZEROPAGE_X_0x76, 'ROR_ZEROPAGE_X_0x76'),
        (ROR_ABSOLUTE_0x6E, 'ROR_ABSOLUTE_0x6E'),
        (ROR_ABSOLUTE_X_0x7E, 'ROR_ABSOLUTE_X_0x7E'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_ror_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ROR instructions in the InstructionSet.

    Note: ROR doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_ror_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'ROR_ACCUMULATOR_0x6A',
    'ROR_ZEROPAGE_0x66',
    'ROR_ZEROPAGE_X_0x76',
    'ROR_ABSOLUTE_0x6E',
    'ROR_ABSOLUTE_X_0x7E',
    'register_ror_instructions',
]
