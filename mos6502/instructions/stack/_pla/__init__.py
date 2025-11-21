#!/usr/bin/env python3
"""PLA (Pull Accumulator from Stack) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#PLA
# Pull Accumulator from Stack
#
# pop A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	PLA	68	1	4
PLA_IMPLIED_0x68 = InstructionOpcode(
    0x68,
    "mos6502.instructions.stack._pla",
    "pla_implied_0x68"
)


def add_pla_to_instruction_set_enum(instruction_set_class) -> None:
    """Add PLA instruction to the InstructionSet enum dynamically."""
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

    pla_member = PseudoEnumMember(PLA_IMPLIED_0x68, "PLA_IMPLIED_0x68")
    instruction_set_class._value2member_map_[PLA_IMPLIED_0x68] = pla_member
    setattr(instruction_set_class, "PLA_IMPLIED_0x68", PLA_IMPLIED_0x68)


def register_pla_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register PLA instruction in the InstructionSet."""
    add_pla_to_instruction_set_enum(instruction_set_class)

    pla_implied_0x68_can_modify_flags: Byte = Byte()
    pla_implied_0x68_can_modify_flags[flags.N] = True
    pla_implied_0x68_can_modify_flags[flags.Z] = True
    instruction_map[PLA_IMPLIED_0x68] = {
        "addressing": "implied",
        "assembler": "PLA",
        "opc": PLA_IMPLIED_0x68,
        "bytes": "1",
        "cycles": "4",
        "flags": pla_implied_0x68_can_modify_flags,
    }


__all__ = ["PLA_IMPLIED_0x68", "register_pla_instructions"]
