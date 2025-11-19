#!/usr/bin/env python3
"""RTI (Return from Interrupt) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#RTI
# Return from Interrupt
#
# The status register is pulled with the break flag
# and bit 5 ignored. Then PC is pulled from the stack.
#
# pull SR, pull PC
# N	Z	C	I	D	V
# from stack
# addressing	assembler	opc	bytes	cycles
# implied	RTI	40	1	6
RTI_IMPLIED_0x40: Literal[64] = 0x40


def add_rti_to_instruction_set_enum(instruction_set_class) -> None:
    """Add RTI instruction to the InstructionSet enum dynamically."""
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

    rti_member = PseudoEnumMember(RTI_IMPLIED_0x40, 'RTI_IMPLIED_0x40')
    instruction_set_class._value2member_map_[RTI_IMPLIED_0x40] = rti_member
    setattr(instruction_set_class, 'RTI_IMPLIED_0x40', RTI_IMPLIED_0x40)


def register_rti_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register RTI instruction in the InstructionSet.

    Note: RTI doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    # Add to enum
    add_rti_to_instruction_set_enum(instruction_set_class)


__all__ = ['RTI_IMPLIED_0x40', 'register_rti_instructions']
