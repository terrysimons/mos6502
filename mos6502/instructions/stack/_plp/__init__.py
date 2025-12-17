#!/usr/bin/env python3
"""PLP (Pull Processor Status from Stack) instruction."""
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#PLP
# Pull Processor Status from Stack
#
# pop P
# N	Z	C	I	D	V
# from stack
# addressing	assembler	opc	bytes	cycles
# implied	PLP	28	1	4
PLP_IMPLIED_0x28 = InstructionOpcode(
    0x28,
    "mos6502.instructions.stack._plp",
    "plp_implied_0x28"
)


def add_plp_to_instruction_set_enum(instruction_set_class) -> None:
    """Add PLP instruction to the InstructionSet enum dynamically."""
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

    plp_member = PseudoEnumMember(PLP_IMPLIED_0x28, "PLP_IMPLIED_0x28")
    instruction_set_class._value2member_map_[PLP_IMPLIED_0x28] = plp_member
    setattr(instruction_set_class, "PLP_IMPLIED_0x28", PLP_IMPLIED_0x28)


def register_plp_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register PLP instruction in the InstructionSet."""
    add_plp_to_instruction_set_enum(instruction_set_class)

    # PLP restores all flags from stack
    plp_implied_0x28_can_modify_flags: Byte = Byte(0xFF)  # All flags can be modified
    instruction_map[PLP_IMPLIED_0x28] = {
        "addressing": "implied",
        "assembler": "PLP",
        "opc": PLP_IMPLIED_0x28,
        "bytes": "1",
        "cycles": "4",
        "flags": plp_implied_0x28_can_modify_flags,
    }


__all__ = ["PLP_IMPLIED_0x28", "register_plp_instructions"]
