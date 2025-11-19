#!/usr/bin/env python3
"""CPX (Compare Memory and Index X) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#CPX
# Compare Memory and Index X
#
# X - M
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	CPX #oper	E0	2	2
# zeropage	CPX oper	E4	2	3
# absolute	CPX oper	EC	3	4
CPX_IMMEDIATE_0xE0: Literal[224] = 0xE0
CPX_ZEROPAGE_0xE4: Literal[228] = 0xE4
CPX_ABSOLUTE_0xEC: Literal[236] = 0xEC


def add_cpx_to_instruction_set_enum(instruction_set_class) -> None:
    """Add CPX instructions to the InstructionSet enum dynamically."""
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

    for value, name in [
        (CPX_IMMEDIATE_0xE0, 'CPX_IMMEDIATE_0xE0'),
        (CPX_ZEROPAGE_0xE4, 'CPX_ZEROPAGE_0xE4'),
        (CPX_ABSOLUTE_0xEC, 'CPX_ABSOLUTE_0xEC'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_cpx_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register CPX instructions in the InstructionSet.

    Note: CPX doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_cpx_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'CPX_IMMEDIATE_0xE0',
    'CPX_ZEROPAGE_0xE4',
    'CPX_ABSOLUTE_0xEC',
    'register_cpx_instructions',
]
