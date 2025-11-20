#!/usr/bin/env python3
"""SED (Set Decimal Flag) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#SED
# Set Decimal Flag
#
# 1 -> D
# N	Z	C	I	D	V
# -	-	-	-	1	-
# addressing	assembler	opc	bytes	cycles
# implied	SED	F8	1	2
SED_IMPLIED_0xF8 = InstructionOpcode(
    0xF8,
    "mos6502.instructions.flags._sed",
    "sed_implied_0xf8"
)


def add_sed_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SED instruction to the InstructionSet enum dynamically."""
    # Create a pseudo-enum member that has a .name attribute
    # We can't create a true enum member after class definition, but we can
    # create an object that behaves like one for lookup purposes
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

    sed_member = PseudoEnumMember(SED_IMPLIED_0xF8, 'SED_IMPLIED_0xF8')
    instruction_set_class._value2member_map_[SED_IMPLIED_0xF8] = sed_member
    setattr(instruction_set_class, 'SED_IMPLIED_0xF8', SED_IMPLIED_0xF8)


def register_sed_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SED instruction in the InstructionSet."""
    # Add to enum
    add_sed_to_instruction_set_enum(instruction_set_class)

    # Add to map
    sed_implied_0xf8_can_modify_flags: Byte = Byte()
    sed_implied_0xf8_can_modify_flags[flags.D] = True
    instruction_map[SED_IMPLIED_0xF8] = {
        "addressing": "implied",
        "assembler": "SED",
        "opc": SED_IMPLIED_0xF8,
        "bytes": "1",
        "cycles": "2",
        "flags": sed_implied_0xf8_can_modify_flags,
    }


__all__ = ['SED_IMPLIED_0xF8', 'register_sed_instructions']
