#!/usr/bin/env python3
"""DCP (Decrement and Compare) illegal instruction.

ILLEGAL INSTRUCTION - NMOS 6502 only
On 65C02 (CMOS), these opcodes act as NOPs.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#DCP
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/Programming_with_unofficial_opcodes
"""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# DCP - Decrement Memory and Compare with Accumulator
#
# Operation: M = M - 1, Compare(A, M)
#
# This illegal instruction decrements a memory location, then compares the
# result with the accumulator (without modifying A). It is functionally
# equivalent to:
#   DEC {operand}
#   CMP {operand}
# but executes in a single instruction.
#
# NMOS (6502/6502A/6502C): Decrements memory and compares with A
# CMOS (65C02): Acts as NOP - no registers, flags, or memory modified
#
# Stability: STABLE
#
# ---
# Flags Affected:
# N	Z	C	I	D	V
# ✓	✓	✓	-	-	-
#
# N: Set if bit 7 of (A - M) is set
# Z: Set if A equals the decremented memory value
# C: Set if A >= the decremented memory value (no borrow)
#
# ---
# Addressing Modes:
# addressing       assembler    opc  bytes  cycles
# zeropage         DCP oper     C7   2      5
# zeropage,X       DCP oper,X   D7   2      6
# (indirect,X)     DCP (oper,X) C3   2      8
# (indirect),Y     DCP (oper),Y D3   2      8
# absolute         DCP oper     CF   3      6
# absolute,X       DCP oper,X   DF   3      7
# absolute,Y       DCP oper,Y   DB   3      7
#
# ---
# Usage:
# DCP is useful for decrementing a counter and testing if it has reached
# a specific value in a single instruction. Common in loop optimization.

DCP_ZEROPAGE_0xC7 = InstructionOpcode(
    0xC7,
    "mos6502.instructions.illegal._dcp",
    "dcp_zeropage_0xc7"
)

DCP_ZEROPAGE_X_0xD7 = InstructionOpcode(
    0xD7,
    "mos6502.instructions.illegal._dcp",
    "dcp_zeropage_x_0xd7"
)

DCP_INDEXED_INDIRECT_X_0xC3 = InstructionOpcode(
    0xC3,
    "mos6502.instructions.illegal._dcp",
    "dcp_indexed_indirect_x_0xc3"
)

DCP_INDIRECT_INDEXED_Y_0xD3 = InstructionOpcode(
    0xD3,
    "mos6502.instructions.illegal._dcp",
    "dcp_indirect_indexed_y_0xd3"
)

DCP_ABSOLUTE_0xCF = InstructionOpcode(
    0xCF,
    "mos6502.instructions.illegal._dcp",
    "dcp_absolute_0xcf"
)

DCP_ABSOLUTE_X_0xDF = InstructionOpcode(
    0xDF,
    "mos6502.instructions.illegal._dcp",
    "dcp_absolute_x_0xdf"
)

DCP_ABSOLUTE_Y_0xDB = InstructionOpcode(
    0xDB,
    "mos6502.instructions.illegal._dcp",
    "dcp_absolute_y_0xdb"
)


def add_dcp_to_instruction_set_enum(instruction_set_class) -> None:
    """Add DCP instructions to the InstructionSet enum dynamically."""
    class PseudoEnumMember(int):
        def __new__(cls, value, name) -> "InstructionSet":
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

    # Add each DCP variant to the enum
    for opcode_name, opcode_value in [
        ("DCP_ZEROPAGE_0xC7", DCP_ZEROPAGE_0xC7),
        ("DCP_ZEROPAGE_X_0xD7", DCP_ZEROPAGE_X_0xD7),
        ("DCP_INDEXED_INDIRECT_X_0xC3", DCP_INDEXED_INDIRECT_X_0xC3),
        ("DCP_INDIRECT_INDEXED_Y_0xD3", DCP_INDIRECT_INDEXED_Y_0xD3),
        ("DCP_ABSOLUTE_0xCF", DCP_ABSOLUTE_0xCF),
        ("DCP_ABSOLUTE_X_0xDF", DCP_ABSOLUTE_X_0xDF),
        ("DCP_ABSOLUTE_Y_0xDB", DCP_ABSOLUTE_Y_0xDB),
    ]:
        member = PseudoEnumMember(opcode_value, opcode_name)
        instruction_set_class._value2member_map_[opcode_value] = member
        setattr(instruction_set_class, opcode_name, opcode_value)


def register_dcp_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register DCP illegal instructions in the InstructionSet map."""
    # Add to enum
    add_dcp_to_instruction_set_enum(instruction_set_class)

    # DCP modifies N, Z, C flags
    dcp_can_modify_flags: Byte = Byte()
    dcp_can_modify_flags[0] = 1  # N
    dcp_can_modify_flags[1] = 1  # Z
    dcp_can_modify_flags[7] = 1  # C

    # Add to map
    instruction_map[DCP_ZEROPAGE_0xC7] = {
        "addressing": "zeropage",
        "assembler": "DCP {oper}",
        "opc": DCP_ZEROPAGE_0xC7,
        "bytes": "2",
        "cycles": "5",
        "flags": dcp_can_modify_flags,
    }

    instruction_map[DCP_ZEROPAGE_X_0xD7] = {
        "addressing": "zeropage,X",
        "assembler": "DCP {oper},X",
        "opc": DCP_ZEROPAGE_X_0xD7,
        "bytes": "2",
        "cycles": "6",
        "flags": dcp_can_modify_flags,
    }

    instruction_map[DCP_INDEXED_INDIRECT_X_0xC3] = {
        "addressing": "(indirect,X)",
        "assembler": "DCP ({oper},X)",
        "opc": DCP_INDEXED_INDIRECT_X_0xC3,
        "bytes": "2",
        "cycles": "8",
        "flags": dcp_can_modify_flags,
    }

    instruction_map[DCP_INDIRECT_INDEXED_Y_0xD3] = {
        "addressing": "(indirect),Y",
        "assembler": "DCP ({oper}),Y",
        "opc": DCP_INDIRECT_INDEXED_Y_0xD3,
        "bytes": "2",
        "cycles": "8",
        "flags": dcp_can_modify_flags,
    }

    instruction_map[DCP_ABSOLUTE_0xCF] = {
        "addressing": "absolute",
        "assembler": "DCP {oper}",
        "opc": DCP_ABSOLUTE_0xCF,
        "bytes": "3",
        "cycles": "6",
        "flags": dcp_can_modify_flags,
    }

    instruction_map[DCP_ABSOLUTE_X_0xDF] = {
        "addressing": "absolute,X",
        "assembler": "DCP {oper},X",
        "opc": DCP_ABSOLUTE_X_0xDF,
        "bytes": "3",
        "cycles": "7",
        "flags": dcp_can_modify_flags,
    }

    instruction_map[DCP_ABSOLUTE_Y_0xDB] = {
        "addressing": "absolute,Y",
        "assembler": "DCP {oper},Y",
        "opc": DCP_ABSOLUTE_Y_0xDB,
        "bytes": "3",
        "cycles": "7",
        "flags": dcp_can_modify_flags,
    }


__all__ = [
    "DCP_ZEROPAGE_0xC7",
    "DCP_ZEROPAGE_X_0xD7",
    "DCP_INDEXED_INDIRECT_X_0xC3",
    "DCP_INDIRECT_INDEXED_Y_0xD3",
    "DCP_ABSOLUTE_0xCF",
    "DCP_ABSOLUTE_X_0xDF",
    "DCP_ABSOLUTE_Y_0xDB",
    "register_dcp_instructions",
]
