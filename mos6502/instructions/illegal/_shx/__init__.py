#!/usr/bin/env python3
"""SHX (SXA, XAS) - Store X AND (high byte + 1).

ILLEGAL INSTRUCTION - UNSTABLE - NMOS 6502 only
On 65C02 (CMOS), this opcode acts as a NOP.

SHX stores the result of X AND (high byte of address + 1) to memory.

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# SHX (SXA, XAS) - Unstable store instruction
# Operation: Memory = X & (high_byte + 1)
SHX_ABSOLUTE_Y_0x9E = InstructionOpcode(
    0x9E,
    "mos6502.instructions.illegal._shx",
    "shx_absolute_y_0x9e"
)


def add_shx_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SHX instruction to the InstructionSet enum dynamically."""
    class PseudoEnumMember:
        """MicroPython-compatible pseudo-enum member."""
        __slots__ = ('_value_', '_name')

        def __init__(self, value, name):
            self._value_ = int(value)
            self._name = name

        @property
        def name(self):
            return self._name

        @property
        def value(self):
            return self._value_

        def __int__(self):
            return self._value_

        def __eq__(self, other):
            if isinstance(other, int):
                return self._value_ == other
            return NotImplemented

        def __hash__(self):
            return hash(self._value_)

    member = PseudoEnumMember(SHX_ABSOLUTE_Y_0x9E, "SHX_ABSOLUTE_Y_0x9E")
    instruction_set_class._value2member_map_[SHX_ABSOLUTE_Y_0x9E] = member
    setattr(instruction_set_class, "SHX_ABSOLUTE_Y_0x9E", SHX_ABSOLUTE_Y_0x9E)


def register_shx_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SHX illegal instruction in the InstructionSet map."""
    add_shx_to_instruction_set_enum(instruction_set_class)

    # SHX doesn't affect any flags
    shx_flags: Byte = Byte()

    instruction_map[SHX_ABSOLUTE_Y_0x9E] = {
        "addressing": "absolute,Y",
        "assembler": "SHX {oper},Y",
        "opc": SHX_ABSOLUTE_Y_0x9E,
        "bytes": "3",
        "cycles": "5",
        "flags": shx_flags,
    }


__all__ = ["SHX_ABSOLUTE_Y_0x9E", "register_shx_instructions"]
