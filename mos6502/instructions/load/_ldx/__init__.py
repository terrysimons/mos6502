#!/usr/bin/env python3
"""LDX (Load X Register) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#LDX
# Load X Register with Memory
#
# M -> X
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# immediate	LDX #oper	A2	2	2
# zeropage	LDX oper	A6	2	3
# zeropage,Y	LDX oper,Y	B6	2	4
# absolute	LDX oper	AE	3	4
# absolute,Y	LDX oper,Y	BE	3	4*

LDX_IMMEDIATE_0xA2 = InstructionOpcode(
    0xA2,
    "mos6502.instructions.load._ldx",
    "ldx_immediate_0xa2"
)

LDX_ZEROPAGE_0xA6 = InstructionOpcode(
    0xA6,
    "mos6502.instructions.load._ldx",
    "ldx_zeropage_0xa6"
)

LDX_ZEROPAGE_Y_0xB6 = InstructionOpcode(
    0xB6,
    "mos6502.instructions.load._ldx",
    "ldx_zeropage_y_0xb6"
)

LDX_ABSOLUTE_0xAE = InstructionOpcode(
    0xAE,
    "mos6502.instructions.load._ldx",
    "ldx_absolute_0xae"
)

LDX_ABSOLUTE_Y_0xBE = InstructionOpcode(
    0xBE,
    "mos6502.instructions.load._ldx",
    "ldx_absolute_y_0xbe"
)


def add_ldx_to_instruction_set_enum(instruction_set_class) -> None:
    """Add LDX instructions to the InstructionSet enum dynamically."""
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
        (LDX_IMMEDIATE_0xA2, 'LDX_IMMEDIATE_0xA2'),
        (LDX_ZEROPAGE_0xA6, 'LDX_ZEROPAGE_0xA6'),
        (LDX_ZEROPAGE_Y_0xB6, 'LDX_ZEROPAGE_Y_0xB6'),
        (LDX_ABSOLUTE_0xAE, 'LDX_ABSOLUTE_0xAE'),
        (LDX_ABSOLUTE_Y_0xBE, 'LDX_ABSOLUTE_Y_0xBE'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_ldx_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register LDX instructions in the InstructionSet."""
    add_ldx_to_instruction_set_enum(instruction_set_class)

    ldx_can_modify_flags: Byte = Byte()
    ldx_can_modify_flags[flags.N] = True
    ldx_can_modify_flags[flags.Z] = True

    instruction_map[LDX_IMMEDIATE_0xA2] = {
        "addressing": "immediate",
        "assembler": "LDX #{oper}",
        "opc": LDX_IMMEDIATE_0xA2,
        "bytes": "2",
        "cycles": "2",
        "flags": ldx_can_modify_flags,
    }

    instruction_map[LDX_ZEROPAGE_0xA6] = {
        "addressing": "zeropage",
        "assembler": "LDX {oper}",
        "opc": LDX_ZEROPAGE_0xA6,
        "bytes": "2",
        "cycles": "3",
        "flags": ldx_can_modify_flags,
    }

    instruction_map[LDX_ZEROPAGE_Y_0xB6] = {
        "addressing": "zeropage,Y",
        "assembler": "LDX {oper},Y",
        "opc": LDX_ZEROPAGE_Y_0xB6,
        "bytes": "2",
        "cycles": "4",
        "flags": ldx_can_modify_flags,
    }

    instruction_map[LDX_ABSOLUTE_0xAE] = {
        "addressing": "absolute",
        "assembler": "LDX {oper}",
        "opc": LDX_ABSOLUTE_0xAE,
        "bytes": "3",
        "cycles": "4",
        "flags": ldx_can_modify_flags,
    }

    instruction_map[LDX_ABSOLUTE_Y_0xBE] = {
        "addressing": "absolute,Y",
        "assembler": "LDX {oper},Y",
        "opc": LDX_ABSOLUTE_Y_0xBE,
        "bytes": "3",
        "cycles": "4*",
        "flags": ldx_can_modify_flags,
    }


__all__ = [
    'LDX_IMMEDIATE_0xA2',
    'LDX_ZEROPAGE_0xA6',
    'LDX_ZEROPAGE_Y_0xB6',
    'LDX_ABSOLUTE_0xAE',
    'LDX_ABSOLUTE_Y_0xBE',
    'register_ldx_instructions',
]
