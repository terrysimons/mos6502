#!/usr/bin/env python3
"""INY (Increment Index Y by One) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#INY
# Increment Index Y by One
#
# Y + 1 -> Y
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	INY	C8	1	2
INY_IMPLIED_0xC8: Literal[200] = 0xC8


def add_iny_to_instruction_set_enum(instruction_set_class) -> None:
    """Add INY instruction to the InstructionSet enum dynamically."""
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

    iny_member = PseudoEnumMember(INY_IMPLIED_0xC8, 'INY_IMPLIED_0xC8')
    instruction_set_class._value2member_map_[INY_IMPLIED_0xC8] = iny_member
    setattr(instruction_set_class, 'INY_IMPLIED_0xC8', INY_IMPLIED_0xC8)


def register_iny_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register INY instruction in the InstructionSet.

    Note: INY doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    add_iny_to_instruction_set_enum(instruction_set_class)


__all__ = ['INY_IMPLIED_0xC8', 'register_iny_instructions']
