#!/usr/bin/env python3
"""STY (Store Y Register) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#STY
# Store Y Register in Memory
#
# Y -> M
# N	Z	C	I	D	V
# -	-	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	STY oper	84	2	3
# zeropage,X	STY oper,X	94	2	4
# absolute	STY oper	8C	3	4

STY_ZEROPAGE_0x84 = InstructionOpcode(
    0x84,
    "mos6502.instructions.store._sty",
    "sty_zeropage_0x84"
)

STY_ZEROPAGE_X_0x94 = InstructionOpcode(
    0x94,
    "mos6502.instructions.store._sty",
    "sty_zeropage_x_0x94"
)

STY_ABSOLUTE_0x8C = InstructionOpcode(
    0x8C,
    "mos6502.instructions.store._sty",
    "sty_absolute_0x8c"
)


def add_sty_to_instruction_set_enum(instruction_set_class) -> None:
    """Add STY instructions to the InstructionSet enum dynamically."""
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

    for value, name in [
        (STY_ZEROPAGE_0x84, "STY_ZEROPAGE_0x84"),
        (STY_ZEROPAGE_X_0x94, "STY_ZEROPAGE_X_0x94"),
        (STY_ABSOLUTE_0x8C, "STY_ABSOLUTE_0x8C"),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_sty_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register STY instructions in the InstructionSet."""
    add_sty_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    sty_can_modify_flags: Byte = Byte()
    # STY doesn't modify any flags

    instruction_map[STY_ZEROPAGE_0x84] = {
        "addressing": "zeropage",
        "assembler": "STY {oper}",
        "opc": STY_ZEROPAGE_0x84,
        "bytes": "2",
        "cycles": "3",
        "flags": sty_can_modify_flags,
    }

    instruction_map[STY_ZEROPAGE_X_0x94] = {
        "addressing": "zeropage,X",
        "assembler": "STY {oper},X",
        "opc": STY_ZEROPAGE_X_0x94,
        "bytes": "2",
        "cycles": "4",
        "flags": sty_can_modify_flags,
    }

    instruction_map[STY_ABSOLUTE_0x8C] = {
        "addressing": "absolute",
        "assembler": "STY {oper}",
        "opc": STY_ABSOLUTE_0x8C,
        "bytes": "3",
        "cycles": "4",
        "flags": sty_can_modify_flags,
    }


__all__ = [
    "STY_ZEROPAGE_0x84",
    "STY_ZEROPAGE_X_0x94",
    "STY_ABSOLUTE_0x8C",
    "register_sty_instructions",
]
