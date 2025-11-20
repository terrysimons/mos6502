#!/usr/bin/env python3
"""DEC (Decrement Memory) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#DEC
# Decrement Memory by One
#
# M - 1 -> M
# N	Z	C	I	D	V
# +	+	-	-	-	-
# addressing	assembler	opc	bytes	cycles
# zeropage	DEC oper	C6	2	5
# zeropage,X	DEC oper,X	D6	2	6
# absolute	DEC oper	CE	3	6
# absolute,X	DEC oper,X	DE	3	7

DEC_ZEROPAGE_0xC6 = InstructionOpcode(
    0xC6,
    "mos6502.instructions.arithmetic._dec",
    "dec_zeropage_0xc6"
)

DEC_ZEROPAGE_X_0xD6 = InstructionOpcode(
    0xD6,
    "mos6502.instructions.arithmetic._dec",
    "dec_zeropage_x_0xd6"
)

DEC_ABSOLUTE_0xCE = InstructionOpcode(
    0xCE,
    "mos6502.instructions.arithmetic._dec",
    "dec_absolute_0xce"
)

DEC_ABSOLUTE_X_0xDE = InstructionOpcode(
    0xDE,
    "mos6502.instructions.arithmetic._dec",
    "dec_absolute_x_0xde"
)


def add_dec_to_instruction_set_enum(instruction_set_class) -> None:
    """Add DEC instructions to the InstructionSet enum dynamically."""
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
        (DEC_ZEROPAGE_0xC6, 'DEC_ZEROPAGE_0xC6'),
        (DEC_ZEROPAGE_X_0xD6, 'DEC_ZEROPAGE_X_0xD6'),
        (DEC_ABSOLUTE_0xCE, 'DEC_ABSOLUTE_0xCE'),
        (DEC_ABSOLUTE_X_0xDE, 'DEC_ABSOLUTE_X_0xDE'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_dec_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register DEC instructions in the InstructionSet."""
    add_dec_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    dec_can_modify_flags: Byte = Byte()
    dec_can_modify_flags[flags.N] = 1
    dec_can_modify_flags[flags.Z] = 1

    instruction_map[DEC_ZEROPAGE_0xC6] = {
        "addressing": "zeropage",
        "assembler": "DEC {oper}",
        "opc": DEC_ZEROPAGE_0xC6,
        "bytes": "2",
        "cycles": "5",
        "flags": dec_can_modify_flags,
    }

    instruction_map[DEC_ZEROPAGE_X_0xD6] = {
        "addressing": "zeropage,X",
        "assembler": "DEC {oper},X",
        "opc": DEC_ZEROPAGE_X_0xD6,
        "bytes": "2",
        "cycles": "6",
        "flags": dec_can_modify_flags,
    }

    instruction_map[DEC_ABSOLUTE_0xCE] = {
        "addressing": "absolute",
        "assembler": "DEC {oper}",
        "opc": DEC_ABSOLUTE_0xCE,
        "bytes": "3",
        "cycles": "6",
        "flags": dec_can_modify_flags,
    }

    instruction_map[DEC_ABSOLUTE_X_0xDE] = {
        "addressing": "absolute,X",
        "assembler": "DEC {oper},X",
        "opc": DEC_ABSOLUTE_X_0xDE,
        "bytes": "3",
        "cycles": "7",
        "flags": dec_can_modify_flags,
    }


__all__ = [
    'DEC_ZEROPAGE_0xC6',
    'DEC_ZEROPAGE_X_0xD6',
    'DEC_ABSOLUTE_0xCE',
    'DEC_ABSOLUTE_X_0xDE',
    'register_dec_instructions',
]
