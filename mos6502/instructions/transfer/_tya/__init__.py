#!/usr/bin/env python3
"""TYA (Transfer Index Y to Accumulator) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#TYA
# Transfer Index Y to Accumulator
#
# Y -> A
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	TYA	98	1	2
TYA_IMPLIED_0x98 = InstructionOpcode(
    0x98,
    "mos6502.instructions.transfer._tya",
    "tya_implied_0x98"
)


def add_tya_to_instruction_set_enum(instruction_set_class) -> None:
    """Add TYA instruction to the InstructionSet enum dynamically."""
    class PseudoEnumMember:
        """MicroPython-compatible pseudo-enum member."""
        __slots__ = ('_value_', '_name')

        def __init__(self, value, name):
            self._value_ = int(value)
            self._name = name

        @property
        def name(self):
            return self._name

        @property
        def value(self):
            return self._value_

        def __int__(self):
            return self._value_

        def __eq__(self, other):
            if isinstance(other, int):
                return self._value_ == other
            return NotImplemented

        def __hash__(self):
            return hash(self._value_)

    tya_member = PseudoEnumMember(TYA_IMPLIED_0x98, "TYA_IMPLIED_0x98")
    instruction_set_class._value2member_map_[TYA_IMPLIED_0x98] = tya_member
    setattr(instruction_set_class, "TYA_IMPLIED_0x98", TYA_IMPLIED_0x98)


def register_tya_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register TYA instruction in the InstructionSet."""
    add_tya_to_instruction_set_enum(instruction_set_class)

    tya_implied_0x98_can_modify_flags: Byte = Byte()
    tya_implied_0x98_can_modify_flags[flags.N] = True
    tya_implied_0x98_can_modify_flags[flags.Z] = True
    instruction_map[TYA_IMPLIED_0x98] = {
        "addressing": "implied",
        "assembler": "TYA",
        "opc": TYA_IMPLIED_0x98,
        "bytes": "1",
        "cycles": "2",
        "flags": tya_implied_0x98_can_modify_flags,
    }


__all__ = ["TYA_IMPLIED_0x98", "register_tya_instructions"]
