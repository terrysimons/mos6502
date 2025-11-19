#!/usr/bin/env python3
"""TSX (Transfer Stack Pointer to Index X) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#TSX
# Transfer Stack Pointer to Index X
#
# S -> X
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TSX	BA	1	2
TSX_IMPLIED_0xBA: Literal[186] = 0xBA


def add_tsx_to_instruction_set_enum(instruction_set_class) -> None:
    """Add TSX instruction to the InstructionSet enum dynamically."""
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

    tsx_member = PseudoEnumMember(TSX_IMPLIED_0xBA, 'TSX_IMPLIED_0xBA')
    instruction_set_class._value2member_map_[TSX_IMPLIED_0xBA] = tsx_member
    setattr(instruction_set_class, 'TSX_IMPLIED_0xBA', TSX_IMPLIED_0xBA)


def register_tsx_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register TSX instruction in the InstructionSet.

    Note: TSX doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    add_tsx_to_instruction_set_enum(instruction_set_class)


__all__ = ['TSX_IMPLIED_0xBA', 'register_tsx_instructions']
