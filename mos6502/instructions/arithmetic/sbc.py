#!/usr/bin/env python3
"""SBC (Subtract Memory from Accumulator with Borrow) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#SBC
# Subtract Memory from Accumulator with Borrow
#
# A - M - C -> A
# N	Z	C	I	D	V
# +	+	+	-	-	+
# addressing	assembler	opc	bytes	cycles
# immediate	SBC #oper	E9	2	2
# zeropage	SBC oper	E5	2	3
# zeropage,X	SBC oper,X	F5	2	4
# absolute	SBC oper	ED	3	4
# absolute,X	SBC oper,X	FD	3	4*
# absolute,Y	SBC oper,Y	F9	3	4*
# (indirect,X)	SBC (oper,X)	E1	2	6
# (indirect),Y	SBC (oper),Y	F1	2	5*
SBC_IMMEDIATE_0xE9: Literal[233] = 0xE9
SBC_ZEROPAGE_0xE5: Literal[229] = 0xE5
SBC_ZEROPAGE_X_0xF5: Literal[245] = 0xF5
SBC_ABSOLUTE_0xED: Literal[237] = 0xED
SBC_ABSOLUTE_X_0xFD: Literal[253] = 0xFD
SBC_ABSOLUTE_Y_0xF9: Literal[249] = 0xF9
SBC_INDEXED_INDIRECT_X_0xE1: Literal[225] = 0xE1
SBC_INDIRECT_INDEXED_Y_0xF1: Literal[241] = 0xF1


def add_sbc_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SBC instructions to the InstructionSet enum dynamically."""
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
        (SBC_IMMEDIATE_0xE9, 'SBC_IMMEDIATE_0xE9'),
        (SBC_ZEROPAGE_0xE5, 'SBC_ZEROPAGE_0xE5'),
        (SBC_ZEROPAGE_X_0xF5, 'SBC_ZEROPAGE_X_0xF5'),
        (SBC_ABSOLUTE_0xED, 'SBC_ABSOLUTE_0xED'),
        (SBC_ABSOLUTE_X_0xFD, 'SBC_ABSOLUTE_X_0xFD'),
        (SBC_ABSOLUTE_Y_0xF9, 'SBC_ABSOLUTE_Y_0xF9'),
        (SBC_INDEXED_INDIRECT_X_0xE1, 'SBC_INDEXED_INDIRECT_X_0xE1'),
        (SBC_INDIRECT_INDEXED_Y_0xF1, 'SBC_INDIRECT_INDEXED_Y_0xF1'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_sbc_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SBC instructions in the InstructionSet.

    Note: SBC doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_sbc_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'SBC_IMMEDIATE_0xE9',
    'SBC_ZEROPAGE_0xE5',
    'SBC_ZEROPAGE_X_0xF5',
    'SBC_ABSOLUTE_0xED',
    'SBC_ABSOLUTE_X_0xFD',
    'SBC_ABSOLUTE_Y_0xF9',
    'SBC_INDEXED_INDIRECT_X_0xE1',
    'SBC_INDIRECT_INDEXED_Y_0xF1',
    'register_sbc_instructions',
]
