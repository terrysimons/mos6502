#!/usr/bin/env python3
"""TYA (Transfer Index Y to Accumulator) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#TYA
# Transfer Index Y to Accumulator
#
# Y -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TYA	98	1	2
TYA_IMPLIED_0x98: Literal[152] = 0x98


def add_tya_to_instruction_set_enum(instruction_set_class) -> None:
    """Add TYA instruction to the InstructionSet enum dynamically."""
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

    tya_member = PseudoEnumMember(TYA_IMPLIED_0x98, 'TYA_IMPLIED_0x98')
    instruction_set_class._value2member_map_[TYA_IMPLIED_0x98] = tya_member
    setattr(instruction_set_class, 'TYA_IMPLIED_0x98', TYA_IMPLIED_0x98)


def register_tya_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register TYA instruction in the InstructionSet.

    Note: TYA doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    add_tya_to_instruction_set_enum(instruction_set_class)


__all__ = ['TYA_IMPLIED_0x98', 'register_tya_instructions']
