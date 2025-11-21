#!/usr/bin/env python3
"""INX (Increment Index X by One) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#INX
# Increment Index X by One
#
# X + 1 -> X
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	INX	E8	1	2
INX_IMPLIED_0xE8 = InstructionOpcode(
    0xE8,
    "mos6502.instructions.arithmetic._inx",
    "inx_implied_0xe8"
)


def add_inx_to_instruction_set_enum(instruction_set_class) -> None:
    """Add INX instruction to the InstructionSet enum dynamically."""
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

    inx_member = PseudoEnumMember(INX_IMPLIED_0xE8, "INX_IMPLIED_0xE8")
    instruction_set_class._value2member_map_[INX_IMPLIED_0xE8] = inx_member
    setattr(instruction_set_class, "INX_IMPLIED_0xE8", INX_IMPLIED_0xE8)


def register_inx_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register INX instruction in the InstructionSet."""
    add_inx_to_instruction_set_enum(instruction_set_class)

    inx_implied_0xe8_can_modify_flags: Byte = Byte()
    inx_implied_0xe8_can_modify_flags[flags.N] = True
    inx_implied_0xe8_can_modify_flags[flags.Z] = True
    instruction_map[INX_IMPLIED_0xE8] = {
        "addressing": "implied",
        "assembler": "INX",
        "opc": INX_IMPLIED_0xE8,
        "bytes": "1",
        "cycles": "2",
        "flags": inx_implied_0xe8_can_modify_flags,
    }


__all__ = ["INX_IMPLIED_0xE8", "register_inx_instructions"]
