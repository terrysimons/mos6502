#!/usr/bin/env python3
"""BCS (Branch on Carry Set) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#BCS
# Branch on Carry Set
# branch on C = 1
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BCS oper	B0	2	2**
BCS_RELATIVE_0xB0 = InstructionOpcode(
    0xB0,
    "mos6502.instructions.branch._bcs",
    "bcs_relative_0xb0"
)


def add_bcs_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BCS instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(BCS_RELATIVE_0xB0, "BCS_RELATIVE_0xB0")
    instruction_set_class._value2member_map_[BCS_RELATIVE_0xB0] = member
    setattr(instruction_set_class, "BCS_RELATIVE_0xB0", BCS_RELATIVE_0xB0)


def register_bcs_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BCS instructions in the InstructionSet."""
    add_bcs_to_instruction_set_enum(instruction_set_class)

    bcs_relative_0xb0_can_modify_flags: Byte = Byte()
    instruction_map[BCS_RELATIVE_0xB0] = {
        "addressing": "relative",
        "assembler": "BCS {oper}",
        "opc": BCS_RELATIVE_0xB0,
        "bytes": "2",
        "cycles": "2**",
        "flags": bcs_relative_0xb0_can_modify_flags,
    }


__all__ = ["BCS_RELATIVE_0xB0", "register_bcs_instructions"]
