#!/usr/bin/env python3
"""ANE (XAA) - AND X with Accumulator and Immediate.

ILLEGAL INSTRUCTION - HIGHLY UNSTABLE - NMOS 6502 only
On 65C02 (CMOS), this opcode acts as a NOP.

ANE is one of the most unstable illegal opcodes. It performs:
  A = (A | CONST) & X & immediate

Where CONST is an unpredictable "magic" value that varies between chips,
manufacturing batches, temperature, and even within the same chip over time.

Common CONST values observed:
  - 0xFF (most common, used by most emulators)
  - 0xEE (some 6502C chips)
  - 0xEF
  - 0x00

WARNING: This instruction's behavior is undefined on real hardware.
Do not use in production code targeting real 6502 hardware.

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes#Highly_unstable_opcodes
  - https://csdb.dk/release/?id=198357 (Visual 6502 analysis)
"""

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# ANE (XAA) - Highly Unstable
# Operation: A = (A | CONST) & X & immediate
# NMOS: Performs unstable AND operation
# CMOS: Acts as NOP
ANE_IMMEDIATE_0x8B = InstructionOpcode(
    0x8B,
    "mos6502.instructions.illegal._ane",
    "ane_immediate_0x8b"
)


def add_ane_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ANE instruction to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(ANE_IMMEDIATE_0x8B, "ANE_IMMEDIATE_0x8B")
    instruction_set_class._value2member_map_[ANE_IMMEDIATE_0x8B] = member
    setattr(instruction_set_class, "ANE_IMMEDIATE_0x8B", ANE_IMMEDIATE_0x8B)


def register_ane_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ANE illegal instruction in the InstructionSet map."""
    add_ane_to_instruction_set_enum(instruction_set_class)

    ane_can_modify_flags: Byte = Byte()
    ane_can_modify_flags[0] = 1  # N
    ane_can_modify_flags[1] = 1  # Z

    instruction_map[ANE_IMMEDIATE_0x8B] = {
        "addressing": "immediate",
        "assembler": "ANE #{oper}",
        "opc": ANE_IMMEDIATE_0x8B,
        "bytes": "2",
        "cycles": "2",
        "flags": ane_can_modify_flags,
    }


__all__ = ["ANE_IMMEDIATE_0x8B", "register_ane_instructions"]
