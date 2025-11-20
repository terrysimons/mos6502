#!/usr/bin/env python3
"""LAX (Load A and X) illegal instruction.

ILLEGAL INSTRUCTION - NMOS 6502 only
On 65C02 (CMOS), these opcodes act as NOPs.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#LAX
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/Programming_with_unofficial_opcodes
"""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# LAX - Load Accumulator and X Register
#
# Operation: A,X = M
#
# This illegal instruction loads a byte of memory into both the accumulator
# and X register simultaneously. It is functionally equivalent to:
#   LDA {operand}
#   LDX {operand}
# but executes in a single instruction.
#
# NMOS (6502/6502A/6502C): Loads memory into both A and X registers
# CMOS (65C02): Acts as NOP - no registers or flags modified
#
# Stability: STABLE (except immediate mode $AB which is HIGHLY UNSTABLE)
#
# ---
# Flags Affected:
# N	Z	C	I	D	V
# ✓	✓	-	-	-	-
#
# N: Set if bit 7 of loaded value is set
# Z: Set if loaded value is zero
#
# ---
# Addressing Modes:
# addressing       assembler    opc  bytes  cycles
# zeropage         LAX oper     A7   2      3
# zeropage,Y       LAX oper,Y   B7   2      4
# (indirect,X)     LAX (oper,X) A3   2      6
# (indirect),Y     LAX (oper),Y B3   2      5*
# absolute         LAX oper     AF   3      4
# absolute,Y       LAX oper,Y   BF   3      4*
# immediate        LAX #oper    AB   2      2      **HIGHLY UNSTABLE**
#
# * Add 1 cycle if page boundary is crossed
#
# ---
# WARNING - Immediate Mode ($AB):
# The immediate addressing mode is HIGHLY UNSTABLE. The actual operation is:
#   A,X = (A | CONST) & immediate
# where CONST is an undefined "magic constant" that varies unpredictably based on:
#   - Manufacturing process variations
#   - Temperature
#   - Voltage
#   - Individual chip characteristics
#
# DO NOT USE LAX #immediate IN PRODUCTION CODE
#
# The other addressing modes are stable and safe to use on NMOS 6502 variants.

LAX_ZEROPAGE_0xA7 = InstructionOpcode(
    0xA7,
    "mos6502.instructions.illegal._lax",
    "lax_zeropage_0xa7"
)

LAX_ZEROPAGE_Y_0xB7 = InstructionOpcode(
    0xB7,
    "mos6502.instructions.illegal._lax",
    "lax_zeropage_y_0xb7"
)

LAX_INDEXED_INDIRECT_X_0xA3 = InstructionOpcode(
    0xA3,
    "mos6502.instructions.illegal._lax",
    "lax_indexed_indirect_x_0xa3"
)

LAX_INDIRECT_INDEXED_Y_0xB3 = InstructionOpcode(
    0xB3,
    "mos6502.instructions.illegal._lax",
    "lax_indirect_indexed_y_0xb3"
)

LAX_ABSOLUTE_0xAF = InstructionOpcode(
    0xAF,
    "mos6502.instructions.illegal._lax",
    "lax_absolute_0xaf"
)

LAX_ABSOLUTE_Y_0xBF = InstructionOpcode(
    0xBF,
    "mos6502.instructions.illegal._lax",
    "lax_absolute_y_0xbf"
)

LAX_IMMEDIATE_0xAB = InstructionOpcode(
    0xAB,
    "mos6502.instructions.illegal._lax",
    "lax_immediate_0xab"
)


def add_lax_to_instruction_set_enum(instruction_set_class) -> None:
    """Add LAX instructions to the InstructionSet enum dynamically."""
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

    # Add each LAX variant to the enum
    for opcode_name, opcode_value in [
        ('LAX_ZEROPAGE_0xA7', LAX_ZEROPAGE_0xA7),
        ('LAX_ZEROPAGE_Y_0xB7', LAX_ZEROPAGE_Y_0xB7),
        ('LAX_INDEXED_INDIRECT_X_0xA3', LAX_INDEXED_INDIRECT_X_0xA3),
        ('LAX_INDIRECT_INDEXED_Y_0xB3', LAX_INDIRECT_INDEXED_Y_0xB3),
        ('LAX_ABSOLUTE_0xAF', LAX_ABSOLUTE_0xAF),
        ('LAX_ABSOLUTE_Y_0xBF', LAX_ABSOLUTE_Y_0xBF),
        ('LAX_IMMEDIATE_0xAB', LAX_IMMEDIATE_0xAB),
    ]:
        member = PseudoEnumMember(opcode_value, opcode_name)
        instruction_set_class._value2member_map_[opcode_value] = member
        setattr(instruction_set_class, opcode_name, opcode_value)


def register_lax_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register LAX illegal instructions in the InstructionSet map."""
    # Add to enum
    add_lax_to_instruction_set_enum(instruction_set_class)

    # Flags that can be modified
    lax_can_modify_flags: Byte = Byte()
    lax_can_modify_flags[0] = 1  # N
    lax_can_modify_flags[1] = 1  # Z

    # Add to map
    instruction_map[LAX_ZEROPAGE_0xA7] = {
        "addressing": "zeropage",
        "assembler": "LAX {oper}",
        "opc": LAX_ZEROPAGE_0xA7,
        "bytes": "2",
        "cycles": "3",
        "flags": lax_can_modify_flags,
    }

    instruction_map[LAX_ZEROPAGE_Y_0xB7] = {
        "addressing": "zeropage,Y",
        "assembler": "LAX {oper},Y",
        "opc": LAX_ZEROPAGE_Y_0xB7,
        "bytes": "2",
        "cycles": "4",
        "flags": lax_can_modify_flags,
    }

    instruction_map[LAX_INDEXED_INDIRECT_X_0xA3] = {
        "addressing": "(indirect,X)",
        "assembler": "LAX ({oper},X)",
        "opc": LAX_INDEXED_INDIRECT_X_0xA3,
        "bytes": "2",
        "cycles": "6",
        "flags": lax_can_modify_flags,
    }

    instruction_map[LAX_INDIRECT_INDEXED_Y_0xB3] = {
        "addressing": "(indirect),Y",
        "assembler": "LAX ({oper}),Y",
        "opc": LAX_INDIRECT_INDEXED_Y_0xB3,
        "bytes": "2",
        "cycles": "5*",
        "flags": lax_can_modify_flags,
    }

    instruction_map[LAX_ABSOLUTE_0xAF] = {
        "addressing": "absolute",
        "assembler": "LAX {oper}",
        "opc": LAX_ABSOLUTE_0xAF,
        "bytes": "3",
        "cycles": "4",
        "flags": lax_can_modify_flags,
    }

    instruction_map[LAX_ABSOLUTE_Y_0xBF] = {
        "addressing": "absolute,Y",
        "assembler": "LAX {oper},Y",
        "opc": LAX_ABSOLUTE_Y_0xBF,
        "bytes": "3",
        "cycles": "4*",
        "flags": lax_can_modify_flags,
    }

    instruction_map[LAX_IMMEDIATE_0xAB] = {
        "addressing": "immediate",
        "assembler": "LAX #{oper}",
        "opc": LAX_IMMEDIATE_0xAB,
        "bytes": "2",
        "cycles": "2",
        "flags": lax_can_modify_flags,
    }


__all__ = [
    'LAX_ZEROPAGE_0xA7',
    'LAX_ZEROPAGE_Y_0xB7',
    'LAX_INDEXED_INDIRECT_X_0xA3',
    'LAX_INDIRECT_INDEXED_Y_0xB3',
    'LAX_ABSOLUTE_0xAF',
    'LAX_ABSOLUTE_Y_0xBF',
    'LAX_IMMEDIATE_0xAB',
    'register_lax_instructions',
]
