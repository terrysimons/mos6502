#!/usr/bin/env python3
"""ARR (AND then Rotate Right) illegal instruction.

ILLEGAL INSTRUCTION - NMOS 6502 only
On 65C02 (CMOS), this opcode acts as a NOP.

ARR performs an AND operation with an immediate value, then rotates the result
right through the carry flag. It sets flags in a special way different from
normal ROR.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#ARR
  - http://www.oxyron.de/html/opcodes02.html
"""

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# ARR - AND then Rotate Right
# Operation: A = (A & immediate) ROR, with special flag handling
# NMOS: ANDs immediate value with A, then rotates right with special flags
# CMOS: Acts as NOP

ARR_IMMEDIATE_0x6B = InstructionOpcode(0x6B, "mos6502.instructions.illegal._arr", "arr_immediate_0x6b")


def add_arr_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ARR instruction to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(ARR_IMMEDIATE_0x6B, "ARR_IMMEDIATE_0x6B")
    instruction_set_class._value2member_map_[ARR_IMMEDIATE_0x6B] = member
    setattr(instruction_set_class, "ARR_IMMEDIATE_0x6B", ARR_IMMEDIATE_0x6B)


def register_arr_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ARR illegal instruction in the InstructionSet map."""
    add_arr_to_instruction_set_enum(instruction_set_class)

    arr_can_modify_flags: Byte = Byte()
    arr_can_modify_flags[0] = 1  # N
    arr_can_modify_flags[1] = 1  # Z
    arr_can_modify_flags[6] = 1  # V
    arr_can_modify_flags[7] = 1  # C

    instruction_map[ARR_IMMEDIATE_0x6B] = {"addressing": "immediate", "assembler": "ARR #{oper}", "opc": ARR_IMMEDIATE_0x6B, "bytes": "2", "cycles": "2", "flags": arr_can_modify_flags}


__all__ = ["ARR_IMMEDIATE_0x6B", "register_arr_instructions"]
