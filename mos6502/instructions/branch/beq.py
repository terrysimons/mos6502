#!/usr/bin/env python3
"""BEQ (Branch on Result Zero) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#BEQ
#
# Branch on Result Zero
# branch on Z = 1
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BEQ oper	F0	2	2**
BEQ_RELATIVE_0xF0: Literal[240] = 0xF0


def add_beq_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BEQ instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(BEQ_RELATIVE_0xF0, 'BEQ_RELATIVE_0xF0')
    instruction_set_class._value2member_map_[BEQ_RELATIVE_0xF0] = member
    setattr(instruction_set_class, 'BEQ_RELATIVE_0xF0', BEQ_RELATIVE_0xF0)


def register_beq_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BEQ instructions in the InstructionSet.

    Note: BEQ doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_beq_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'BEQ_RELATIVE_0xF0',
    'register_beq_instructions',
]
