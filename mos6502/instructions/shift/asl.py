#!/usr/bin/env python3
"""ASL (Arithmetic Shift Left) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#ASL
#
# Shift Left One Bit (Memory or Accumulator)
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# accumulator	ASL A	0A	1	2
# zeropage	ASL oper	06	2	5
# zeropage,X	ASL oper,X	16	2	6
# absolute	ASL oper	0E	3	6
# absolute,X	ASL oper,X	1E	3	7
ASL_ACCUMULATOR_0x0A: Literal[10] = 0x0A
ASL_ZEROPAGE_0x06: Literal[6] = 0x06
ASL_ZEROPAGE_X_0x16: Literal[22] = 0x16
ASL_ABSOLUTE_0x0E: Literal[14] = 0x0E
ASL_ABSOLUTE_X_0x1E: Literal[30] = 0x1E


def add_asl_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ASL instructions to the InstructionSet enum dynamically."""
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
        (ASL_ACCUMULATOR_0x0A, 'ASL_ACCUMULATOR_0x0A'),
        (ASL_ZEROPAGE_0x06, 'ASL_ZEROPAGE_0x06'),
        (ASL_ZEROPAGE_X_0x16, 'ASL_ZEROPAGE_X_0x16'),
        (ASL_ABSOLUTE_0x0E, 'ASL_ABSOLUTE_0x0E'),
        (ASL_ABSOLUTE_X_0x1E, 'ASL_ABSOLUTE_X_0x1E'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_asl_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ASL instructions in the InstructionSet.

    Note: ASL doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_asl_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'ASL_ACCUMULATOR_0x0A',
    'ASL_ZEROPAGE_0x06',
    'ASL_ZEROPAGE_X_0x16',
    'ASL_ABSOLUTE_0x0E',
    'ASL_ABSOLUTE_X_0x1E',
    'register_asl_instructions',
]
