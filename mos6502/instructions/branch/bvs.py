#!/usr/bin/env python3
"""BVS (Branch on Overflow Set) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#BVS
# Branch on Overflow Set
#
# branch on V = 1
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BVS oper	70	2	2**
BVS_RELATIVE_0x70: Literal[112] = 0x70


def add_bvs_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BVS instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(BVS_RELATIVE_0x70, 'BVS_RELATIVE_0x70')
    instruction_set_class._value2member_map_[BVS_RELATIVE_0x70] = member
    setattr(instruction_set_class, 'BVS_RELATIVE_0x70', BVS_RELATIVE_0x70)


def register_bvs_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BVS instructions in the InstructionSet.

    Note: BVS doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_bvs_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'BVS_RELATIVE_0x70',
    'register_bvs_instructions',
]
