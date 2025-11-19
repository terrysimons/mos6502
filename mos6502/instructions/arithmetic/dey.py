#!/usr/bin/env python3
"""DEY (Decrement Index Y by One) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#DEY
# Decrement Index Y by One
#
# Y - 1 -> Y
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	DEY	88	1	2
DEY_IMPLIED_0x88: Literal[136] = 0x88


def add_dey_to_instruction_set_enum(instruction_set_class) -> None:
    """Add DEY instruction to the InstructionSet enum dynamically."""
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

    dey_member = PseudoEnumMember(DEY_IMPLIED_0x88, 'DEY_IMPLIED_0x88')
    instruction_set_class._value2member_map_[DEY_IMPLIED_0x88] = dey_member
    setattr(instruction_set_class, 'DEY_IMPLIED_0x88', DEY_IMPLIED_0x88)


def register_dey_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register DEY instruction in the InstructionSet.

    Note: DEY doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    add_dey_to_instruction_set_enum(instruction_set_class)


__all__ = ['DEY_IMPLIED_0x88', 'register_dey_instructions']
