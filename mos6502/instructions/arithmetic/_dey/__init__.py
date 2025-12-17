#!/usr/bin/env python3
"""DEY (Decrement Index Y by One) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#DEY
# Decrement Index Y by One
#
# Y - 1 -> Y
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	DEY	88	1	2
DEY_IMPLIED_0x88 = InstructionOpcode(
    0x88,
    "mos6502.instructions.arithmetic._dey",
    "dey_implied_0x88"
)


def add_dey_to_instruction_set_enum(instruction_set_class) -> None:
    """Add DEY instruction to the InstructionSet enum dynamically."""
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

    dey_member = PseudoEnumMember(DEY_IMPLIED_0x88, "DEY_IMPLIED_0x88")
    instruction_set_class._value2member_map_[DEY_IMPLIED_0x88] = dey_member
    setattr(instruction_set_class, "DEY_IMPLIED_0x88", DEY_IMPLIED_0x88)


def register_dey_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register DEY instruction in the InstructionSet."""
    add_dey_to_instruction_set_enum(instruction_set_class)

    dey_implied_0x88_can_modify_flags: Byte = Byte()
    dey_implied_0x88_can_modify_flags[flags.N] = True
    dey_implied_0x88_can_modify_flags[flags.Z] = True
    instruction_map[DEY_IMPLIED_0x88] = {
        "addressing": "implied",
        "assembler": "DEY",
        "opc": DEY_IMPLIED_0x88,
        "bytes": "1",
        "cycles": "2",
        "flags": dey_implied_0x88_can_modify_flags,
    }


__all__ = ["DEY_IMPLIED_0x88", "register_dey_instructions"]
