#!/usr/bin/env python3
"""RTI (Return from Interrupt) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#RTI
# Return from Interrupt
#
# pull P, pull PC
# N	Z	C	I	D	V
# from stack
# addressing	assembler	opc	bytes	cycles
# implied	RTI	40	1	6
RTI_IMPLIED_0x40 = InstructionOpcode(
    0x40,
    "mos6502.instructions.subroutines._rti",
    "rti_implied_0x40"
)


def add_rti_to_instruction_set_enum(instruction_set_class) -> None:
    """Add RTI instruction to the InstructionSet enum dynamically."""
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

    rti_member = PseudoEnumMember(RTI_IMPLIED_0x40, "RTI_IMPLIED_0x40")
    instruction_set_class._value2member_map_[RTI_IMPLIED_0x40] = rti_member
    setattr(instruction_set_class, "RTI_IMPLIED_0x40", RTI_IMPLIED_0x40)


def register_rti_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register RTI instruction in the InstructionSet."""
    add_rti_to_instruction_set_enum(instruction_set_class)

    # RTI restores all flags from stack
    rti_implied_0x40_can_modify_flags: Byte = Byte(0xFF)  # All flags can be modified
    instruction_map[RTI_IMPLIED_0x40] = {
        "addressing": "implied",
        "assembler": "RTI",
        "opc": RTI_IMPLIED_0x40,
        "bytes": "1",
        "cycles": "6",
        "flags": rti_implied_0x40_can_modify_flags,
    }


__all__ = ["RTI_IMPLIED_0x40", "register_rti_instructions"]
