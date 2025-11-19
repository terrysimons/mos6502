#!/usr/bin/env python3
"""BNE (Branch on Result not Zero) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#BNE
# Branch on Result not Zero
#
# branch on Z = 0
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BNE oper	D0	2	2**
BNE_RELATIVE_0xD0: Literal[208] = 0xD0


def add_bne_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BNE instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(BNE_RELATIVE_0xD0, 'BNE_RELATIVE_0xD0')
    instruction_set_class._value2member_map_[BNE_RELATIVE_0xD0] = member
    setattr(instruction_set_class, 'BNE_RELATIVE_0xD0', BNE_RELATIVE_0xD0)


def register_bne_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BNE instructions in the InstructionSet.

    Note: BNE doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_bne_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'BNE_RELATIVE_0xD0',
    'register_bne_instructions',
]
