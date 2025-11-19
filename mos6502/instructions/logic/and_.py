#!/usr/bin/env python3
"""AND (AND Memory with Accumulator) instruction."""
from typing import Literal

# https://www.masswerk.at/6502/6502_instruction_set.html#AND
#
# AND Memory with Accumulator
#
# A AND M -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	AND #oper	29	2	2
# zeropage	AND oper	25	2	3
# zeropage,X	AND oper,X	35	2	4
# absolute	AND oper	2D	3	4
# absolute,X	AND oper,X	3D	3	4*
# absolute,Y	AND oper,Y	39	3	4*
# (indirect,X)	AND (oper,X)	21	2	6
# (indirect),Y	AND (oper),Y	31	2	5*
AND_IMMEDIATE_0x29: Literal[41] = 0x29
AND_ZEROPAGE_0x25: Literal[37] = 0x25
AND_ZEROPAGE_X_0x35: Literal[53] = 0x35
AND_ABSOLUTE_0x2D: Literal[45] = 0x2D
AND_ABSOLUTE_X_0x3D: Literal[61] = 0x3D
AND_ABSOLUTE_Y_0x39: Literal[57] = 0x39
AND_INDEXED_INDIRECT_X_0x21: Literal[33] = 0x21
AND_INDIRECT_INDEXED_Y_0x31: Literal[49] = 0x31


def add_and_to_instruction_set_enum(instruction_set_class) -> None:
    """Add AND instructions to the InstructionSet enum dynamically."""
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
        (AND_IMMEDIATE_0x29, 'AND_IMMEDIATE_0x29'),
        (AND_ZEROPAGE_0x25, 'AND_ZEROPAGE_0x25'),
        (AND_ZEROPAGE_X_0x35, 'AND_ZEROPAGE_X_0x35'),
        (AND_ABSOLUTE_0x2D, 'AND_ABSOLUTE_0x2D'),
        (AND_ABSOLUTE_X_0x3D, 'AND_ABSOLUTE_X_0x3D'),
        (AND_ABSOLUTE_Y_0x39, 'AND_ABSOLUTE_Y_0x39'),
        (AND_INDEXED_INDIRECT_X_0x21, 'AND_INDEXED_INDIRECT_X_0x21'),
        (AND_INDIRECT_INDEXED_Y_0x31, 'AND_INDIRECT_INDEXED_Y_0x31'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_and_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register AND instructions in the InstructionSet.

    Note: AND doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_and_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'AND_IMMEDIATE_0x29',
    'AND_ZEROPAGE_0x25',
    'AND_ZEROPAGE_X_0x35',
    'AND_ABSOLUTE_0x2D',
    'AND_ABSOLUTE_X_0x3D',
    'AND_ABSOLUTE_Y_0x39',
    'AND_INDEXED_INDIRECT_X_0x21',
    'AND_INDIRECT_INDEXED_Y_0x31',
    'register_and_instructions',
]
