#!/usr/bin/env python3
"""DEC (Decrement Memory by One) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#DEC
# Decrement Memory by One
#
# M - 1 -> M
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	DEC oper	C6	2	5
# zeropage,X	DEC oper,X	D6	2	6
# absolute	DEC oper	CE	3	6
# absolute,X	DEC oper,X	DE	3	7
DEC_ZEROPAGE_0xC6: Literal[198] = 0xC6
DEC_ZEROPAGE_X_0xD6: Literal[214] = 0xD6
DEC_ABSOLUTE_0xCE: Literal[206] = 0xCE
DEC_ABSOLUTE_X_0xDE: Literal[222] = 0xDE


def add_dec_to_instruction_set_enum(instruction_set_class) -> None:
    """Add DEC instructions to the InstructionSet enum dynamically."""
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
        (DEC_ZEROPAGE_0xC6, 'DEC_ZEROPAGE_0xC6'),
        (DEC_ZEROPAGE_X_0xD6, 'DEC_ZEROPAGE_X_0xD6'),
        (DEC_ABSOLUTE_0xCE, 'DEC_ABSOLUTE_0xCE'),
        (DEC_ABSOLUTE_X_0xDE, 'DEC_ABSOLUTE_X_0xDE'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_dec_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register DEC instructions in the InstructionSet.

    Note: DEC doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_dec_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'DEC_ZEROPAGE_0xC6',
    'DEC_ZEROPAGE_X_0xD6',
    'DEC_ABSOLUTE_0xCE',
    'DEC_ABSOLUTE_X_0xDE',
    'register_dec_instructions',
]
