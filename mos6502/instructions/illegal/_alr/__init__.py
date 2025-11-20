#!/usr/bin/env python3
"""ALR (AND then Logical Shift Right) illegal instruction.

ILLEGAL INSTRUCTION - NMOS 6502 only
On 65C02 (CMOS), this opcode acts as a NOP.

ALR performs an AND operation with an immediate value, then shifts the result
right by one bit. Also known as ASR in some references.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#ALR
  - http://www.oxyron.de/html/opcodes02.html
"""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# ALR - AND then Logical Shift Right
# Operation: A = (A & immediate) >> 1
# NMOS: ANDs immediate value with A, then shifts right
# CMOS: Acts as NOP

ALR_IMMEDIATE_0x4B = InstructionOpcode(0x4B, "mos6502.instructions.illegal._alr", "alr_immediate_0x4b")


def add_alr_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ALR instruction to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(ALR_IMMEDIATE_0x4B, 'ALR_IMMEDIATE_0x4B')
    instruction_set_class._value2member_map_[ALR_IMMEDIATE_0x4B] = member
    setattr(instruction_set_class, 'ALR_IMMEDIATE_0x4B', ALR_IMMEDIATE_0x4B)


def register_alr_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ALR illegal instruction in the InstructionSet map."""
    add_alr_to_instruction_set_enum(instruction_set_class)

    alr_can_modify_flags: Byte = Byte()
    alr_can_modify_flags[0] = 1  # N
    alr_can_modify_flags[1] = 1  # Z
    alr_can_modify_flags[7] = 1  # C

    instruction_map[ALR_IMMEDIATE_0x4B] = {"addressing": "immediate", "assembler": "ALR #{oper}", "opc": ALR_IMMEDIATE_0x4B, "bytes": "2", "cycles": "2", "flags": alr_can_modify_flags}


__all__ = ['ALR_IMMEDIATE_0x4B', 'register_alr_instructions']
