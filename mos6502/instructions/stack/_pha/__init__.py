#!/usr/bin/env python3
"""PHA (Push Accumulator on Stack) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#PHA
# Push Accumulator on Stack
#
# push A
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	PHA	48	1	3
PHA_IMPLIED_0x48 = InstructionOpcode(
    0x48,
    "mos6502.instructions.stack._pha",
    "pha_implied_0x48"
)


def add_pha_to_instruction_set_enum(instruction_set_class) -> None:
    """Add PHA instruction to the InstructionSet enum dynamically."""
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

    pha_member = PseudoEnumMember(PHA_IMPLIED_0x48, 'PHA_IMPLIED_0x48')
    instruction_set_class._value2member_map_[PHA_IMPLIED_0x48] = pha_member
    setattr(instruction_set_class, 'PHA_IMPLIED_0x48', PHA_IMPLIED_0x48)


def register_pha_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register PHA instruction in the InstructionSet."""
    add_pha_to_instruction_set_enum(instruction_set_class)

    # PHA doesn't modify any flags
    pha_implied_0x48_can_modify_flags: Byte = Byte()
    instruction_map[PHA_IMPLIED_0x48] = {
        "addressing": "implied",
        "assembler": "PHA",
        "opc": PHA_IMPLIED_0x48,
        "bytes": "1",
        "cycles": "3",
        "flags": pha_implied_0x48_can_modify_flags,
    }


__all__ = ['PHA_IMPLIED_0x48', 'register_pha_instructions']
