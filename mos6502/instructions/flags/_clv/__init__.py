#!/usr/bin/env python3
"""CLV (Clear Overflow Flag) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#CLV
# Clear Overflow Flag
#
# 0 -> V
# N	Z	C	I	D	V
# -	-	-	-	-	0
# addressing	assembler	opc	bytes	cycles
# implied	CLV	B8	1	2
CLV_IMPLIED_0xB8 = InstructionOpcode(
    0xB8,
    "mos6502.instructions.flags._clv",
    "clv_implied_0xb8"
)


def add_clv_to_instruction_set_enum(instruction_set_class) -> None:
    """Add CLV instruction to the InstructionSet enum dynamically."""
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

    clv_member = PseudoEnumMember(CLV_IMPLIED_0xB8, "CLV_IMPLIED_0xB8")
    instruction_set_class._value2member_map_[CLV_IMPLIED_0xB8] = clv_member
    setattr(instruction_set_class, "CLV_IMPLIED_0xB8", CLV_IMPLIED_0xB8)


def register_clv_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register CLV instruction in the InstructionSet."""
    # Add to enum
    add_clv_to_instruction_set_enum(instruction_set_class)

    # Add to map
    clv_implied_0xb8_can_modify_flags: Byte = Byte()
    clv_implied_0xb8_can_modify_flags[flags.V] = True
    instruction_map[CLV_IMPLIED_0xB8] = {
        "addressing": "implied",
        "assembler": "CLV",
        "opc": CLV_IMPLIED_0xB8,
        "bytes": "1",
        "cycles": "2",
        "flags": clv_implied_0xb8_can_modify_flags,
    }


__all__ = ["CLV_IMPLIED_0xB8", "register_clv_instructions"]
