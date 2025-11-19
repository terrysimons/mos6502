#!/usr/bin/env python3
"""CLD (Clear Decimal Mode) instruction."""
from typing import Literal

from mos6502 import flags
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#CLD
# Clear Decimal Mode
#
# 0 -> D
# N	Z	C	I	D	V
# -	-	-	-	0	-
# addressing	assembler	opc	bytes	cycles
# implied	CLD	D8	1	2
CLD_IMPLIED_0xD8: Literal[216] = 0xD8


def add_cld_to_instruction_set_enum(instruction_set_class) -> None:
    """Add CLD instruction to the InstructionSet enum dynamically."""
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

    cld_member = PseudoEnumMember(CLD_IMPLIED_0xD8, 'CLD_IMPLIED_0xD8')
    instruction_set_class._value2member_map_[CLD_IMPLIED_0xD8] = cld_member
    setattr(instruction_set_class, 'CLD_IMPLIED_0xD8', CLD_IMPLIED_0xD8)


def register_cld_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register CLD instruction in the InstructionSet."""
    # Add to enum
    add_cld_to_instruction_set_enum(instruction_set_class)

    # Add to map
    cld_immediate_0xd8_can_modify_flags: Byte = Byte()
    cld_immediate_0xd8_can_modify_flags[flags.D] = True
    instruction_map[CLD_IMPLIED_0xD8] = {
        "addressing": "implied",
        "assembler": "CLD",
        "opc": CLD_IMPLIED_0xD8,
        "bytes": "1",
        "cycles": "2",
        "flags": cld_immediate_0xd8_can_modify_flags,
    }


__all__ = ['CLD_IMPLIED_0xD8', 'register_cld_instructions']
