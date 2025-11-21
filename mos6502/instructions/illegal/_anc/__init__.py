#!/usr/bin/env python3
"""ANC (AND with Carry) illegal instruction.

ILLEGAL INSTRUCTION - NMOS 6502 only
On 65C02 (CMOS), these opcodes act as NOPs.

ANC performs an AND operation with an immediate value, then sets the carry
flag to match the negative flag (bit 7 of the result).

References:
  - https://masswerk.at/6502/6502_instruction_set.html#ANC
  - http://www.oxyron.de/html/opcodes02.html
"""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# ANC - AND with Carry
# Operation: A = A & immediate, C = N
# NMOS: ANDs immediate value with A, sets C to bit 7 of result
# CMOS: Acts as NOP
# Note: Two opcodes (0x0B and 0x2B) perform the same operation

ANC_IMMEDIATE_0x0B = InstructionOpcode(0x0B, "mos6502.instructions.illegal._anc", "anc_immediate_0x0b")
ANC_IMMEDIATE_0x2B = InstructionOpcode(0x2B, "mos6502.instructions.illegal._anc", "anc_immediate_0x2b")


def add_anc_to_instruction_set_enum(instruction_set_class) -> None:
    """Add ANC instructions to the InstructionSet enum dynamically."""
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
        ("ANC_IMMEDIATE_0x0B", ANC_IMMEDIATE_0x0B),
        ("ANC_IMMEDIATE_0x2B", ANC_IMMEDIATE_0x2B),
    ]:
        member = PseudoEnumMember(opcode_value, opcode_name)
        instruction_set_class._value2member_map_[opcode_value] = member
        setattr(instruction_set_class, opcode_name, opcode_value)


def register_anc_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register ANC illegal instructions in the InstructionSet map."""
    add_anc_to_instruction_set_enum(instruction_set_class)

    anc_can_modify_flags: Byte = Byte()
    anc_can_modify_flags[0] = 1  # N
    anc_can_modify_flags[1] = 1  # Z
    anc_can_modify_flags[7] = 1  # C

    instruction_map[ANC_IMMEDIATE_0x0B] = {"addressing": "immediate", "assembler": "ANC #{oper}", "opc": ANC_IMMEDIATE_0x0B, "bytes": "2", "cycles": "2", "flags": anc_can_modify_flags}
    instruction_map[ANC_IMMEDIATE_0x2B] = {"addressing": "immediate", "assembler": "ANC #{oper}", "opc": ANC_IMMEDIATE_0x2B, "bytes": "2", "cycles": "2", "flags": anc_can_modify_flags}


__all__ = ["ANC_IMMEDIATE_0x0B", "ANC_IMMEDIATE_0x2B", "register_anc_instructions"]
