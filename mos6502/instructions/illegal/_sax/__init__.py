#!/usr/bin/env python3
"""SAX (Store A AND X) illegal instruction.

ILLEGAL INSTRUCTION - NMOS 6502 only
On 65C02 (CMOS), these opcodes act as NOPs.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#SAX
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/Programming_with_unofficial_opcodes
"""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# SAX - Store Accumulator AND X Register
#
# Operation: M = A & X
#
# This illegal instruction performs a bitwise AND operation between the
# accumulator and X register, then stores the result to memory.
#
# NMOS (6502/6502A/6502C): Stores A & X to memory
# CMOS (65C02): Acts as NOP - no registers, flags, or memory modified
#
# Stability: STABLE
#
# ---
# Flags Affected:
# N	Z	C	I	D	V
# -	-	-	-	-	-
#
# No flags are affected by this instruction.
#
# ---
# Addressing Modes:
# addressing       assembler    opc  bytes  cycles
# zeropage         SAX oper     87   2      3
# zeropage,Y       SAX oper,Y   97   2      4
# (indirect,X)     SAX (oper,X) 83   2      6
# absolute         SAX oper     8F   3      4
#
# Note: SAX does not support absolute indexed modes (no SAX abs,X or SAX abs,Y)
#
# ---
# Usage:
# This instruction is useful for quickly storing the result of A & X without
# modifying either register. It's stable and safe to use on NMOS 6502 variants.

SAX_ZEROPAGE_0x87 = InstructionOpcode(
    0x87,
    "mos6502.instructions.illegal._sax",
    "sax_zeropage_0x87"
)

SAX_ZEROPAGE_Y_0x97 = InstructionOpcode(
    0x97,
    "mos6502.instructions.illegal._sax",
    "sax_zeropage_y_0x97"
)

SAX_INDEXED_INDIRECT_X_0x83 = InstructionOpcode(
    0x83,
    "mos6502.instructions.illegal._sax",
    "sax_indexed_indirect_x_0x83"
)

SAX_ABSOLUTE_0x8F = InstructionOpcode(
    0x8F,
    "mos6502.instructions.illegal._sax",
    "sax_absolute_0x8f"
)


def add_sax_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SAX instructions to the InstructionSet enum dynamically."""
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

    # Add each SAX variant to the enum
    for opcode_name, opcode_value in [
        ("SAX_ZEROPAGE_0x87", SAX_ZEROPAGE_0x87),
        ("SAX_ZEROPAGE_Y_0x97", SAX_ZEROPAGE_Y_0x97),
        ("SAX_INDEXED_INDIRECT_X_0x83", SAX_INDEXED_INDIRECT_X_0x83),
        ("SAX_ABSOLUTE_0x8F", SAX_ABSOLUTE_0x8F),
    ]:
        member = PseudoEnumMember(opcode_value, opcode_name)
        instruction_set_class._value2member_map_[opcode_value] = member
        setattr(instruction_set_class, opcode_name, opcode_value)


def register_sax_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SAX illegal instructions in the InstructionSet map."""
    # Add to enum
    add_sax_to_instruction_set_enum(instruction_set_class)

    # SAX doesn't modify any flags
    sax_can_modify_flags: Byte = Byte()

    # Add to map
    instruction_map[SAX_ZEROPAGE_0x87] = {
        "addressing": "zeropage",
        "assembler": "SAX {oper}",
        "opc": SAX_ZEROPAGE_0x87,
        "bytes": "2",
        "cycles": "3",
        "flags": sax_can_modify_flags,
    }

    instruction_map[SAX_ZEROPAGE_Y_0x97] = {
        "addressing": "zeropage,Y",
        "assembler": "SAX {oper},Y",
        "opc": SAX_ZEROPAGE_Y_0x97,
        "bytes": "2",
        "cycles": "4",
        "flags": sax_can_modify_flags,
    }

    instruction_map[SAX_INDEXED_INDIRECT_X_0x83] = {
        "addressing": "(indirect,X)",
        "assembler": "SAX ({oper},X)",
        "opc": SAX_INDEXED_INDIRECT_X_0x83,
        "bytes": "2",
        "cycles": "6",
        "flags": sax_can_modify_flags,
    }

    instruction_map[SAX_ABSOLUTE_0x8F] = {
        "addressing": "absolute",
        "assembler": "SAX {oper}",
        "opc": SAX_ABSOLUTE_0x8F,
        "bytes": "3",
        "cycles": "4",
        "flags": sax_can_modify_flags,
    }


__all__ = [
    "SAX_ZEROPAGE_0x87",
    "SAX_ZEROPAGE_Y_0x97",
    "SAX_INDEXED_INDIRECT_X_0x83",
    "SAX_ABSOLUTE_0x8F",
    "register_sax_instructions",
]
