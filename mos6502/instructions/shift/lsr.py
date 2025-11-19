#!/usr/bin/env python3
"""LSR (Logical Shift Right) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#LSR
# Shift One Bit Right (Memory or Accumulator)
#
# 0 -> [76543210] -> C
# N	Z	C	I	D	V
# 0	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# accumulator	LSR A	4A	1	2
# zeropage	LSR oper	46	2	5
# zeropage,X	LSR oper,X	56	2	6
# absolute	LSR oper	4E	3	6
# absolute,X	LSR oper,X	5E	3	7
LSR_ACCUMULATOR_0x4A: Literal[74] = 0x4A
LSR_ZEROPAGE_0x46: Literal[70] = 0x46
LSR_ZEROPAGE_X_0x56: Literal[86] = 0x56
LSR_ABSOLUTE_0x4E: Literal[78] = 0x4E
LSR_ABSOLUTE_X_0x5E: Literal[94] = 0x5E


def add_lsr_to_instruction_set_enum(instruction_set_class) -> None:
    """Add LSR instructions to the InstructionSet enum dynamically."""
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
        (LSR_ACCUMULATOR_0x4A, 'LSR_ACCUMULATOR_0x4A'),
        (LSR_ZEROPAGE_0x46, 'LSR_ZEROPAGE_0x46'),
        (LSR_ZEROPAGE_X_0x56, 'LSR_ZEROPAGE_X_0x56'),
        (LSR_ABSOLUTE_0x4E, 'LSR_ABSOLUTE_0x4E'),
        (LSR_ABSOLUTE_X_0x5E, 'LSR_ABSOLUTE_X_0x5E'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_lsr_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register LSR instructions in the InstructionSet.

    Note: LSR doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_lsr_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'LSR_ACCUMULATOR_0x4A',
    'LSR_ZEROPAGE_0x46',
    'LSR_ZEROPAGE_X_0x56',
    'LSR_ABSOLUTE_0x4E',
    'LSR_ABSOLUTE_X_0x5E',
    'register_lsr_instructions',
]
