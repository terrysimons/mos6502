#!/usr/bin/env python3
"""NOP (No Operation) instruction."""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#NOP
# No Operation
#
# ---
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	NOP	EA	1	2
NOP_IMPLIED_0xEA = InstructionOpcode(
    0xEA,
    "mos6502.instructions._nop",
    "nop_implied_0xea"
)


def add_nop_to_instruction_set_enum(instruction_set_class) -> None:
    """Add NOP instruction to the InstructionSet enum dynamically."""
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
        def name(self) -> str:
            return self._name

        @property
        def value(self) -> int:
            return self._value_

    nop_member = PseudoEnumMember(NOP_IMPLIED_0xEA, "NOP_IMPLIED_0xEA")
    instruction_set_class._value2member_map_[NOP_IMPLIED_0xEA] = nop_member
    setattr(instruction_set_class, "NOP_IMPLIED_0xEA", NOP_IMPLIED_0xEA)


def register_nop_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register NOP instruction in the InstructionSet map."""
    # Add to enum
    add_nop_to_instruction_set_enum(instruction_set_class)

    # Add to map
    nop_implied_0xea_can_modify_flags: Byte = Byte()
    instruction_map[NOP_IMPLIED_0xEA] = {
        "addressing": "implied",
        "assembler": "NOP",
        "opc": NOP_IMPLIED_0xEA,
        "bytes": "1",
        "cycles": "2",
        "flags": nop_implied_0xea_can_modify_flags,
    }


__all__ = ["NOP_IMPLIED_0xEA", "register_nop_instructions"]
