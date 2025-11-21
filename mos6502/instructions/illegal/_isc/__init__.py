#!/usr/bin/env python3
"""ISC (Increment and Subtract with Carry) illegal instruction.

ILLEGAL INSTRUCTION - NMOS 6502 only
On 65C02 (CMOS), these opcodes act as NOPs.

Also known as ISB (Increment and Subtract with Borrow).

References:
  - https://masswerk.at/6502/6502_instruction_set.html#ISC
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/Programming_with_unofficial_opcodes
"""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# ISC - Increment Memory and Subtract from Accumulator with Carry
#
# Operation: M = M + 1, A = A - M - (1 - C)
#
# This illegal instruction increments a memory location, then subtracts the
# result from the accumulator using the carry flag (borrow). It is functionally
# equivalent to:
#   INC {operand}
#   SBC {operand}
# but executes in a single instruction.
#
# NMOS (6502/6502A/6502C): Increments memory and subtracts from A with carry
# CMOS (65C02): Acts as NOP - no registers, flags, or memory modified
#
# Stability: STABLE
#
# ---
# Flags Affected:
# N\tZ\tC\tI\tD\tV
# ✓\t✓\t✓\t-\t-\t✓
#
# N: Set if bit 7 of result is set
# Z: Set if result is zero
# C: Set if no borrow (A >= M)
# V: Set on signed overflow
#
# ---
# Addressing Modes:
# addressing       assembler    opc  bytes  cycles
# zeropage         ISC oper     E7   2      5
# zeropage,X       ISC oper,X   F7   2      6
# (indirect,X)     ISC (oper,X) E3   2      8
# (indirect),Y     ISC (oper),Y F3   2      8
# absolute         ISC oper     EF   3      6
# absolute,X       ISC oper,X   FF   3      7
# absolute,Y       ISC oper,Y   FB   3      7
#
# ---
# Usage:
# ISC is useful for incrementing a value and then subtracting it from the
# accumulator in a single instruction, commonly used in loop calculations.

ISC_ZEROPAGE_0xE7 = InstructionOpcode(
    0xE7,
    "mos6502.instructions.illegal._isc",
    "isc_zeropage_0xe7"
)

ISC_ZEROPAGE_X_0xF7 = InstructionOpcode(
    0xF7,
    "mos6502.instructions.illegal._isc",
    "isc_zeropage_x_0xf7"
)

ISC_INDEXED_INDIRECT_X_0xE3 = InstructionOpcode(
    0xE3,
    "mos6502.instructions.illegal._isc",
    "isc_indexed_indirect_x_0xe3"
)

ISC_INDIRECT_INDEXED_Y_0xF3 = InstructionOpcode(
    0xF3,
    "mos6502.instructions.illegal._isc",
    "isc_indirect_indexed_y_0xf3"
)

ISC_ABSOLUTE_0xEF = InstructionOpcode(
    0xEF,
    "mos6502.instructions.illegal._isc",
    "isc_absolute_0xef"
)

ISC_ABSOLUTE_X_0xFF = InstructionOpcode(
    0xFF,
    "mos6502.instructions.illegal._isc",
    "isc_absolute_x_0xff"
)

ISC_ABSOLUTE_Y_0xFB = InstructionOpcode(
    0xFB,
    "mos6502.instructions.illegal._isc",
    "isc_absolute_y_0xfb"
)


def add_isc_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ISC instructions to the InstructionSet enum dynamically."""
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

    # Add each ISC variant to the enum
    for opcode_name, opcode_value in [
        ("ISC_ZEROPAGE_0xE7", ISC_ZEROPAGE_0xE7),
        ("ISC_ZEROPAGE_X_0xF7", ISC_ZEROPAGE_X_0xF7),
        ("ISC_INDEXED_INDIRECT_X_0xE3", ISC_INDEXED_INDIRECT_X_0xE3),
        ("ISC_INDIRECT_INDEXED_Y_0xF3", ISC_INDIRECT_INDEXED_Y_0xF3),
        ("ISC_ABSOLUTE_0xEF", ISC_ABSOLUTE_0xEF),
        ("ISC_ABSOLUTE_X_0xFF", ISC_ABSOLUTE_X_0xFF),
        ("ISC_ABSOLUTE_Y_0xFB", ISC_ABSOLUTE_Y_0xFB),
    ]:
        member = PseudoEnumMember(opcode_value, opcode_name)
        instruction_set_class._value2member_map_[opcode_value] = member
        setattr(instruction_set_class, opcode_name, opcode_value)


def register_isc_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ISC illegal instructions in the InstructionSet map."""
    # Add to enum
    add_isc_to_instruction_set_enum(instruction_set_class)

    # ISC modifies N, Z, C, V flags (same as SBC)
    isc_can_modify_flags: Byte = Byte()
    isc_can_modify_flags[0] = 1  # N
    isc_can_modify_flags[1] = 1  # Z
    isc_can_modify_flags[6] = 1  # V
    isc_can_modify_flags[7] = 1  # C

    # Add to map
    instruction_map[ISC_ZEROPAGE_0xE7] = {
        "addressing": "zeropage",
        "assembler": "ISC {oper}",
        "opc": ISC_ZEROPAGE_0xE7,
        "bytes": "2",
        "cycles": "5",
        "flags": isc_can_modify_flags,
    }

    instruction_map[ISC_ZEROPAGE_X_0xF7] = {
        "addressing": "zeropage,X",
        "assembler": "ISC {oper},X",
        "opc": ISC_ZEROPAGE_X_0xF7,
        "bytes": "2",
        "cycles": "6",
        "flags": isc_can_modify_flags,
    }

    instruction_map[ISC_INDEXED_INDIRECT_X_0xE3] = {
        "addressing": "(indirect,X)",
        "assembler": "ISC ({oper},X)",
        "opc": ISC_INDEXED_INDIRECT_X_0xE3,
        "bytes": "2",
        "cycles": "8",
        "flags": isc_can_modify_flags,
    }

    instruction_map[ISC_INDIRECT_INDEXED_Y_0xF3] = {
        "addressing": "(indirect),Y",
        "assembler": "ISC ({oper}),Y",
        "opc": ISC_INDIRECT_INDEXED_Y_0xF3,
        "bytes": "2",
        "cycles": "8",
        "flags": isc_can_modify_flags,
    }

    instruction_map[ISC_ABSOLUTE_0xEF] = {
        "addressing": "absolute",
        "assembler": "ISC {oper}",
        "opc": ISC_ABSOLUTE_0xEF,
        "bytes": "3",
        "cycles": "6",
        "flags": isc_can_modify_flags,
    }

    instruction_map[ISC_ABSOLUTE_X_0xFF] = {
        "addressing": "absolute,X",
        "assembler": "ISC {oper},X",
        "opc": ISC_ABSOLUTE_X_0xFF,
        "bytes": "3",
        "cycles": "7",
        "flags": isc_can_modify_flags,
    }

    instruction_map[ISC_ABSOLUTE_Y_0xFB] = {
        "addressing": "absolute,Y",
        "assembler": "ISC {oper},Y",
        "opc": ISC_ABSOLUTE_Y_0xFB,
        "bytes": "3",
        "cycles": "7",
        "flags": isc_can_modify_flags,
    }


__all__ = [
    "ISC_ZEROPAGE_0xE7",
    "ISC_ZEROPAGE_X_0xF7",
    "ISC_INDEXED_INDIRECT_X_0xE3",
    "ISC_INDIRECT_INDEXED_Y_0xF3",
    "ISC_ABSOLUTE_0xEF",
    "ISC_ABSOLUTE_X_0xFF",
    "ISC_ABSOLUTE_Y_0xFB",
    "register_isc_instructions",
]
