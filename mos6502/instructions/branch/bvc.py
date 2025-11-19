#!/usr/bin/env python3
"""BVC (Branch on Overflow Clear) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#BVC
# Branch on Overflow Clear
#
# branch on V = 0
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BVC oper	50	2	2**
BVC_RELATIVE_0x50: Literal[80] = 0x50


def add_bvc_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BVC instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(BVC_RELATIVE_0x50, 'BVC_RELATIVE_0x50')
    instruction_set_class._value2member_map_[BVC_RELATIVE_0x50] = member
    setattr(instruction_set_class, 'BVC_RELATIVE_0x50', BVC_RELATIVE_0x50)


def register_bvc_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BVC instructions in the InstructionSet.

    Note: BVC doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_bvc_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'BVC_RELATIVE_0x50',
    'register_bvc_instructions',
]
