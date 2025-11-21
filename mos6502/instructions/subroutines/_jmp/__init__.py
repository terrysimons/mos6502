#!/usr/bin/env python3
"""JMP (Jump to New Location) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

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
JMP_ABSOLUTE_0x4C = InstructionOpcode(
    0x4C,
    "mos6502.instructions.subroutines._jmp",
    "jmp_absolute_0x4c"
)

JMP_INDIRECT_0x6C = InstructionOpcode(
    0x6C,
    "mos6502.instructions.subroutines._jmp",
    "jmp_indirect_0x6c"
)


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

    jmp_absolute_member = PseudoEnumMember(JMP_ABSOLUTE_0x4C, "JMP_ABSOLUTE_0x4C")
    instruction_set_class._value2member_map_[JMP_ABSOLUTE_0x4C] = jmp_absolute_member
    setattr(instruction_set_class, "JMP_ABSOLUTE_0x4C", JMP_ABSOLUTE_0x4C)

    jmp_indirect_member = PseudoEnumMember(JMP_INDIRECT_0x6C, "JMP_INDIRECT_0x6C")
    instruction_set_class._value2member_map_[JMP_INDIRECT_0x6C] = jmp_indirect_member
    setattr(instruction_set_class, "JMP_INDIRECT_0x6C", JMP_INDIRECT_0x6C)


def register_jmp_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register JMP instructions in the InstructionSet."""
    add_jmp_to_instruction_set_enum(instruction_set_class)

    # JMP doesn't modify any flags
    jmp_absolute_can_modify_flags: Byte = Byte()
    instruction_map[JMP_ABSOLUTE_0x4C] = {
        "addressing": "absolute",
        "assembler": "JMP {oper}",
        "opc": JMP_ABSOLUTE_0x4C,
        "bytes": "3",
        "cycles": "3",
        "flags": jmp_absolute_can_modify_flags,
    }

    jmp_indirect_can_modify_flags: Byte = Byte()
    instruction_map[JMP_INDIRECT_0x6C] = {
        "addressing": "indirect",
        "assembler": "JMP ({oper})",
        "opc": JMP_INDIRECT_0x6C,
        "bytes": "3",
        "cycles": "5",
        "flags": jmp_indirect_can_modify_flags,
    }


__all__ = ["JMP_ABSOLUTE_0x4C", "JMP_INDIRECT_0x6C", "register_jmp_instructions"]
