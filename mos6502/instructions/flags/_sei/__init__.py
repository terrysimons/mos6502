#!/usr/bin/env python3
"""SEI (Set Interrupt Disable Status) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#SEI
# Set Interrupt Disable Status
#
# 1 -> I
# N	Z	C	I	D	V
# -	-	-	1	-	-
# addressing	assembler	opc	bytes	cycles
# implied	SEI	78	1	2
SEI_IMPLIED_0x78 = InstructionOpcode(
    0x78,
    "mos6502.instructions.flags._sei",
    "sei_implied_0x78"
)


def add_sei_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SEI instruction to the InstructionSet enum dynamically."""
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

    sei_member = PseudoEnumMember(SEI_IMPLIED_0x78, "SEI_IMPLIED_0x78")
    instruction_set_class._value2member_map_[SEI_IMPLIED_0x78] = sei_member
    setattr(instruction_set_class, "SEI_IMPLIED_0x78", SEI_IMPLIED_0x78)


def register_sei_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SEI instruction in the InstructionSet."""
    # Add to enum
    add_sei_to_instruction_set_enum(instruction_set_class)

    # Add to map
    sei_implied_0x78_can_modify_flags: Byte = Byte()
    sei_implied_0x78_can_modify_flags[flags.I] = True
    instruction_map[SEI_IMPLIED_0x78] = {
        "addressing": "implied",
        "assembler": "SEI",
        "opc": SEI_IMPLIED_0x78,
        "bytes": "1",
        "cycles": "2",
        "flags": sei_implied_0x78_can_modify_flags,
    }


__all__ = ["SEI_IMPLIED_0x78", "register_sei_instructions"]
