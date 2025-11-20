#!/usr/bin/env python3
"""BIT (Test Bits in Memory with Accumulator) instruction."""
from mos6502 import flags
from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# https://masswerk.at/6502/6502_instruction_set.html#BIT
#
# Test Bits in Memory with Accumulator
#
# bits 7 and 6 of operand are transfered to bit 7 and 6 of SR (N,V);
# the zero-flag is set to the result of operand AND accumulator.
#
# A AND M, M7 -> N, M6 -> V
# N	Z	C	I	D	V
# M7	+	-	-	-	M6
# addressing	assembler	opc	bytes	cycles
# zeropage	BIT oper	24	2	3
# absolute	BIT oper	2C	3	4
BIT_ZEROPAGE_0x24 = InstructionOpcode(
    0x24,
    "mos6502.instructions._bit",
    "bit_zeropage_0x24"
)

BIT_ABSOLUTE_0x2C = InstructionOpcode(
    0x2C,
    "mos6502.instructions._bit",
    "bit_absolute_0x2c"
)


def add_bit_to_instruction_set_enum(instruction_set_class) -> None:
    """Add BIT instructions to the InstructionSet enum dynamically."""
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
        (BIT_ZEROPAGE_0x24, 'BIT_ZEROPAGE_0x24'),
        (BIT_ABSOLUTE_0x2C, 'BIT_ABSOLUTE_0x2C'),
    ]:
        member = PseudoEnumMember(value, name)
        instruction_set_class._value2member_map_[value] = member
        setattr(instruction_set_class, name, value)


def register_bit_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register BIT instructions in the InstructionSet."""
    add_bit_to_instruction_set_enum(instruction_set_class)

    bit_zeropage_can_modify_flags: Byte = Byte()
    bit_zeropage_can_modify_flags[flags.N] = True
    bit_zeropage_can_modify_flags[flags.Z] = True
    bit_zeropage_can_modify_flags[flags.V] = True
    instruction_map[BIT_ZEROPAGE_0x24] = {
        "addressing": "zeropage",
        "assembler": "BIT {oper}",
        "opc": BIT_ZEROPAGE_0x24,
        "bytes": "2",
        "cycles": "3",
        "flags": bit_zeropage_can_modify_flags,
    }

    bit_absolute_can_modify_flags: Byte = Byte()
    bit_absolute_can_modify_flags[flags.N] = True
    bit_absolute_can_modify_flags[flags.Z] = True
    bit_absolute_can_modify_flags[flags.V] = True
    instruction_map[BIT_ABSOLUTE_0x2C] = {
        "addressing": "absolute",
        "assembler": "BIT {oper}",
        "opc": BIT_ABSOLUTE_0x2C,
        "bytes": "3",
        "cycles": "4",
        "flags": bit_absolute_can_modify_flags,
    }


__all__ = [
    'BIT_ZEROPAGE_0x24',
    'BIT_ABSOLUTE_0x2C',
    'register_bit_instructions',
]
