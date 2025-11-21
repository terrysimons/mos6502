#!/usr/bin/env python3
"""SRE (Shift Right and EOR with Accumulator) illegal instruction.

ILLEGAL INSTRUCTION - NMOS 6502 only
On 65C02 (CMOS), these opcodes act as NOPs.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#SRE
  - http://www.oxyron.de/html/opcodes02.html
"""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# SRE - Shift Right and EOR with Accumulator
# Operation: M = LSR(M), A = A ^ M
# NMOS: Shifts memory right (bit 0 to carry) and EORs with A
# CMOS: Acts as NOP

SRE_ZEROPAGE_0x47 = InstructionOpcode(0x47, "mos6502.instructions.illegal._sre", "sre_zeropage_0x47")
SRE_ZEROPAGE_X_0x57 = InstructionOpcode(0x57, "mos6502.instructions.illegal._sre", "sre_zeropage_x_0x57")
SRE_INDEXED_INDIRECT_X_0x43 = InstructionOpcode(0x43, "mos6502.instructions.illegal._sre", "sre_indexed_indirect_x_0x43")
SRE_INDIRECT_INDEXED_Y_0x53 = InstructionOpcode(0x53, "mos6502.instructions.illegal._sre", "sre_indirect_indexed_y_0x53")
SRE_ABSOLUTE_0x4F = InstructionOpcode(0x4F, "mos6502.instructions.illegal._sre", "sre_absolute_0x4f")
SRE_ABSOLUTE_X_0x5F = InstructionOpcode(0x5F, "mos6502.instructions.illegal._sre", "sre_absolute_x_0x5f")
SRE_ABSOLUTE_Y_0x5B = InstructionOpcode(0x5B, "mos6502.instructions.illegal._sre", "sre_absolute_y_0x5b")


def add_sre_to_instruction_set_enum(instruction_set_class) -> None:
    """Add SRE instructions to the InstructionSet enum dynamically."""
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

    for opcode_name, opcode_value in [
        ("SRE_ZEROPAGE_0x47", SRE_ZEROPAGE_0x47),
        ("SRE_ZEROPAGE_X_0x57", SRE_ZEROPAGE_X_0x57),
        ("SRE_INDEXED_INDIRECT_X_0x43", SRE_INDEXED_INDIRECT_X_0x43),
        ("SRE_INDIRECT_INDEXED_Y_0x53", SRE_INDIRECT_INDEXED_Y_0x53),
        ("SRE_ABSOLUTE_0x4F", SRE_ABSOLUTE_0x4F),
        ("SRE_ABSOLUTE_X_0x5F", SRE_ABSOLUTE_X_0x5F),
        ("SRE_ABSOLUTE_Y_0x5B", SRE_ABSOLUTE_Y_0x5B),
    ]:
        member = PseudoEnumMember(opcode_value, opcode_name)
        instruction_set_class._value2member_map_[opcode_value] = member
        setattr(instruction_set_class, opcode_name, opcode_value)


def register_sre_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register SRE illegal instructions in the InstructionSet map."""
    add_sre_to_instruction_set_enum(instruction_set_class)

    sre_can_modify_flags: Byte = Byte()
    sre_can_modify_flags[0] = 1  # N
    sre_can_modify_flags[1] = 1  # Z
    sre_can_modify_flags[7] = 1  # C

    instruction_map[SRE_ZEROPAGE_0x47] = {"addressing": "zeropage", "assembler": "SRE {oper}", "opc": SRE_ZEROPAGE_0x47, "bytes": "2", "cycles": "5", "flags": sre_can_modify_flags}
    instruction_map[SRE_ZEROPAGE_X_0x57] = {"addressing": "zeropage,X", "assembler": "SRE {oper},X", "opc": SRE_ZEROPAGE_X_0x57, "bytes": "2", "cycles": "6", "flags": sre_can_modify_flags}
    instruction_map[SRE_INDEXED_INDIRECT_X_0x43] = {"addressing": "(indirect,X)", "assembler": "SRE ({oper},X)", "opc": SRE_INDEXED_INDIRECT_X_0x43, "bytes": "2", "cycles": "8", "flags": sre_can_modify_flags}
    instruction_map[SRE_INDIRECT_INDEXED_Y_0x53] = {"addressing": "(indirect),Y", "assembler": "SRE ({oper}),Y", "opc": SRE_INDIRECT_INDEXED_Y_0x53, "bytes": "2", "cycles": "8", "flags": sre_can_modify_flags}
    instruction_map[SRE_ABSOLUTE_0x4F] = {"addressing": "absolute", "assembler": "SRE {oper}", "opc": SRE_ABSOLUTE_0x4F, "bytes": "3", "cycles": "6", "flags": sre_can_modify_flags}
    instruction_map[SRE_ABSOLUTE_X_0x5F] = {"addressing": "absolute,X", "assembler": "SRE {oper},X", "opc": SRE_ABSOLUTE_X_0x5F, "bytes": "3", "cycles": "7", "flags": sre_can_modify_flags}
    instruction_map[SRE_ABSOLUTE_Y_0x5B] = {"addressing": "absolute,Y", "assembler": "SRE {oper},Y", "opc": SRE_ABSOLUTE_Y_0x5B, "bytes": "3", "cycles": "7", "flags": sre_can_modify_flags}


__all__ = ["SRE_ZEROPAGE_0x47", "SRE_ZEROPAGE_X_0x57", "SRE_INDEXED_INDIRECT_X_0x43", "SRE_INDIRECT_INDEXED_Y_0x53", "SRE_ABSOLUTE_0x4F", "SRE_ABSOLUTE_X_0x5F", "SRE_ABSOLUTE_Y_0x5B", "register_sre_instructions"]
