#!/usr/bin/env python3
"""SEI (Set Interrupt Disable Status) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#SEI
# Set Interrupt Disable Status
#
# 1 -> I
# N	Z	C	I	D	V
# -	-	-	1	-	-
# addressing	assembler	opc	bytes	cycles
# implied	SEI	78	1	2
SEI_IMPLIED_0x78: Literal[120] = 0x78


def add_sei_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SEI instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(SEI_IMPLIED_0x78, 'SEI_IMPLIED_0x78')
    instruction_set_class._value2member_map_[SEI_IMPLIED_0x78] = member
    setattr(instruction_set_class, 'SEI_IMPLIED_0x78', SEI_IMPLIED_0x78)


def register_sei_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SEI instructions in the InstructionSet.

    Note: SEI doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_sei_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'SEI_IMPLIED_0x78',
    'register_sei_instructions',
]
