#!/usr/bin/env python3
"""SHY (SYA, SAY) - Store Y AND (high byte + 1).

ILLEGAL INSTRUCTION - UNSTABLE - NMOS 6502 only
On 65C02 (CMOS), this opcode acts as a NOP.

SHY stores the result of Y AND (high byte of address + 1) to memory.

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# SHY (SYA, SAY) - Unstable store instruction
# Operation: Memory = Y & (high_byte + 1)
SHY_ABSOLUTE_X_0x9C = InstructionOpcode(
    0x9C,
    "mos6502.instructions.illegal._shy",
    "shy_absolute_x_0x9c"
)


def add_shy_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SHY instruction to the InstructionSet enum dynamically."""
    class PseudoEnumMember(int):
        def __new__(cls, value, name) -> "InstructionSet":
            obj = int.__new__(cls, value)
            obj._name = name
            obj._value_ = value
            return obj

        @property
        def name(self) -> str:
            return self._name

        @property
        def value(self) -> int:
            return self._value_

    member = PseudoEnumMember(SHY_ABSOLUTE_X_0x9C, "SHY_ABSOLUTE_X_0x9C")
    instruction_set_class._value2member_map_[SHY_ABSOLUTE_X_0x9C] = member
    setattr(instruction_set_class, "SHY_ABSOLUTE_X_0x9C", SHY_ABSOLUTE_X_0x9C)


def register_shy_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SHY illegal instruction in the InstructionSet map."""
    add_shy_to_instruction_set_enum(instruction_set_class)

    # SHY doesn't affect any flags
    shy_flags: Byte = Byte()

    instruction_map[SHY_ABSOLUTE_X_0x9C] = {
        "addressing": "absolute,X",
        "assembler": "SHY {oper},X",
        "opc": SHY_ABSOLUTE_X_0x9C,
        "bytes": "3",
        "cycles": "5",
        "flags": shy_flags,
    }


__all__ = ["SHY_ABSOLUTE_X_0x9C", "register_shy_instructions"]
