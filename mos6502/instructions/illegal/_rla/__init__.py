#!/usr/bin/env python3
"""RLA (Rotate Left and AND with Accumulator) illegal instruction.

ILLEGAL INSTRUCTION - NMOS 6502 only
On 65C02 (CMOS), these opcodes act as NOPs.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#RLA
  - http://www.oxyron.de/html/opcodes02.html
"""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# RLA - Rotate Left and AND with Accumulator
# Operation: M = ROL(M), A = A & M
# NMOS: Rotates memory left (through carry) and ANDs with A
# CMOS: Acts as NOP

RLA_ZEROPAGE_0x27 = InstructionOpcode(0x27, "mos6502.instructions.illegal._rla", "rla_zeropage_0x27")
RLA_ZEROPAGE_X_0x37 = InstructionOpcode(0x37, "mos6502.instructions.illegal._rla", "rla_zeropage_x_0x37")
RLA_INDEXED_INDIRECT_X_0x23 = InstructionOpcode(0x23, "mos6502.instructions.illegal._rla", "rla_indexed_indirect_x_0x23")
RLA_INDIRECT_INDEXED_Y_0x33 = InstructionOpcode(0x33, "mos6502.instructions.illegal._rla", "rla_indirect_indexed_y_0x33")
RLA_ABSOLUTE_0x2F = InstructionOpcode(0x2F, "mos6502.instructions.illegal._rla", "rla_absolute_0x2f")
RLA_ABSOLUTE_X_0x3F = InstructionOpcode(0x3F, "mos6502.instructions.illegal._rla", "rla_absolute_x_0x3f")
RLA_ABSOLUTE_Y_0x3B = InstructionOpcode(0x3B, "mos6502.instructions.illegal._rla", "rla_absolute_y_0x3b")


def add_rla_to_instruction_set_enum(instruction_set_class) -> None:
    """Add RLA instructions to the InstructionSet enum dynamically."""
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

    for opcode_name, opcode_value in [
        ("RLA_ZEROPAGE_0x27", RLA_ZEROPAGE_0x27),
        ("RLA_ZEROPAGE_X_0x37", RLA_ZEROPAGE_X_0x37),
        ("RLA_INDEXED_INDIRECT_X_0x23", RLA_INDEXED_INDIRECT_X_0x23),
        ("RLA_INDIRECT_INDEXED_Y_0x33", RLA_INDIRECT_INDEXED_Y_0x33),
        ("RLA_ABSOLUTE_0x2F", RLA_ABSOLUTE_0x2F),
        ("RLA_ABSOLUTE_X_0x3F", RLA_ABSOLUTE_X_0x3F),
        ("RLA_ABSOLUTE_Y_0x3B", RLA_ABSOLUTE_Y_0x3B),
    ]:
        member = PseudoEnumMember(opcode_value, opcode_name)
        instruction_set_class._value2member_map_[opcode_value] = member
        setattr(instruction_set_class, opcode_name, opcode_value)


def register_rla_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register RLA illegal instructions in the InstructionSet map."""
    add_rla_to_instruction_set_enum(instruction_set_class)

    rla_can_modify_flags: Byte = Byte()
    rla_can_modify_flags[0] = 1  # N
    rla_can_modify_flags[1] = 1  # Z
    rla_can_modify_flags[7] = 1  # C

    instruction_map[RLA_ZEROPAGE_0x27] = {"addressing": "zeropage", "assembler": "RLA {oper}", "opc": RLA_ZEROPAGE_0x27, "bytes": "2", "cycles": "5", "flags": rla_can_modify_flags}
    instruction_map[RLA_ZEROPAGE_X_0x37] = {"addressing": "zeropage,X", "assembler": "RLA {oper},X", "opc": RLA_ZEROPAGE_X_0x37, "bytes": "2", "cycles": "6", "flags": rla_can_modify_flags}
    instruction_map[RLA_INDEXED_INDIRECT_X_0x23] = {"addressing": "(indirect,X)", "assembler": "RLA ({oper},X)", "opc": RLA_INDEXED_INDIRECT_X_0x23, "bytes": "2", "cycles": "8", "flags": rla_can_modify_flags}
    instruction_map[RLA_INDIRECT_INDEXED_Y_0x33] = {"addressing": "(indirect),Y", "assembler": "RLA ({oper}),Y", "opc": RLA_INDIRECT_INDEXED_Y_0x33, "bytes": "2", "cycles": "8", "flags": rla_can_modify_flags}
    instruction_map[RLA_ABSOLUTE_0x2F] = {"addressing": "absolute", "assembler": "RLA {oper}", "opc": RLA_ABSOLUTE_0x2F, "bytes": "3", "cycles": "6", "flags": rla_can_modify_flags}
    instruction_map[RLA_ABSOLUTE_X_0x3F] = {"addressing": "absolute,X", "assembler": "RLA {oper},X", "opc": RLA_ABSOLUTE_X_0x3F, "bytes": "3", "cycles": "7", "flags": rla_can_modify_flags}
    instruction_map[RLA_ABSOLUTE_Y_0x3B] = {"addressing": "absolute,Y", "assembler": "RLA {oper},Y", "opc": RLA_ABSOLUTE_Y_0x3B, "bytes": "3", "cycles": "7", "flags": rla_can_modify_flags}


__all__ = ["RLA_ZEROPAGE_0x27", "RLA_ZEROPAGE_X_0x37", "RLA_INDEXED_INDIRECT_X_0x23", "RLA_INDIRECT_INDEXED_Y_0x33", "RLA_ABSOLUTE_0x2F", "RLA_ABSOLUTE_X_0x3F", "RLA_ABSOLUTE_Y_0x3B", "register_rla_instructions"]
