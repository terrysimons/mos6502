#!/usr/bin/env python3
"""BIT (Test Bits in Memory with Accumulator) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#BIT
#
# Test Bits in Memory with Accumulator
#
# bits 7 and 6 of operand are transfered to bit 7 and 6 of SR (N,V);
# the zero-flag is set to the result of operand AND accumulator.
#
# A AND M, M7 -> N, M6 -> V
# N	Z	C	I	D	V
# M7	+	-	-	-	M6
# addressing	assembler	opc	bytes	cycles
# zeropage	BIT oper	24	2	3
# absolute	BIT oper	2C	3	4
BIT_ZEROPAGE_0x24: Literal[36] = 0x24
BIT_ABSOLUTE_0x2C: Literal[44] = 0x2C


def add_bit_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BIT instructions to the InstructionSet enum dynamically."""
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
        (BIT_ZEROPAGE_0x24, 'BIT_ZEROPAGE_0x24'),
        (BIT_ABSOLUTE_0x2C, 'BIT_ABSOLUTE_0x2C'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_bit_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BIT instructions in the InstructionSet.

    Note: BIT doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_bit_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'BIT_ZEROPAGE_0x24',
    'BIT_ABSOLUTE_0x2C',
    'register_bit_instructions',
]
