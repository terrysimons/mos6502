#!/usr/bin/env python3
"""SBX (Subtract from X) illegal instruction.

ILLEGAL INSTRUCTION - NMOS 6502 only
On 65C02 (CMOS), this opcode acts as a NOP.

SBX performs (A & X) - immediate and stores the result in X. It sets the
carry flag as if a compare was performed. Also known as AXS or SAX (not to
be confused with the SAX store instruction).

References:
  - https://masswerk.at/6502/6502_instruction_set.html#SBX
  - http://www.oxyron.de/html/opcodes02.html
"""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# SBX - Subtract from X
# Operation: X = (A & X) - immediate
# NMOS: Computes (A & X) - immediate, stores in X
# CMOS: Acts as NOP

SBX_IMMEDIATE_0xCB = InstructionOpcode(0xCB, "mos6502.instructions.illegal._sbx", "sbx_immediate_0xcb")


def add_sbx_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SBX instruction to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(SBX_IMMEDIATE_0xCB, 'SBX_IMMEDIATE_0xCB')
    instruction_set_class._value2member_map_[SBX_IMMEDIATE_0xCB] = member
    setattr(instruction_set_class, 'SBX_IMMEDIATE_0xCB', SBX_IMMEDIATE_0xCB)


def register_sbx_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SBX illegal instruction in the InstructionSet map."""
    add_sbx_to_instruction_set_enum(instruction_set_class)

    sbx_can_modify_flags: Byte = Byte()
    sbx_can_modify_flags[0] = 1  # N
    sbx_can_modify_flags[1] = 1  # Z
    sbx_can_modify_flags[7] = 1  # C

    instruction_map[SBX_IMMEDIATE_0xCB] = {"addressing": "immediate", "assembler": "SBX #{oper}", "opc": SBX_IMMEDIATE_0xCB, "bytes": "2", "cycles": "2", "flags": sbx_can_modify_flags}


__all__ = ['SBX_IMMEDIATE_0xCB', 'register_sbx_instructions']
