#!/usr/bin/env python3
"""ORA (OR Memory with Accumulator) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#ORA
# OR Memory with Accumulator
#
# A OR M -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	ORA #oper	09	2	2
# zeropage	ORA oper	05	2	3
# zeropage,X	ORA oper,X	15	2	4
# absolute	ORA oper	0D	3	4
# absolute,X	ORA oper,X	1D	3	4*
# absolute,Y	ORA oper,Y	19	3	4*
# (indirect,X)	ORA (oper,X)	01	2	6
# (indirect),Y	ORA (oper),Y	11	2	5*
ORA_IMMEDIATE_0x09: Literal[9] = 0x09
ORA_ZEROPAGE_0x05: Literal[5] = 0x05
ORA_ZEROPAGE_X_0x15: Literal[21] = 0x15
ORA_ABSOLUTE_0x0D: Literal[13] = 0x0D
ORA_ABSOLUTE_X_0x1D: Literal[29] = 0x1D
ORA_ABSOLUTE_Y_0x19: Literal[25] = 0x19
ORA_INDEXED_INDIRECT_X_0x01: Literal[1] = 0x01
ORA_INDIRECT_INDEXED_Y_0x11: Literal[17] = 0x11


def add_ora_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ORA instructions to the InstructionSet enum dynamically."""
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
        (ORA_IMMEDIATE_0x09, 'ORA_IMMEDIATE_0x09'),
        (ORA_ZEROPAGE_0x05, 'ORA_ZEROPAGE_0x05'),
        (ORA_ZEROPAGE_X_0x15, 'ORA_ZEROPAGE_X_0x15'),
        (ORA_ABSOLUTE_0x0D, 'ORA_ABSOLUTE_0x0D'),
        (ORA_ABSOLUTE_X_0x1D, 'ORA_ABSOLUTE_X_0x1D'),
        (ORA_ABSOLUTE_Y_0x19, 'ORA_ABSOLUTE_Y_0x19'),
        (ORA_INDEXED_INDIRECT_X_0x01, 'ORA_INDEXED_INDIRECT_X_0x01'),
        (ORA_INDIRECT_INDEXED_Y_0x11, 'ORA_INDIRECT_INDEXED_Y_0x11'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_ora_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ORA instructions in the InstructionSet.

    Note: ORA doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    add_ora_to_instruction_set_enum(instruction_set_class)


__all__ = [
    'ORA_IMMEDIATE_0x09',
    'ORA_ZEROPAGE_0x05',
    'ORA_ZEROPAGE_X_0x15',
    'ORA_ABSOLUTE_0x0D',
    'ORA_ABSOLUTE_X_0x1D',
    'ORA_ABSOLUTE_Y_0x19',
    'ORA_INDEXED_INDIRECT_X_0x01',
    'ORA_INDIRECT_INDEXED_Y_0x11',
    'register_ora_instructions',
]
