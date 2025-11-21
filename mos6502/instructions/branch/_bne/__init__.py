#!/usr/bin/env python3
"""BNE (Branch on Not Equal) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#BNE
# Branch on Not Equal
# branch on Z = 0
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BNE oper	D0	2	2**
BNE_RELATIVE_0xD0 = InstructionOpcode(
    0xD0,
    "mos6502.instructions.branch._bne",
    "bne_relative_0xd0"
)


def add_bne_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BNE instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(BNE_RELATIVE_0xD0, "BNE_RELATIVE_0xD0")
    instruction_set_class._value2member_map_[BNE_RELATIVE_0xD0] = member
    setattr(instruction_set_class, "BNE_RELATIVE_0xD0", BNE_RELATIVE_0xD0)


def register_bne_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BNE instructions in the InstructionSet."""
    add_bne_to_instruction_set_enum(instruction_set_class)

    bne_relative_0xd0_can_modify_flags: Byte = Byte()
    instruction_map[BNE_RELATIVE_0xD0] = {
        "addressing": "relative",
        "assembler": "BNE {oper}",
        "opc": BNE_RELATIVE_0xD0,
        "bytes": "2",
        "cycles": "2**",
        "flags": bne_relative_0xd0_can_modify_flags,
    }


__all__ = ["BNE_RELATIVE_0xD0", "register_bne_instructions"]
