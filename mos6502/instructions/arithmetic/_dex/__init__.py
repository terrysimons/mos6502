#!/usr/bin/env python3
"""DEX (Decrement Index X by One) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#DEX
# Decrement Index X by One
#
# X - 1 -> X
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	DEX	CA	1	2
DEX_IMPLIED_0xCA = InstructionOpcode(
    0xCA,
    "mos6502.instructions.arithmetic._dex",
    "dex_implied_0xca"
)


def add_dex_to_instruction_set_enum(instruction_set_class) -> None:
    """Add DEX instruction to the InstructionSet enum dynamically."""
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

    dex_member = PseudoEnumMember(DEX_IMPLIED_0xCA, "DEX_IMPLIED_0xCA")
    instruction_set_class._value2member_map_[DEX_IMPLIED_0xCA] = dex_member
    setattr(instruction_set_class, "DEX_IMPLIED_0xCA", DEX_IMPLIED_0xCA)


def register_dex_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register DEX instruction in the InstructionSet."""
    add_dex_to_instruction_set_enum(instruction_set_class)

    dex_implied_0xca_can_modify_flags: Byte = Byte()
    dex_implied_0xca_can_modify_flags[flags.N] = True
    dex_implied_0xca_can_modify_flags[flags.Z] = True
    instruction_map[DEX_IMPLIED_0xCA] = {
        "addressing": "implied",
        "assembler": "DEX",
        "opc": DEX_IMPLIED_0xCA,
        "bytes": "1",
        "cycles": "2",
        "flags": dex_implied_0xca_can_modify_flags,
    }


__all__ = ["DEX_IMPLIED_0xCA", "register_dex_instructions"]
