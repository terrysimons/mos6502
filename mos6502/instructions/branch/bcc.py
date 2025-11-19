#!/usr/bin/env python3
"""BCC (Branch on Carry Clear) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#BCC
#
# Branch on Carry Clear
# branch on C = 0
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BCC oper	90	2	2**
BCC_RELATIVE_0x90: Literal[144] = 0x90


def add_bcc_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BCC instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(BCC_RELATIVE_0x90, 'BCC_RELATIVE_0x90')
    instruction_set_class._value2member_map_[BCC_RELATIVE_0x90] = member
    setattr(instruction_set_class, 'BCC_RELATIVE_0x90', BCC_RELATIVE_0x90)


def register_bcc_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BCC instructions in the InstructionSet.

    Note: BCC doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_bcc_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'BCC_RELATIVE_0x90',
    'register_bcc_instructions',
]
