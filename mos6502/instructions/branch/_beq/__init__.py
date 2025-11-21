#!/usr/bin/env python3
"""BEQ (Branch on Equal/Zero) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#BEQ
# Branch on Equal/Zero
# branch on Z = 1
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BEQ oper	F0	2	2**
BEQ_RELATIVE_0xF0 = InstructionOpcode(
    0xF0,
    "mos6502.instructions.branch._beq",
    "beq_relative_0xf0"
)


def add_beq_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BEQ instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(BEQ_RELATIVE_0xF0, "BEQ_RELATIVE_0xF0")
    instruction_set_class._value2member_map_[BEQ_RELATIVE_0xF0] = member
    setattr(instruction_set_class, "BEQ_RELATIVE_0xF0", BEQ_RELATIVE_0xF0)


def register_beq_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BEQ instructions in the InstructionSet."""
    add_beq_to_instruction_set_enum(instruction_set_class)

    beq_relative_0xf0_can_modify_flags: Byte = Byte()
    instruction_map[BEQ_RELATIVE_0xF0] = {
        "addressing": "relative",
        "assembler": "BEQ {oper}",
        "opc": BEQ_RELATIVE_0xF0,
        "bytes": "2",
        "cycles": "2**",
        "flags": beq_relative_0xf0_can_modify_flags,
    }


__all__ = ["BEQ_RELATIVE_0xF0", "register_beq_instructions"]
