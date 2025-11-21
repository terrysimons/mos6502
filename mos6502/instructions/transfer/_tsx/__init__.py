#!/usr/bin/env python3
"""TSX (Transfer Stack Pointer to Index X) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#TSX
# Transfer Stack Pointer to Index X
#
# S -> X
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TSX	BA	1	2
TSX_IMPLIED_0xBA = InstructionOpcode(
    0xBA,
    "mos6502.instructions.transfer._tsx",
    "tsx_implied_0xba"
)


def add_tsx_to_instruction_set_enum(instruction_set_class) -> None:
    """Add TSX instruction to the InstructionSet enum dynamically."""
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

    tsx_member = PseudoEnumMember(TSX_IMPLIED_0xBA, "TSX_IMPLIED_0xBA")
    instruction_set_class._value2member_map_[TSX_IMPLIED_0xBA] = tsx_member
    setattr(instruction_set_class, "TSX_IMPLIED_0xBA", TSX_IMPLIED_0xBA)


def register_tsx_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register TSX instruction in the InstructionSet."""
    add_tsx_to_instruction_set_enum(instruction_set_class)

    tsx_implied_0xba_can_modify_flags: Byte = Byte()
    tsx_implied_0xba_can_modify_flags[flags.N] = True
    tsx_implied_0xba_can_modify_flags[flags.Z] = True
    instruction_map[TSX_IMPLIED_0xBA] = {
        "addressing": "implied",
        "assembler": "TSX",
        "opc": TSX_IMPLIED_0xBA,
        "bytes": "1",
        "cycles": "2",
        "flags": tsx_implied_0xba_can_modify_flags,
    }


__all__ = ["TSX_IMPLIED_0xBA", "register_tsx_instructions"]
