#!/usr/bin/env python3
"""CLC (Clear Carry Flag) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#CLC
# Clear Carry Flag
#
# 0 -> C
# N	Z	C	I	D	V
# -	-	0	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	CLC	18	1	2
CLC_IMPLIED_0x18 = InstructionOpcode(
    0x18,
    "mos6502.instructions.flags._clc",
    "clc_implied_0x18"
)


def add_clc_to_instruction_set_enum(instruction_set_class) -> None:
    """Add CLC instruction to the InstructionSet enum dynamically."""
    # Create a pseudo-enum member that has a .name attribute
    # We can't create a true enum member after class definition, but we can
    # create an object that behaves like one for lookup purposes
    class PseudoEnumMember(int):
        def __new__(cls, value, name) -> "InstructionSet":
            obj = int.__new__(cls, value)
            obj._name = name
            obj._value_ = value
            return obj

        @property
        def name(self) -> str:
            return self._name

        @property
        def value(self) -> int:
            return self._value_

    clc_member = PseudoEnumMember(CLC_IMPLIED_0x18, "CLC_IMPLIED_0x18")
    instruction_set_class._value2member_map_[CLC_IMPLIED_0x18] = clc_member
    setattr(instruction_set_class, "CLC_IMPLIED_0x18", CLC_IMPLIED_0x18)


def register_clc_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register CLC instruction in the InstructionSet."""
    # Add to enum
    add_clc_to_instruction_set_enum(instruction_set_class)

    # Add to map
    clc_immediate_0x18_can_modify_flags: Byte = Byte()
    clc_immediate_0x18_can_modify_flags[flags.C] = True
    instruction_map[CLC_IMPLIED_0x18] = {
        "addressing": "implied",
        "assembler": "CLC",
        "opc": CLC_IMPLIED_0x18,
        "bytes": "1",
        "cycles": "2",
        "flags": clc_immediate_0x18_can_modify_flags,
    }


__all__ = ["CLC_IMPLIED_0x18", "register_clc_instructions"]
