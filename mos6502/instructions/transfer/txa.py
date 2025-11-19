#!/usr/bin/env python3
"""TXA (Transfer Index X to Accumulator) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#TXA
# Transfer Index X to Accumulator
#
# X -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TXA	8A	1	2
TXA_IMPLIED_0x8A: Literal[138] = 0x8A


def add_txa_to_instruction_set_enum(instruction_set_class) -> None:
    """Add TXA instruction to the InstructionSet enum dynamically."""
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

    txa_member = PseudoEnumMember(TXA_IMPLIED_0x8A, 'TXA_IMPLIED_0x8A')
    instruction_set_class._value2member_map_[TXA_IMPLIED_0x8A] = txa_member
    setattr(instruction_set_class, 'TXA_IMPLIED_0x8A', TXA_IMPLIED_0x8A)


def register_txa_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register TXA instruction in the InstructionSet.

    Note: TXA doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    add_txa_to_instruction_set_enum(instruction_set_class)


__all__ = ['TXA_IMPLIED_0x8A', 'register_txa_instructions']
