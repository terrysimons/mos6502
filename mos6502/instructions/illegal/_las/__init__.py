#!/usr/bin/env python3
"""LAS (Load A, X, and S) illegal instruction.

ILLEGAL INSTRUCTION - NMOS 6502 only (UNSTABLE)
On 65C02 (CMOS), this opcode acts as a NOP.

LAS performs M & S and stores the result in A, X, and S.
This is an unstable instruction and may behave unpredictably.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#LAS
  - http://www.oxyron.de/html/opcodes02.html
"""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# LAS - Load A, X, and S
# Operation: A, X, S = M & S
# NMOS: Loads (M & S) into A, X, and S (UNSTABLE)
# CMOS: Acts as NOP

LAS_ABSOLUTE_Y_0xBB = InstructionOpcode(0xBB, "mos6502.instructions.illegal._las", "las_absolute_y_0xbb")


def add_las_to_instruction_set_enum(instruction_set_class) -> None:
    """Add LAS instruction to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(LAS_ABSOLUTE_Y_0xBB, 'LAS_ABSOLUTE_Y_0xBB')
    instruction_set_class._value2member_map_[LAS_ABSOLUTE_Y_0xBB] = member
    setattr(instruction_set_class, 'LAS_ABSOLUTE_Y_0xBB', LAS_ABSOLUTE_Y_0xBB)


def register_las_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register LAS illegal instruction in the InstructionSet map."""
    add_las_to_instruction_set_enum(instruction_set_class)

    las_can_modify_flags: Byte = Byte()
    las_can_modify_flags[0] = 1  # N
    las_can_modify_flags[1] = 1  # Z

    instruction_map[LAS_ABSOLUTE_Y_0xBB] = {"addressing": "absolute,Y", "assembler": "LAS {oper},Y", "opc": LAS_ABSOLUTE_Y_0xBB, "bytes": "3", "cycles": "4*", "flags": las_can_modify_flags}


__all__ = ['LAS_ABSOLUTE_Y_0xBB', 'register_las_instructions']
