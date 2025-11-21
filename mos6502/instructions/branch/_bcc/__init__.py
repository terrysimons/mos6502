#!/usr/bin/env python3
"""BCC (Branch on Carry Clear) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#BCC
#
# Branch on Carry Clear
# branch on C = 0
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BCC oper	90	2	2**
BCC_RELATIVE_0x90 = InstructionOpcode(
    0x90,
    "mos6502.instructions.branch._bcc",
    "bcc_relative_0x90"
)


def add_bcc_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BCC instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(BCC_RELATIVE_0x90, "BCC_RELATIVE_0x90")
    instruction_set_class._value2member_map_[BCC_RELATIVE_0x90] = member
    setattr(instruction_set_class, "BCC_RELATIVE_0x90", BCC_RELATIVE_0x90)


def register_bcc_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BCC instructions in the InstructionSet."""
    add_bcc_to_instruction_set_enum(instruction_set_class)

    # BCC doesn't modify any flags
    bcc_relative_0x90_can_modify_flags: Byte = Byte()
    instruction_map[BCC_RELATIVE_0x90] = {
        "addressing": "relative",
        "assembler": "BCC {oper}",
        "opc": BCC_RELATIVE_0x90,
        "bytes": "2",
        "cycles": "2**",
        "flags": bcc_relative_0x90_can_modify_flags,
    }


__all__ = [
    "BCC_RELATIVE_0x90",
    "register_bcc_instructions",
]
