#!/usr/bin/env python3
"""CPY (Compare Memory and Index Y) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#CPY
# Compare Memory and Index Y
#
# Y - M
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	CPY #oper	C0	2	2
# zeropage	CPY oper	C4	2	3
# absolute	CPY oper	CC	3	4
CPY_IMMEDIATE_0xC0: Literal[192] = 0xC0
CPY_ZEROPAGE_0xC4: Literal[196] = 0xC4
CPY_ABSOLUTE_0xCC: Literal[204] = 0xCC


def add_cpy_to_instruction_set_enum(instruction_set_class) -> None:
    """Add CPY instructions to the InstructionSet enum dynamically."""
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
        (CPY_IMMEDIATE_0xC0, 'CPY_IMMEDIATE_0xC0'),
        (CPY_ZEROPAGE_0xC4, 'CPY_ZEROPAGE_0xC4'),
        (CPY_ABSOLUTE_0xCC, 'CPY_ABSOLUTE_0xCC'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_cpy_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register CPY instructions in the InstructionSet.

    Note: CPY doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_cpy_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'CPY_IMMEDIATE_0xC0',
    'CPY_ZEROPAGE_0xC4',
    'CPY_ABSOLUTE_0xCC',
    'register_cpy_instructions',
]
