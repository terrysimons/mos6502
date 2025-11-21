#!/usr/bin/env python3
"""SEC (Set Carry Flag) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#SEC
# Set Carry Flag
#
# 1 -> C
# N	Z	C	I	D	V
# -	-	1	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	SEC	38	1	2
SEC_IMPLIED_0x38 = InstructionOpcode(
    0x38,
    "mos6502.instructions.flags._sec",
    "sec_implied_0x38"
)


def add_sec_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SEC instruction to the InstructionSet enum dynamically."""
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
        def name(self):
            return self._name

        @property
        def value(self):
            return self._value_

    sec_member = PseudoEnumMember(SEC_IMPLIED_0x38, "SEC_IMPLIED_0x38")
    instruction_set_class._value2member_map_[SEC_IMPLIED_0x38] = sec_member
    setattr(instruction_set_class, "SEC_IMPLIED_0x38", SEC_IMPLIED_0x38)


def register_sec_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SEC instruction in the InstructionSet."""
    # Add to enum
    add_sec_to_instruction_set_enum(instruction_set_class)

    # Add to map
    sec_implied_0x38_can_modify_flags: Byte = Byte()
    sec_implied_0x38_can_modify_flags[flags.C] = True
    instruction_map[SEC_IMPLIED_0x38] = {
        "addressing": "implied",
        "assembler": "SEC",
        "opc": SEC_IMPLIED_0x38,
        "bytes": "1",
        "cycles": "2",
        "flags": sec_implied_0x38_can_modify_flags,
    }


__all__ = ["SEC_IMPLIED_0x38", "register_sec_instructions"]
