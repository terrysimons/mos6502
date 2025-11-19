#!/usr/bin/env python3
"""TAY (Transfer Accumulator to Index Y) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#TAY
# Transfer Accumulator to Index Y
#
# A -> Y
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TAY	A8	1	2
TAY_IMPLIED_0xA8: Literal[168] = 0xA8


def add_tay_to_instruction_set_enum(instruction_set_class) -> None:
    """Add TAY instruction to the InstructionSet enum dynamically."""
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

    tay_member = PseudoEnumMember(TAY_IMPLIED_0xA8, 'TAY_IMPLIED_0xA8')
    instruction_set_class._value2member_map_[TAY_IMPLIED_0xA8] = tay_member
    setattr(instruction_set_class, 'TAY_IMPLIED_0xA8', TAY_IMPLIED_0xA8)


def register_tay_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register TAY instruction in the InstructionSet.

    Note: TAY doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    add_tay_to_instruction_set_enum(instruction_set_class)


__all__ = ['TAY_IMPLIED_0xA8', 'register_tay_instructions']
