#!/usr/bin/env python3
"""BRK (Force Break) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#BRK
# Force Break
#
# BRK initiates a software interrupt similar to a hardware
# interrupt (IRQ). The return address pushed to the stack is
# PC+2, providing an extra byte of spacing for a break mark
# (identifying a reason for the break.)
# The status register will be pushed to the stack with the break
# flag set to 1. However, when retrieved during RTI or by a PLP
# instruction, the break flag will be ignored.
# The interrupt disable flag is set to 1.
#
# Operation:
# - interrupt initiated
# - PC+2 pushed to stack
# - SR pushed to stack (with B flag set)
# - I flag set to 1
# N	Z	C	I	D	V
# -	-	-	1	-	-
# addressing	assembler	opc	bytes	cycles
# implied	BRK	00	1	7
BRK_IMPLIED_0x00 = InstructionOpcode(
    0x00,
    "mos6502.instructions._brk",
    "brk_implied_0x00"
)


def add_brk_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BRK instruction to the InstructionSet enum dynamically."""
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

    brk_member = PseudoEnumMember(BRK_IMPLIED_0x00, "BRK_IMPLIED_0x00")
    instruction_set_class._value2member_map_[BRK_IMPLIED_0x00] = brk_member
    setattr(instruction_set_class, "BRK_IMPLIED_0x00", BRK_IMPLIED_0x00)


def register_brk_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BRK instruction in the InstructionSet."""
    add_brk_to_instruction_set_enum(instruction_set_class)

    brk_implied_can_modify_flags: Byte = Byte()
    brk_implied_can_modify_flags[flags.I] = True
    instruction_map[BRK_IMPLIED_0x00] = {
        "addressing": "implied",
        "assembler": "BRK",
        "opc": BRK_IMPLIED_0x00,
        "bytes": "1",
        "cycles": "7",
        "flags": brk_implied_can_modify_flags,
    }


__all__ = ["BRK_IMPLIED_0x00", "register_brk_instructions"]
