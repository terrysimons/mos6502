#!/usr/bin/env python3
"""CMP (Compare Memory with Accumulator) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#CMP
# Compare Memory with Accumulator
#
# A - M
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	CMP #oper	C9	2	2
# zeropage	CMP oper	C5	2	3
# zeropage,X	CMP oper,X	D5	2	4
# absolute	CMP oper	CD	3	4
# absolute,X	CMP oper,X	DD	3	4*
# absolute,Y	CMP oper,Y	D9	3	4*
# (indirect,X)	CMP (oper,X)	C1	2	6
# (indirect),Y	CMP (oper),Y	D1	2	5*
CMP_IMMEDIATE_0xC9: Literal[201] = 0xC9
CMP_ZEROPAGE_0xC5: Literal[197] = 0xC5
CMP_ZEROPAGE_X_0xD5: Literal[213] = 0xD5
CMP_ABSOLUTE_0xCD: Literal[205] = 0xCD
CMP_ABSOLUTE_X_0xDD: Literal[221] = 0xDD
CMP_ABSOLUTE_Y_0xD9: Literal[217] = 0xD9
CMP_INDEXED_INDIRECT_X_0xC1: Literal[193] = 0xC1
CMP_INDIRECT_INDEXED_Y_0xD1: Literal[209] = 0xD1


def add_cmp_to_instruction_set_enum(instruction_set_class) -> None:
    """Add CMP instructions to the InstructionSet enum dynamically."""
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
        (CMP_IMMEDIATE_0xC9, 'CMP_IMMEDIATE_0xC9'),
        (CMP_ZEROPAGE_0xC5, 'CMP_ZEROPAGE_0xC5'),
        (CMP_ZEROPAGE_X_0xD5, 'CMP_ZEROPAGE_X_0xD5'),
        (CMP_ABSOLUTE_0xCD, 'CMP_ABSOLUTE_0xCD'),
        (CMP_ABSOLUTE_X_0xDD, 'CMP_ABSOLUTE_X_0xDD'),
        (CMP_ABSOLUTE_Y_0xD9, 'CMP_ABSOLUTE_Y_0xD9'),
        (CMP_INDEXED_INDIRECT_X_0xC1, 'CMP_INDEXED_INDIRECT_X_0xC1'),
        (CMP_INDIRECT_INDEXED_Y_0xD1, 'CMP_INDIRECT_INDEXED_Y_0xD1'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_cmp_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register CMP instructions in the InstructionSet.

    Note: CMP doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_cmp_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'CMP_IMMEDIATE_0xC9',
    'CMP_ZEROPAGE_0xC5',
    'CMP_ZEROPAGE_X_0xD5',
    'CMP_ABSOLUTE_0xCD',
    'CMP_ABSOLUTE_X_0xDD',
    'CMP_ABSOLUTE_Y_0xD9',
    'CMP_INDEXED_INDIRECT_X_0xC1',
    'CMP_INDIRECT_INDEXED_Y_0xD1',
    'register_cmp_instructions',
]
