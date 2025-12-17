#!/usr/bin/env python3
"""INY (Increment Index Y by One) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#INY
# Increment Index Y by One
#
# Y + 1 -> Y
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# implied	INY	C8	1	2
INY_IMPLIED_0xC8 = InstructionOpcode(
    0xC8,
    "mos6502.instructions.arithmetic._iny",
    "iny_implied_0xc8"
)


def add_iny_to_instruction_set_enum(instruction_set_class) -> None:
    """Add INY instruction to the InstructionSet enum dynamically."""
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

    iny_member = PseudoEnumMember(INY_IMPLIED_0xC8, "INY_IMPLIED_0xC8")
    instruction_set_class._value2member_map_[INY_IMPLIED_0xC8] = iny_member
    setattr(instruction_set_class, "INY_IMPLIED_0xC8", INY_IMPLIED_0xC8)


def register_iny_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register INY instruction in the InstructionSet."""
    add_iny_to_instruction_set_enum(instruction_set_class)

    iny_implied_0xc8_can_modify_flags: Byte = Byte()
    iny_implied_0xc8_can_modify_flags[flags.N] = True
    iny_implied_0xc8_can_modify_flags[flags.Z] = True
    instruction_map[INY_IMPLIED_0xC8] = {
        "addressing": "implied",
        "assembler": "INY",
        "opc": INY_IMPLIED_0xC8,
        "bytes": "1",
        "cycles": "2",
        "flags": iny_implied_0xc8_can_modify_flags,
    }


__all__ = ["INY_IMPLIED_0xC8", "register_iny_instructions"]
