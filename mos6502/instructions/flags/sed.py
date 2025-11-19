#!/usr/bin/env python3
"""SED (Set Decimal Flag) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#SED
# Set Decimal Flag
#
# 1 -> D
# N	Z	C	I	D	V
# -	-	-	-	1	-
# addressing	assembler	opc	bytes	cycles
# implied	SED	F8	1	2
SED_IMPLIED_0xF8: Literal[248] = 0xF8


def add_sed_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SED instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(SED_IMPLIED_0xF8, 'SED_IMPLIED_0xF8')
    instruction_set_class._value2member_map_[SED_IMPLIED_0xF8] = member
    setattr(instruction_set_class, 'SED_IMPLIED_0xF8', SED_IMPLIED_0xF8)


def register_sed_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SED instructions in the InstructionSet.

    Note: SED doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_sed_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'SED_IMPLIED_0xF8',
    'register_sed_instructions',
]
