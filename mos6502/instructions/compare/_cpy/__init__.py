#!/usr/bin/env python3
"""CPY (Compare Y Register) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#CPY
# Compare Y Register with Memory
#
# Y - M (affects flags only, doesn't store result)
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	CPY #oper	C0	2	2
# zeropage	CPY oper	C4	2	3
# absolute	CPY oper	CC	3	4

CPY_IMMEDIATE_0xC0 = InstructionOpcode(
    0xC0,
    "mos6502.instructions.compare._cpy",
    "cpy_immediate_0xc0"
)

CPY_ZEROPAGE_0xC4 = InstructionOpcode(
    0xC4,
    "mos6502.instructions.compare._cpy",
    "cpy_zeropage_0xc4"
)

CPY_ABSOLUTE_0xCC = InstructionOpcode(
    0xCC,
    "mos6502.instructions.compare._cpy",
    "cpy_absolute_0xcc"
)


def add_cpy_to_instruction_set_enum(instruction_set_class) -> None:
    """Add CPY instructions to the InstructionSet enum dynamically."""
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
        (CPY_IMMEDIATE_0xC0, "CPY_IMMEDIATE_0xC0"),
        (CPY_ZEROPAGE_0xC4, "CPY_ZEROPAGE_0xC4"),
        (CPY_ABSOLUTE_0xCC, "CPY_ABSOLUTE_0xCC"),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_cpy_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register CPY instructions in the InstructionSet."""
    add_cpy_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    cpy_can_modify_flags: Byte = Byte()
    cpy_can_modify_flags[flags.N] = 1
    cpy_can_modify_flags[flags.Z] = 1
    cpy_can_modify_flags[flags.C] = 1

    instruction_map[CPY_IMMEDIATE_0xC0] = {
        "addressing": "immediate",
        "assembler": "CPY #{oper}",
        "opc": CPY_IMMEDIATE_0xC0,
        "bytes": "2",
        "cycles": "2",
        "flags": cpy_can_modify_flags,
    }

    instruction_map[CPY_ZEROPAGE_0xC4] = {
        "addressing": "zeropage",
        "assembler": "CPY {oper}",
        "opc": CPY_ZEROPAGE_0xC4,
        "bytes": "2",
        "cycles": "3",
        "flags": cpy_can_modify_flags,
    }

    instruction_map[CPY_ABSOLUTE_0xCC] = {
        "addressing": "absolute",
        "assembler": "CPY {oper}",
        "opc": CPY_ABSOLUTE_0xCC,
        "bytes": "3",
        "cycles": "4",
        "flags": cpy_can_modify_flags,
    }


__all__ = [
    "CPY_IMMEDIATE_0xC0",
    "CPY_ZEROPAGE_0xC4",
    "CPY_ABSOLUTE_0xCC",
    "register_cpy_instructions",
]
