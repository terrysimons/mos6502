#!/usr/bin/env python3
"""BRK (Force Break) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#BRK
# Force Break
#
# BRK initiates a software interrupt similar to a hardware
# interrupt (IRQ). The return address pushed to the stack is
# PC+2, providing an extra byte of spacing for a break mark
# (identifying a reason for the break.)
# The status register will be pushed to the stack with the break
# flag set to 1. However, when retrieved during RTI or by a PLP
# instruction, the break flag will be ignored.
# The interrupt disable flag is not set automatically.
#
# interrupt,
# push PC+2, push SR
# N	Z	C	I	D	V
# -	-	-	1	-	-
# addressing	assembler	opc	bytes	cycles
# implied	BRK	00	1	7
BRK_IMPLIED_0x00: Literal[0] = 0x00


def add_brk_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BRK instruction to the InstructionSet enum dynamically."""
    # Create a pseudo-enum member that has a .name attribute
    # We can't create a true enum member after class definition, but we can
    # create an object that behaves like one for lookup purposes
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

    brk_member = PseudoEnumMember(BRK_IMPLIED_0x00, 'BRK_IMPLIED_0x00')
    instruction_set_class._value2member_map_[BRK_IMPLIED_0x00] = brk_member
    setattr(instruction_set_class, 'BRK_IMPLIED_0x00', BRK_IMPLIED_0x00)


def register_brk_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BRK instruction in the InstructionSet enum.

    Note: BRK doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    # Add to enum
    add_brk_to_instruction_set_enum(instruction_set_class)


__all__ = ['BRK_IMPLIED_0x00', 'register_brk_instructions']
