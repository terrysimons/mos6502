#!/usr/bin/env python3
"""SHA (AHX, AXA) - Store A AND X AND (high byte + 1).

ILLEGAL INSTRUCTION - UNSTABLE - NMOS 6502 only
On 65C02 (CMOS), this opcode acts as a NOP.

SHA stores the result of A AND X AND (high byte of address + 1) to memory.

The behavior is unstable and varies between chips. The value stored may be
affected by page boundary crossing in unpredictable ways.

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# SHA (AHX, AXA) - Unstable store instruction
# Operation: Memory = A & X & (high_byte + 1)
SHA_INDIRECT_INDEXED_Y_0x93 = InstructionOpcode(
    0x93,
    "mos6502.instructions.illegal._sha",
    "sha_indirect_indexed_y_0x93"
)

SHA_ABSOLUTE_Y_0x9F = InstructionOpcode(
    0x9F,
    "mos6502.instructions.illegal._sha",
    "sha_absolute_y_0x9f"
)


def add_sha_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SHA instructions to the InstructionSet enum dynamically."""
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

    for opcode, name in [
        (SHA_INDIRECT_INDEXED_Y_0x93, "SHA_INDIRECT_INDEXED_Y_0x93"),
        (SHA_ABSOLUTE_Y_0x9F, "SHA_ABSOLUTE_Y_0x9F"),
    ]:
        member = PseudoEnumMember(opcode, name)
        instruction_set_class._value2member_map_[opcode] = member
        setattr(instruction_set_class, name, opcode)


def register_sha_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SHA illegal instructions in the InstructionSet map."""
    add_sha_to_instruction_set_enum(instruction_set_class)

    # SHA doesn't affect any flags
    sha_flags: Byte = Byte()

    instruction_map[SHA_INDIRECT_INDEXED_Y_0x93] = {
        "addressing": "(indirect),Y",
        "assembler": "SHA ({oper}),Y",
        "opc": SHA_INDIRECT_INDEXED_Y_0x93,
        "bytes": "2",
        "cycles": "6",
        "flags": sha_flags,
    }

    instruction_map[SHA_ABSOLUTE_Y_0x9F] = {
        "addressing": "absolute,Y",
        "assembler": "SHA {oper},Y",
        "opc": SHA_ABSOLUTE_Y_0x9F,
        "bytes": "3",
        "cycles": "5",
        "flags": sha_flags,
    }


__all__ = [
    "SHA_INDIRECT_INDEXED_Y_0x93",
    "SHA_ABSOLUTE_Y_0x9F",
    "register_sha_instructions",
]
