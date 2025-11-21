#!/usr/bin/env python3
"""SLO (Shift Left and OR with Accumulator) illegal instruction.

ILLEGAL INSTRUCTION - NMOS 6502 only
On 65C02 (CMOS), these opcodes act as NOPs.

Also known as ASO (Arithmetic Shift Left and OR).

References:
  - https://masswerk.at/6502/6502_instruction_set.html#SLO
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/Programming_with_unofficial_opcodes
"""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# SLO - Shift Left and OR with Accumulator
#
# Operation: M = M << 1, A = A | M
#
# This illegal instruction shifts a memory location left by one bit, then
# performs a bitwise OR with the accumulator. It is functionally equivalent to:
#   ASL {operand}
#   ORA {operand}
# but executes in a single instruction.
#
# NMOS (6502/6502A/6502C): Shifts memory left and ORs with A
# CMOS (65C02): Acts as NOP - no registers, flags, or memory modified
#
# Stability: STABLE
#
# ---
# Flags Affected:
# N\tZ\tC\tI\tD\tV
# ✓\t✓\t✓\t-\t-\t-
#
# N: Set if bit 7 of result is set
# Z: Set if result is zero
# C: Set to the bit shifted out (bit 7 of original value)
#
# ---
# Addressing Modes:
# addressing       assembler    opc  bytes  cycles
# zeropage         SLO oper     07   2      5
# zeropage,X       SLO oper,X   17   2      6
# (indirect,X)     SLO (oper,X) 03   2      8
# (indirect),Y     SLO (oper),Y 13   2      8
# absolute         SLO oper     0F   3      6
# absolute,X       SLO oper,X   1F   3      7
# absolute,Y       SLO oper,Y   1B   3      7
#
# ---
# Usage:
# SLO is useful for quickly doubling a value and combining it with the
# accumulator using bitwise OR.

SLO_ZEROPAGE_0x07 = InstructionOpcode(
    0x07,
    "mos6502.instructions.illegal._slo",
    "slo_zeropage_0x07"
)

SLO_ZEROPAGE_X_0x17 = InstructionOpcode(
    0x17,
    "mos6502.instructions.illegal._slo",
    "slo_zeropage_x_0x17"
)

SLO_INDEXED_INDIRECT_X_0x03 = InstructionOpcode(
    0x03,
    "mos6502.instructions.illegal._slo",
    "slo_indexed_indirect_x_0x03"
)

SLO_INDIRECT_INDEXED_Y_0x13 = InstructionOpcode(
    0x13,
    "mos6502.instructions.illegal._slo",
    "slo_indirect_indexed_y_0x13"
)

SLO_ABSOLUTE_0x0F = InstructionOpcode(
    0x0F,
    "mos6502.instructions.illegal._slo",
    "slo_absolute_0x0f"
)

SLO_ABSOLUTE_X_0x1F = InstructionOpcode(
    0x1F,
    "mos6502.instructions.illegal._slo",
    "slo_absolute_x_0x1f"
)

SLO_ABSOLUTE_Y_0x1B = InstructionOpcode(
    0x1B,
    "mos6502.instructions.illegal._slo",
    "slo_absolute_y_0x1b"
)


def add_slo_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SLO instructions to the InstructionSet enum dynamically."""
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

    # Add each SLO variant to the enum
    for opcode_name, opcode_value in [
        ("SLO_ZEROPAGE_0x07", SLO_ZEROPAGE_0x07),
        ("SLO_ZEROPAGE_X_0x17", SLO_ZEROPAGE_X_0x17),
        ("SLO_INDEXED_INDIRECT_X_0x03", SLO_INDEXED_INDIRECT_X_0x03),
        ("SLO_INDIRECT_INDEXED_Y_0x13", SLO_INDIRECT_INDEXED_Y_0x13),
        ("SLO_ABSOLUTE_0x0F", SLO_ABSOLUTE_0x0F),
        ("SLO_ABSOLUTE_X_0x1F", SLO_ABSOLUTE_X_0x1F),
        ("SLO_ABSOLUTE_Y_0x1B", SLO_ABSOLUTE_Y_0x1B),
    ]:
        member = PseudoEnumMember(opcode_value, opcode_name)
        instruction_set_class._value2member_map_[opcode_value] = member
        setattr(instruction_set_class, opcode_name, opcode_value)


def register_slo_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SLO illegal instructions in the InstructionSet map."""
    # Add to enum
    add_slo_to_instruction_set_enum(instruction_set_class)

    # SLO modifies N, Z, C flags
    slo_can_modify_flags: Byte = Byte()
    slo_can_modify_flags[0] = 1  # N
    slo_can_modify_flags[1] = 1  # Z
    slo_can_modify_flags[7] = 1  # C

    # Add to map
    instruction_map[SLO_ZEROPAGE_0x07] = {
        "addressing": "zeropage",
        "assembler": "SLO {oper}",
        "opc": SLO_ZEROPAGE_0x07,
        "bytes": "2",
        "cycles": "5",
        "flags": slo_can_modify_flags,
    }

    instruction_map[SLO_ZEROPAGE_X_0x17] = {
        "addressing": "zeropage,X",
        "assembler": "SLO {oper},X",
        "opc": SLO_ZEROPAGE_X_0x17,
        "bytes": "2",
        "cycles": "6",
        "flags": slo_can_modify_flags,
    }

    instruction_map[SLO_INDEXED_INDIRECT_X_0x03] = {
        "addressing": "(indirect,X)",
        "assembler": "SLO ({oper},X)",
        "opc": SLO_INDEXED_INDIRECT_X_0x03,
        "bytes": "2",
        "cycles": "8",
        "flags": slo_can_modify_flags,
    }

    instruction_map[SLO_INDIRECT_INDEXED_Y_0x13] = {
        "addressing": "(indirect),Y",
        "assembler": "SLO ({oper}),Y",
        "opc": SLO_INDIRECT_INDEXED_Y_0x13,
        "bytes": "2",
        "cycles": "8",
        "flags": slo_can_modify_flags,
    }

    instruction_map[SLO_ABSOLUTE_0x0F] = {
        "addressing": "absolute",
        "assembler": "SLO {oper}",
        "opc": SLO_ABSOLUTE_0x0F,
        "bytes": "3",
        "cycles": "6",
        "flags": slo_can_modify_flags,
    }

    instruction_map[SLO_ABSOLUTE_X_0x1F] = {
        "addressing": "absolute,X",
        "assembler": "SLO {oper},X",
        "opc": SLO_ABSOLUTE_X_0x1F,
        "bytes": "3",
        "cycles": "7",
        "flags": slo_can_modify_flags,
    }

    instruction_map[SLO_ABSOLUTE_Y_0x1B] = {
        "addressing": "absolute,Y",
        "assembler": "SLO {oper},Y",
        "opc": SLO_ABSOLUTE_Y_0x1B,
        "bytes": "3",
        "cycles": "7",
        "flags": slo_can_modify_flags,
    }


__all__ = [
    "SLO_ZEROPAGE_0x07",
    "SLO_ZEROPAGE_X_0x17",
    "SLO_INDEXED_INDIRECT_X_0x03",
    "SLO_INDIRECT_INDEXED_Y_0x13",
    "SLO_ABSOLUTE_0x0F",
    "SLO_ABSOLUTE_X_0x1F",
    "SLO_ABSOLUTE_Y_0x1B",
    "register_slo_instructions",
]
