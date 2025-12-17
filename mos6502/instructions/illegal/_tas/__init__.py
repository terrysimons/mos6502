#!/usr/bin/env python3
"""TAS (XAS, SHS) - Transfer A AND X to Stack and Store.

ILLEGAL INSTRUCTION - UNSTABLE - NMOS 6502 only
On 65C02 (CMOS), this opcode acts as a NOP.

TAS performs two operations:
1. S = A & X (store A AND X into stack pointer)
2. Memory = A & X & (high byte + 1)

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# TAS (XAS, SHS) - Unstable transfer and store instruction
# Operation: S = A & X; Memory = A & X & (high_byte + 1)
TAS_ABSOLUTE_Y_0x9B = InstructionOpcode(
    0x9B,
    "mos6502.instructions.illegal._tas",
    "tas_absolute_y_0x9b"
)


def add_tas_to_instruction_set_enum(instruction_set_class) -> None:
    """Add TAS instruction to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(TAS_ABSOLUTE_Y_0x9B, "TAS_ABSOLUTE_Y_0x9B")
    instruction_set_class._value2member_map_[TAS_ABSOLUTE_Y_0x9B] = member
    setattr(instruction_set_class, "TAS_ABSOLUTE_Y_0x9B", TAS_ABSOLUTE_Y_0x9B)


def register_tas_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register TAS illegal instruction in the InstructionSet map."""
    add_tas_to_instruction_set_enum(instruction_set_class)

    # TAS doesn't affect any flags
    tas_flags: Byte = Byte()

    instruction_map[TAS_ABSOLUTE_Y_0x9B] = {
        "addressing": "absolute,Y",
        "assembler": "TAS {oper},Y",
        "opc": TAS_ABSOLUTE_Y_0x9B,
        "bytes": "3",
        "cycles": "5",
        "flags": tas_flags,
    }


__all__ = ["TAS_ABSOLUTE_Y_0x9B", "register_tas_instructions"]
