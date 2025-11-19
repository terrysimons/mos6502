#!/usr/bin/env python3
"""TAX (Transfer Accumulator to Index X) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#TAX
# Transfer Accumulator to Index X
#
# A -> X
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TAX	AA	1	2
TAX_IMPLIED_0xAA: Literal[170] = 0xAA


def add_tax_to_instruction_set_enum(instruction_set_class) -> None:
    """Add TAX instruction to the InstructionSet enum dynamically."""
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

    tax_member = PseudoEnumMember(TAX_IMPLIED_0xAA, 'TAX_IMPLIED_0xAA')
    instruction_set_class._value2member_map_[TAX_IMPLIED_0xAA] = tax_member
    setattr(instruction_set_class, 'TAX_IMPLIED_0xAA', TAX_IMPLIED_0xAA)


def register_tax_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register TAX instruction in the InstructionSet.

    Note: TAX doesn't have a map entry because it's handled as a special case
    in core.py execute() method.
    """
    add_tax_to_instruction_set_enum(instruction_set_class)


__all__ = ['TAX_IMPLIED_0xAA', 'register_tax_instructions']
