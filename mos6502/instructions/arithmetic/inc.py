#!/usr/bin/env python3
"""INC (Increment Memory by One) instruction."""
from typing import Literal

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
INC_ZEROPAGE_0xE6: Literal[230] = 0xE6
INC_ZEROPAGE_X_0xF6: Literal[246] = 0xF6
INC_ABSOLUTE_0xEE: Literal[238] = 0xEE
INC_ABSOLUTE_X_0xFE: Literal[254] = 0xFE


def add_inc_to_instruction_set_enum(instruction_set_class) -> None:
    """Add INC instructions to the InstructionSet enum dynamically."""
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
        (INC_ZEROPAGE_0xE6, 'INC_ZEROPAGE_0xE6'),
        (INC_ZEROPAGE_X_0xF6, 'INC_ZEROPAGE_X_0xF6'),
        (INC_ABSOLUTE_0xEE, 'INC_ABSOLUTE_0xEE'),
        (INC_ABSOLUTE_X_0xFE, 'INC_ABSOLUTE_X_0xFE'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_inc_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register INC instructions in the InstructionSet.

    Note: INC doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_inc_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'INC_ZEROPAGE_0xE6',
    'INC_ZEROPAGE_X_0xF6',
    'INC_ABSOLUTE_0xEE',
    'INC_ABSOLUTE_X_0xFE',
    'register_inc_instructions',
]
