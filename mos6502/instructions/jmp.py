#!/usr/bin/env python3
"""JMP (Jump to New Location) instruction."""
from typing import Literal

# https://masswerk.at/6502/6502_instruction_set.html#JMP
# Jump to New Location
#
# (PC+1) -> PCL
# (PC+2) -> PCH
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# absolute	JMP oper	4C	3	3
# indirect	JMP (oper)	6C	3	5
JMP_ABSOLUTE_0x4C: Literal[76] = 0x4C
JMP_INDIRECT_0x6C: Literal[108] = 0x6C


def add_jmp_to_instruction_set_enum(instruction_set_class) -> None:
    """Add JMP instructions to the InstructionSet enum dynamically."""
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

    jmp_absolute_member = PseudoEnumMember(JMP_ABSOLUTE_0x4C, 'JMP_ABSOLUTE_0x4C')
    instruction_set_class._value2member_map_[JMP_ABSOLUTE_0x4C] = jmp_absolute_member
    setattr(instruction_set_class, 'JMP_ABSOLUTE_0x4C', JMP_ABSOLUTE_0x4C)

    jmp_indirect_member = PseudoEnumMember(JMP_INDIRECT_0x6C, 'JMP_INDIRECT_0x6C')
    instruction_set_class._value2member_map_[JMP_INDIRECT_0x6C] = jmp_indirect_member
    setattr(instruction_set_class, 'JMP_INDIRECT_0x6C', JMP_INDIRECT_0x6C)


def register_jmp_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register JMP instructions in the InstructionSet.

    Note: JMP doesn't have map entries because it's handled as a special case
    in core.py execute() method.
    """
    # Add to enum
    add_jmp_to_instruction_set_enum(instruction_set_class)


__all__ = ['JMP_ABSOLUTE_0x4C', 'JMP_INDIRECT_0x6C', 'register_jmp_instructions']
