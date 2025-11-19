#!/usr/bin/env python3
"""PLP (Pull Processor Status from Stack) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#PLP
# Pull Processor Status from Stack
#
# The status register will be pulled with the break
# flag and bit 5 ignored.
#
# pull SR
# N	Z	C	I	D	V
# from stack
# addressing	assembler	opc	bytes	cycles
# implied	PLP	28	1	4
PLP_IMPLIED_0x28: Literal[40] = 0x28


def add_plp_to_instruction_set_enum(instruction_set_class) -> None:
    """Add PLP instruction to the InstructionSet enum dynamically."""
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

    plp_member = PseudoEnumMember(PLP_IMPLIED_0x28, 'PLP_IMPLIED_0x28')
    instruction_set_class._value2member_map_[PLP_IMPLIED_0x28] = plp_member
    setattr(instruction_set_class, 'PLP_IMPLIED_0x28', PLP_IMPLIED_0x28)


def register_plp_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register PLP instruction in the InstructionSet.

    Note: PLP doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    # Add to enum
    add_plp_to_instruction_set_enum(instruction_set_class)


__all__ = ['PLP_IMPLIED_0x28', 'register_plp_instructions']
