#!/usr/bin/env python3
"""ROR (Rotate Right) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#ROR
# Rotate Right
#
# Rotate One Bit Right (Memory or Accumulator)
# C -> [76543210] -> C
#
# N	Z	C	I	D	V
# +	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# accumulator	ROR A	6A	1	2
# zeropage	ROR oper	66	2	5
# zeropage,X	ROR oper,X	76	2	6
# absolute	ROR oper	6E	3	6
# absolute,X	ROR oper,X	7E	3	7

ROR_ACCUMULATOR_0x6A = InstructionOpcode(
    0x6A,
    "mos6502.instructions.shift._ror",
    "ror_accumulator_0x6a"
)

ROR_ZEROPAGE_0x66 = InstructionOpcode(
    0x66,
    "mos6502.instructions.shift._ror",
    "ror_zeropage_0x66"
)

ROR_ZEROPAGE_X_0x76 = InstructionOpcode(
    0x76,
    "mos6502.instructions.shift._ror",
    "ror_zeropage_x_0x76"
)

ROR_ABSOLUTE_0x6E = InstructionOpcode(
    0x6E,
    "mos6502.instructions.shift._ror",
    "ror_absolute_0x6e"
)

ROR_ABSOLUTE_X_0x7E = InstructionOpcode(
    0x7E,
    "mos6502.instructions.shift._ror",
    "ror_absolute_x_0x7e"
)


def add_ror_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ROR instructions to the InstructionSet enum dynamically."""
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
        (ROR_ACCUMULATOR_0x6A, 'ROR_ACCUMULATOR_0x6A'),
        (ROR_ZEROPAGE_0x66, 'ROR_ZEROPAGE_0x66'),
        (ROR_ZEROPAGE_X_0x76, 'ROR_ZEROPAGE_X_0x76'),
        (ROR_ABSOLUTE_0x6E, 'ROR_ABSOLUTE_0x6E'),
        (ROR_ABSOLUTE_X_0x7E, 'ROR_ABSOLUTE_X_0x7E'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_ror_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ROR instructions in the InstructionSet."""
    add_ror_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    ror_can_modify_flags: Byte = Byte()
    ror_can_modify_flags[flags.N] = 1
    ror_can_modify_flags[flags.Z] = 1
    ror_can_modify_flags[flags.C] = 1

    instruction_map[ROR_ACCUMULATOR_0x6A] = {
        "addressing": "accumulator",
        "assembler": "ROR A",
        "opc": ROR_ACCUMULATOR_0x6A,
        "bytes": "1",
        "cycles": "2",
        "flags": ror_can_modify_flags,
    }

    instruction_map[ROR_ZEROPAGE_0x66] = {
        "addressing": "zeropage",
        "assembler": "ROR {oper}",
        "opc": ROR_ZEROPAGE_0x66,
        "bytes": "2",
        "cycles": "5",
        "flags": ror_can_modify_flags,
    }

    instruction_map[ROR_ZEROPAGE_X_0x76] = {
        "addressing": "zeropage,X",
        "assembler": "ROR {oper},X",
        "opc": ROR_ZEROPAGE_X_0x76,
        "bytes": "2",
        "cycles": "6",
        "flags": ror_can_modify_flags,
    }

    instruction_map[ROR_ABSOLUTE_0x6E] = {
        "addressing": "absolute",
        "assembler": "ROR {oper}",
        "opc": ROR_ABSOLUTE_0x6E,
        "bytes": "3",
        "cycles": "6",
        "flags": ror_can_modify_flags,
    }

    instruction_map[ROR_ABSOLUTE_X_0x7E] = {
        "addressing": "absolute,X",
        "assembler": "ROR {oper},X",
        "opc": ROR_ABSOLUTE_X_0x7E,
        "bytes": "3",
        "cycles": "7",
        "flags": ror_can_modify_flags,
    }


__all__ = [
    'ROR_ACCUMULATOR_0x6A',
    'ROR_ZEROPAGE_0x66',
    'ROR_ZEROPAGE_X_0x76',
    'ROR_ABSOLUTE_0x6E',
    'ROR_ABSOLUTE_X_0x7E',
    'register_ror_instructions',
]
