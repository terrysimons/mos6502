#!/usr/bin/env python3
"""TXA (Transfer Index X to Accumulator) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#TXA
# Transfer Index X to Accumulator
#
# X -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TXA	8A	1	2
TXA_IMPLIED_0x8A = InstructionOpcode(
    0x8A,
    "mos6502.instructions.transfer._txa",
    "txa_implied_0x8a"
)


def add_txa_to_instruction_set_enum(instruction_set_class) -> None:
    """Add TXA instruction to the InstructionSet enum dynamically."""
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

    txa_member = PseudoEnumMember(TXA_IMPLIED_0x8A, 'TXA_IMPLIED_0x8A')
    instruction_set_class._value2member_map_[TXA_IMPLIED_0x8A] = txa_member
    setattr(instruction_set_class, 'TXA_IMPLIED_0x8A', TXA_IMPLIED_0x8A)


def register_txa_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register TXA instruction in the InstructionSet."""
    add_txa_to_instruction_set_enum(instruction_set_class)

    txa_implied_0x8a_can_modify_flags: Byte = Byte()
    txa_implied_0x8a_can_modify_flags[flags.N] = True
    txa_implied_0x8a_can_modify_flags[flags.Z] = True
    instruction_map[TXA_IMPLIED_0x8A] = {
        "addressing": "implied",
        "assembler": "TXA",
        "opc": TXA_IMPLIED_0x8A,
        "bytes": "1",
        "cycles": "2",
        "flags": txa_implied_0x8a_can_modify_flags,
    }


__all__ = ['TXA_IMPLIED_0x8A', 'register_txa_instructions']
