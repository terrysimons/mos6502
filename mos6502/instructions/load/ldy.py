#!/usr/bin/env python3
"""LDY (Load Index Y with Memory) instruction."""
from typing import Literal

from mos6502 import flags
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#LDY
#
# Load Index Y with Memory
#
# M -> Y
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	LDY #oper	A0	2	2
# zeropage	LDY oper	A4	2	3
# zeropage,X	LDY oper,X	B4	2	4
# absolute	LDY oper	AC	3	4
# absolute,X	LDY oper,X	BC	3	4*
LDY_IMMEDIATE_0xA0: Literal[160] = 0xA0
LDY_ZEROPAGE_0xA4: Literal[164] = 0xA4
LDY_ZEROPAGE_X_0xB4: Literal[180] = 0xB4
LDY_ABSOLUTE_0xAC: Literal[172] = 0xAC
LDY_ABSOLUTE_X_0xBC: Literal[188] = 0xBC


def add_ldy_to_instruction_set_enum(instruction_set_class) -> None:
    """Add LDY instructions to the InstructionSet enum dynamically."""
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

    for value, name in [
        (LDY_IMMEDIATE_0xA0, 'LDY_IMMEDIATE_0xA0'),
        (LDY_ZEROPAGE_0xA4, 'LDY_ZEROPAGE_0xA4'),
        (LDY_ZEROPAGE_X_0xB4, 'LDY_ZEROPAGE_X_0xB4'),
        (LDY_ABSOLUTE_0xAC, 'LDY_ABSOLUTE_0xAC'),
        (LDY_ABSOLUTE_X_0xBC, 'LDY_ABSOLUTE_X_0xBC'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_ldy_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register LDY instructions in the InstructionSet."""
    # Add to enum
    add_ldy_to_instruction_set_enum(instruction_set_class)

    # Add to map
    ldy_immediate_0xa0_can_modify_flags: Byte = Byte()
    ldy_immediate_0xa0_can_modify_flags[flags.N] = True
    ldy_immediate_0xa0_can_modify_flags[flags.Z] = True

    instruction_map[LDY_IMMEDIATE_0xA0] = {
        "addressing": "immediate",
        "assembler": "LDY #{oper}",
        "opc": LDY_IMMEDIATE_0xA0,
        "bytes": "2",
        "cycles": "2",
        "flags": ldy_immediate_0xa0_can_modify_flags,
    }

    ldy_zeropage_0xa4_can_modify_flags: Byte = ldy_immediate_0xa0_can_modify_flags
    instruction_map[LDY_ZEROPAGE_0xA4] = {
        "addressing": "zeropage",
        "assembler": "LDY {oper}",
        "opc": LDY_ZEROPAGE_0xA4,
        "bytes": "2",
        "cycles": "3",
        "flags": ldy_zeropage_0xa4_can_modify_flags,
    }

    ldy_zeropage_x_0xb4_can_modify_flags: Byte = ldy_immediate_0xa0_can_modify_flags
    instruction_map[LDY_ZEROPAGE_X_0xB4] = {
        "addressing": "zeropage,X",
        "assembler": "LDY {oper},X",
        "opc": LDY_ZEROPAGE_X_0xB4,
        "bytes": "2",
        "cycles": "4",
        "flags": ldy_zeropage_x_0xb4_can_modify_flags,
    }

    ldy_absolute_0xac_can_modify_flags: Byte = ldy_immediate_0xa0_can_modify_flags
    instruction_map[LDY_ABSOLUTE_0xAC] = {
        "addressing": "absolute",
        "assembler": "LDY {oper}",
        "opc": LDY_ABSOLUTE_0xAC,
        "bytes": "3",
        "cycles": "4",
        "flags": ldy_absolute_0xac_can_modify_flags,
    }

    ldy_absolute_x_0xbc_can_modify_flags: Byte = ldy_immediate_0xa0_can_modify_flags
    instruction_map[LDY_ABSOLUTE_X_0xBC] = {
        "addressing": "absolute,X",
        "assembler": "LDY {oper},X",
        "opc": LDY_ABSOLUTE_X_0xBC,
        "bytes": "3",
        "cycles": "4*",
        "flags": ldy_absolute_x_0xbc_can_modify_flags,
    }


__all__ = [
    'LDY_IMMEDIATE_0xA0',
    'LDY_ZEROPAGE_0xA4',
    'LDY_ZEROPAGE_X_0xB4',
    'LDY_ABSOLUTE_0xAC',
    'LDY_ABSOLUTE_X_0xBC',
    'register_ldy_instructions',
]
