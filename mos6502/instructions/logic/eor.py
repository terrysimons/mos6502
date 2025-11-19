#!/usr/bin/env python3
"""EOR (Exclusive-OR Memory with Accumulator) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#EOR
# Exclusive-OR Memory with Accumulator
#
# A EOR M -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	EOR #oper	49	2	2
# zeropage	EOR oper	45	2	3
# zeropage,X	EOR oper,X	55	2	4
# absolute	EOR oper	4D	3	4
# absolute,X	EOR oper,X	5D	3	4*
# absolute,Y	EOR oper,Y	59	3	4*
# (indirect,X)	EOR (oper,X)	41	2	6
# (indirect),Y	EOR (oper),Y	51	2	5*
EOR_IMMEDIATE_0x49: Literal[73] = 0x49
EOR_ZEROPAGE_0x45: Literal[69] = 0x45
EOR_ZEROPAGE_X_0x55: Literal[85] = 0x55
EOR_ABSOLUTE_0x4D: Literal[77] = 0x4D
EOR_ABSOLUTE_X_0x5D: Literal[93] = 0x5D
EOR_ABSOLUTE_Y_0x59: Literal[89] = 0x59
EOR_INDEXED_INDIRECT_X_0x41: Literal[65] = 0x41
EOR_INDIRECT_INDEXED_Y_0x51: Literal[81] = 0x51


def add_eor_to_instruction_set_enum(instruction_set_class) -> None:
    """Add EOR instructions to the InstructionSet enum dynamically."""
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
        (EOR_IMMEDIATE_0x49, 'EOR_IMMEDIATE_0x49'),
        (EOR_ZEROPAGE_0x45, 'EOR_ZEROPAGE_0x45'),
        (EOR_ZEROPAGE_X_0x55, 'EOR_ZEROPAGE_X_0x55'),
        (EOR_ABSOLUTE_0x4D, 'EOR_ABSOLUTE_0x4D'),
        (EOR_ABSOLUTE_X_0x5D, 'EOR_ABSOLUTE_X_0x5D'),
        (EOR_ABSOLUTE_Y_0x59, 'EOR_ABSOLUTE_Y_0x59'),
        (EOR_INDEXED_INDIRECT_X_0x41, 'EOR_INDEXED_INDIRECT_X_0x41'),
        (EOR_INDIRECT_INDEXED_Y_0x51, 'EOR_INDIRECT_INDEXED_Y_0x51'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_eor_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register EOR instructions in the InstructionSet.

    Note: EOR doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_eor_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'EOR_IMMEDIATE_0x49',
    'EOR_ZEROPAGE_0x45',
    'EOR_ZEROPAGE_X_0x55',
    'EOR_ABSOLUTE_0x4D',
    'EOR_ABSOLUTE_X_0x5D',
    'EOR_ABSOLUTE_Y_0x59',
    'EOR_INDEXED_INDIRECT_X_0x41',
    'EOR_INDIRECT_INDEXED_Y_0x51',
    'register_eor_instructions',
]
