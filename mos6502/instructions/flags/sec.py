#!/usr/bin/env python3
"""SEC (Set Carry Flag) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#SEC
# Set Carry Flag
#
# 1 -> C
# N	Z	C	I	D	V
# -	-	1	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	SEC	38	1	2
SEC_IMPLIED_0x38: Literal[56] = 0x38


def add_sec_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SEC instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(SEC_IMPLIED_0x38, 'SEC_IMPLIED_0x38')
    instruction_set_class._value2member_map_[SEC_IMPLIED_0x38] = member
    setattr(instruction_set_class, 'SEC_IMPLIED_0x38', SEC_IMPLIED_0x38)


def register_sec_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SEC instructions in the InstructionSet.

    Note: SEC doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_sec_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'SEC_IMPLIED_0x38',
    'register_sec_instructions',
]
