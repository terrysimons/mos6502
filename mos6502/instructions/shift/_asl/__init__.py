#!/usr/bin/env python3
"""ASL (Arithmetic Shift Left) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#ASL
# Arithmetic Shift Left
#
# Shift Left One Bit (Memory or Accumulator)
# C <- [76543210] <- 0
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# accumulator	ASL A	0A	1	2
# zeropage	ASL oper	06	2	5
# zeropage,X	ASL oper,X	16	2	6
# absolute	ASL oper	0E	3	6
# absolute,X	ASL oper,X	1E	3	7

ASL_ACCUMULATOR_0x0A = InstructionOpcode(
    0x0A,
    "mos6502.instructions.shift._asl",
    "asl_accumulator_0x0a"
)

ASL_ZEROPAGE_0x06 = InstructionOpcode(
    0x06,
    "mos6502.instructions.shift._asl",
    "asl_zeropage_0x06"
)

ASL_ZEROPAGE_X_0x16 = InstructionOpcode(
    0x16,
    "mos6502.instructions.shift._asl",
    "asl_zeropage_x_0x16"
)

ASL_ABSOLUTE_0x0E = InstructionOpcode(
    0x0E,
    "mos6502.instructions.shift._asl",
    "asl_absolute_0x0e"
)

ASL_ABSOLUTE_X_0x1E = InstructionOpcode(
    0x1E,
    "mos6502.instructions.shift._asl",
    "asl_absolute_x_0x1e"
)


def add_asl_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ASL instructions to the InstructionSet enum dynamically."""
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
        (ASL_ACCUMULATOR_0x0A, 'ASL_ACCUMULATOR_0x0A'),
        (ASL_ZEROPAGE_0x06, 'ASL_ZEROPAGE_0x06'),
        (ASL_ZEROPAGE_X_0x16, 'ASL_ZEROPAGE_X_0x16'),
        (ASL_ABSOLUTE_0x0E, 'ASL_ABSOLUTE_0x0E'),
        (ASL_ABSOLUTE_X_0x1E, 'ASL_ABSOLUTE_X_0x1E'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_asl_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ASL instructions in the InstructionSet."""
    add_asl_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    asl_can_modify_flags: Byte = Byte()
    asl_can_modify_flags[flags.N] = 1
    asl_can_modify_flags[flags.Z] = 1
    asl_can_modify_flags[flags.C] = 1

    instruction_map[ASL_ACCUMULATOR_0x0A] = {
        "addressing": "accumulator",
        "assembler": "ASL A",
        "opc": ASL_ACCUMULATOR_0x0A,
        "bytes": "1",
        "cycles": "2",
        "flags": asl_can_modify_flags,
    }

    instruction_map[ASL_ZEROPAGE_0x06] = {
        "addressing": "zeropage",
        "assembler": "ASL {oper}",
        "opc": ASL_ZEROPAGE_0x06,
        "bytes": "2",
        "cycles": "5",
        "flags": asl_can_modify_flags,
    }

    instruction_map[ASL_ZEROPAGE_X_0x16] = {
        "addressing": "zeropage,X",
        "assembler": "ASL {oper},X",
        "opc": ASL_ZEROPAGE_X_0x16,
        "bytes": "2",
        "cycles": "6",
        "flags": asl_can_modify_flags,
    }

    instruction_map[ASL_ABSOLUTE_0x0E] = {
        "addressing": "absolute",
        "assembler": "ASL {oper}",
        "opc": ASL_ABSOLUTE_0x0E,
        "bytes": "3",
        "cycles": "6",
        "flags": asl_can_modify_flags,
    }

    instruction_map[ASL_ABSOLUTE_X_0x1E] = {
        "addressing": "absolute,X",
        "assembler": "ASL {oper},X",
        "opc": ASL_ABSOLUTE_X_0x1E,
        "bytes": "3",
        "cycles": "7",
        "flags": asl_can_modify_flags,
    }


__all__ = [
    'ASL_ACCUMULATOR_0x0A',
    'ASL_ZEROPAGE_0x06',
    'ASL_ZEROPAGE_X_0x16',
    'ASL_ABSOLUTE_0x0E',
    'ASL_ABSOLUTE_X_0x1E',
    'register_asl_instructions',
]
