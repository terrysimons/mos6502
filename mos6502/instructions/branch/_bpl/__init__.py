#!/usr/bin/env python3
"""BPL (Branch on Plus/Positive) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#BPL
# Branch on Plus/Positive
# branch on N = 0
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BPL oper	10	2	2**
BPL_RELATIVE_0x10 = InstructionOpcode(
    0x10,
    "mos6502.instructions.branch._bpl",
    "bpl_relative_0x10"
)


def add_bpl_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BPL instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(BPL_RELATIVE_0x10, "BPL_RELATIVE_0x10")
    instruction_set_class._value2member_map_[BPL_RELATIVE_0x10] = member
    setattr(instruction_set_class, "BPL_RELATIVE_0x10", BPL_RELATIVE_0x10)


def register_bpl_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BPL instructions in the InstructionSet."""
    add_bpl_to_instruction_set_enum(instruction_set_class)

    bpl_relative_0x10_can_modify_flags: Byte = Byte()
    instruction_map[BPL_RELATIVE_0x10] = {
        "addressing": "relative",
        "assembler": "BPL {oper}",
        "opc": BPL_RELATIVE_0x10,
        "bytes": "2",
        "cycles": "2**",
        "flags": bpl_relative_0x10_can_modify_flags,
    }


__all__ = ["BPL_RELATIVE_0x10", "register_bpl_instructions"]
