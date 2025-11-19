#!/usr/bin/env python3
"""DEX (Decrement Index X by One) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#DEX
# Decrement Index X by One
#
# X - 1 -> X
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	DEX	CA	1	2
DEX_IMPLIED_0xCA: Literal[202] = 0xCA


def add_dex_to_instruction_set_enum(instruction_set_class) -> None:
    """Add DEX instruction to the InstructionSet enum dynamically."""
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

    dex_member = PseudoEnumMember(DEX_IMPLIED_0xCA, 'DEX_IMPLIED_0xCA')
    instruction_set_class._value2member_map_[DEX_IMPLIED_0xCA] = dex_member
    setattr(instruction_set_class, 'DEX_IMPLIED_0xCA', DEX_IMPLIED_0xCA)


def register_dex_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register DEX instruction in the InstructionSet.

    Note: DEX doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    add_dex_to_instruction_set_enum(instruction_set_class)


__all__ = ['DEX_IMPLIED_0xCA', 'register_dex_instructions']
