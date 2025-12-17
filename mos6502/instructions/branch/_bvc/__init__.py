#!/usr/bin/env python3
"""BVC (Branch on Overflow Clear) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#BVC
# Branch on Overflow Clear
# branch on V = 0
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# relative	BVC oper	50	2	2**
BVC_RELATIVE_0x50 = InstructionOpcode(
    0x50,
    "mos6502.instructions.branch._bvc",
    "bvc_relative_0x50"
)


def add_bvc_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BVC instructions to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(BVC_RELATIVE_0x50, "BVC_RELATIVE_0x50")
    instruction_set_class._value2member_map_[BVC_RELATIVE_0x50] = member
    setattr(instruction_set_class, "BVC_RELATIVE_0x50", BVC_RELATIVE_0x50)


def register_bvc_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BVC instructions in the InstructionSet."""
    add_bvc_to_instruction_set_enum(instruction_set_class)

    bvc_relative_0x50_can_modify_flags: Byte = Byte()
    instruction_map[BVC_RELATIVE_0x50] = {
        "addressing": "relative",
        "assembler": "BVC {oper}",
        "opc": BVC_RELATIVE_0x50,
        "bytes": "2",
        "cycles": "2**",
        "flags": bvc_relative_0x50_can_modify_flags,
    }


__all__ = ["BVC_RELATIVE_0x50", "register_bvc_instructions"]
