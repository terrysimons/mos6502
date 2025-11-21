#!/usr/bin/env python3
"""JSR (Jump to New Location Saving Return Address) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#JSR
#
# Jump to New Location Saving Return Address
#
# (PC+1) -> PCL
# (PC+2) -> PCH
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# absolute	JSR oper	20	3	6
JSR_ABSOLUTE_0x20 = InstructionOpcode(
    0x20,
    "mos6502.instructions.subroutines._jsr",
    "jsr_absolute_0x20"
)


def add_jsr_to_instruction_set_enum(instruction_set_class) -> None:
    """Add JSR instruction to the InstructionSet enum dynamically."""
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

    jsr_member = PseudoEnumMember(JSR_ABSOLUTE_0x20, "JSR_ABSOLUTE_0x20")
    instruction_set_class._value2member_map_[JSR_ABSOLUTE_0x20] = jsr_member
    setattr(instruction_set_class, "JSR_ABSOLUTE_0x20", JSR_ABSOLUTE_0x20)


def register_jsr_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register JSR instruction in the InstructionSet."""
    add_jsr_to_instruction_set_enum(instruction_set_class)

    jsr_absolute_0x20_can_modify_flags: Byte = Byte()
    instruction_map[JSR_ABSOLUTE_0x20] = {
        "addressing": "absolute",
        "assembler": "JSR {oper}",
        "opc": JSR_ABSOLUTE_0x20,
        "bytes": "3",
        "cycles": "6",
        "flags": jsr_absolute_0x20_can_modify_flags,
    }


__all__ = ["JSR_ABSOLUTE_0x20", "register_jsr_instructions"]
