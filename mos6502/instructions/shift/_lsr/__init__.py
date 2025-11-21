#!/usr/bin/env python3
"""LSR (Logical Shift Right) instruction."""
from mos6502.instructions import InstructionOpcode

# https://masswerk.at/6502/6502_instruction_set.html#LSR
# Logical Shift Right
#
# Shift One Bit Right (Memory or Accumulator)
# 0 -> [76543210] -> C
#
# N	Z	C	I	D	V
# 0	+	+	-	-	-
# addressing	assembler	opc	bytes	cycles
# accumulator	LSR A	4A	1	2
# zeropage	LSR oper	46	2	5
# zeropage,X	LSR oper,X	56	2	6
# absolute	LSR oper	4E	3	6
# absolute,X	LSR oper,X	5E	3	7

LSR_ACCUMULATOR_0x4A = InstructionOpcode(
    0x4A,
    "mos6502.instructions.shift._lsr",
    "lsr_accumulator_0x4a"
)

LSR_ZEROPAGE_0x46 = InstructionOpcode(
    0x46,
    "mos6502.instructions.shift._lsr",
    "lsr_zeropage_0x46"
)

LSR_ZEROPAGE_X_0x56 = InstructionOpcode(
    0x56,
    "mos6502.instructions.shift._lsr",
    "lsr_zeropage_x_0x56"
)

LSR_ABSOLUTE_0x4E = InstructionOpcode(
    0x4E,
    "mos6502.instructions.shift._lsr",
    "lsr_absolute_0x4e"
)

LSR_ABSOLUTE_X_0x5E = InstructionOpcode(
    0x5E,
    "mos6502.instructions.shift._lsr",
    "lsr_absolute_x_0x5e"
)


def add_lsr_to_instruction_set_enum(instruction_set_class) -> None:
    """Add LSR instructions to the InstructionSet enum dynamically."""
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
        (LSR_ACCUMULATOR_0x4A, "LSR_ACCUMULATOR_0x4A"),
        (LSR_ZEROPAGE_0x46, "LSR_ZEROPAGE_0x46"),
        (LSR_ZEROPAGE_X_0x56, "LSR_ZEROPAGE_X_0x56"),
        (LSR_ABSOLUTE_0x4E, "LSR_ABSOLUTE_0x4E"),
        (LSR_ABSOLUTE_X_0x5E, "LSR_ABSOLUTE_X_0x5E"),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_lsr_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register LSR instructions in the InstructionSet."""
    add_lsr_to_instruction_set_enum(instruction_set_class)

    from mos6502.memory import Byte
    from mos6502 import flags
    lsr_can_modify_flags: Byte = Byte()
    lsr_can_modify_flags[flags.N] = 1
    lsr_can_modify_flags[flags.Z] = 1
    lsr_can_modify_flags[flags.C] = 1

    instruction_map[LSR_ACCUMULATOR_0x4A] = {
        "addressing": "accumulator",
        "assembler": "LSR A",
        "opc": LSR_ACCUMULATOR_0x4A,
        "bytes": "1",
        "cycles": "2",
        "flags": lsr_can_modify_flags,
    }

    instruction_map[LSR_ZEROPAGE_0x46] = {
        "addressing": "zeropage",
        "assembler": "LSR {oper}",
        "opc": LSR_ZEROPAGE_0x46,
        "bytes": "2",
        "cycles": "5",
        "flags": lsr_can_modify_flags,
    }

    instruction_map[LSR_ZEROPAGE_X_0x56] = {
        "addressing": "zeropage,X",
        "assembler": "LSR {oper},X",
        "opc": LSR_ZEROPAGE_X_0x56,
        "bytes": "2",
        "cycles": "6",
        "flags": lsr_can_modify_flags,
    }

    instruction_map[LSR_ABSOLUTE_0x4E] = {
        "addressing": "absolute",
        "assembler": "LSR {oper}",
        "opc": LSR_ABSOLUTE_0x4E,
        "bytes": "3",
        "cycles": "6",
        "flags": lsr_can_modify_flags,
    }

    instruction_map[LSR_ABSOLUTE_X_0x5E] = {
        "addressing": "absolute,X",
        "assembler": "LSR {oper},X",
        "opc": LSR_ABSOLUTE_X_0x5E,
        "bytes": "3",
        "cycles": "7",
        "flags": lsr_can_modify_flags,
    }


__all__ = [
    "LSR_ACCUMULATOR_0x4A",
    "LSR_ZEROPAGE_0x46",
    "LSR_ZEROPAGE_X_0x56",
    "LSR_ABSOLUTE_0x4E",
    "LSR_ABSOLUTE_X_0x5E",
    "register_lsr_instructions",
]
