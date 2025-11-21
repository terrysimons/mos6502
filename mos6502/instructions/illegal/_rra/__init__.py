#!/usr/bin/env python3
"""RRA (Rotate Right and Add with Carry) illegal instruction.

ILLEGAL INSTRUCTION - NMOS 6502 only
On 65C02 (CMOS), these opcodes act as NOPs.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#RRA
  - http://www.oxyron.de/html/opcodes02.html
"""
from __future__ import annotations

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# RRA - Rotate Right and Add with Carry
# Operation: M = ROR(M), A = A + M + C
# NMOS: Rotates memory right (through carry) and ADCs with A
# CMOS: Acts as NOP

RRA_ZEROPAGE_0x67 = InstructionOpcode(0x67, "mos6502.instructions.illegal._rra", "rra_zeropage_0x67")
RRA_ZEROPAGE_X_0x77 = InstructionOpcode(0x77, "mos6502.instructions.illegal._rra", "rra_zeropage_x_0x77")
RRA_INDEXED_INDIRECT_X_0x63 = InstructionOpcode(0x63, "mos6502.instructions.illegal._rra", "rra_indexed_indirect_x_0x63")
RRA_INDIRECT_INDEXED_Y_0x73 = InstructionOpcode(0x73, "mos6502.instructions.illegal._rra", "rra_indirect_indexed_y_0x73")
RRA_ABSOLUTE_0x6F = InstructionOpcode(0x6F, "mos6502.instructions.illegal._rra", "rra_absolute_0x6f")
RRA_ABSOLUTE_X_0x7F = InstructionOpcode(0x7F, "mos6502.instructions.illegal._rra", "rra_absolute_x_0x7f")
RRA_ABSOLUTE_Y_0x7B = InstructionOpcode(0x7B, "mos6502.instructions.illegal._rra", "rra_absolute_y_0x7b")


def add_rra_to_instruction_set_enum(instruction_set_class) -> None:
    """Add RRA instructions to the InstructionSet enum dynamically."""
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
        ("RRA_ZEROPAGE_0x67", RRA_ZEROPAGE_0x67),
        ("RRA_ZEROPAGE_X_0x77", RRA_ZEROPAGE_X_0x77),
        ("RRA_INDEXED_INDIRECT_X_0x63", RRA_INDEXED_INDIRECT_X_0x63),
        ("RRA_INDIRECT_INDEXED_Y_0x73", RRA_INDIRECT_INDEXED_Y_0x73),
        ("RRA_ABSOLUTE_0x6F", RRA_ABSOLUTE_0x6F),
        ("RRA_ABSOLUTE_X_0x7F", RRA_ABSOLUTE_X_0x7F),
        ("RRA_ABSOLUTE_Y_0x7B", RRA_ABSOLUTE_Y_0x7B),
    ]:
        member = PseudoEnumMember(opcode_value, opcode_name)
        instruction_set_class._value2member_map_[opcode_value] = member
        setattr(instruction_set_class, opcode_name, opcode_value)


def register_rra_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register RRA illegal instructions in the InstructionSet map."""
    add_rra_to_instruction_set_enum(instruction_set_class)

    rra_can_modify_flags: Byte = Byte()
    rra_can_modify_flags[0] = 1  # N
    rra_can_modify_flags[1] = 1  # Z
    rra_can_modify_flags[6] = 1  # V
    rra_can_modify_flags[7] = 1  # C

    instruction_map[RRA_ZEROPAGE_0x67] = {"addressing": "zeropage", "assembler": "RRA {oper}", "opc": RRA_ZEROPAGE_0x67, "bytes": "2", "cycles": "5", "flags": rra_can_modify_flags}
    instruction_map[RRA_ZEROPAGE_X_0x77] = {"addressing": "zeropage,X", "assembler": "RRA {oper},X", "opc": RRA_ZEROPAGE_X_0x77, "bytes": "2", "cycles": "6", "flags": rra_can_modify_flags}
    instruction_map[RRA_INDEXED_INDIRECT_X_0x63] = {"addressing": "(indirect,X)", "assembler": "RRA ({oper},X)", "opc": RRA_INDEXED_INDIRECT_X_0x63, "bytes": "2", "cycles": "8", "flags": rra_can_modify_flags}
    instruction_map[RRA_INDIRECT_INDEXED_Y_0x73] = {"addressing": "(indirect),Y", "assembler": "RRA ({oper}),Y", "opc": RRA_INDIRECT_INDEXED_Y_0x73, "bytes": "2", "cycles": "8", "flags": rra_can_modify_flags}
    instruction_map[RRA_ABSOLUTE_0x6F] = {"addressing": "absolute", "assembler": "RRA {oper}", "opc": RRA_ABSOLUTE_0x6F, "bytes": "3", "cycles": "6", "flags": rra_can_modify_flags}
    instruction_map[RRA_ABSOLUTE_X_0x7F] = {"addressing": "absolute,X", "assembler": "RRA {oper},X", "opc": RRA_ABSOLUTE_X_0x7F, "bytes": "3", "cycles": "7", "flags": rra_can_modify_flags}
    instruction_map[RRA_ABSOLUTE_Y_0x7B] = {"addressing": "absolute,Y", "assembler": "RRA {oper},Y", "opc": RRA_ABSOLUTE_Y_0x7B, "bytes": "3", "cycles": "7", "flags": rra_can_modify_flags}


__all__ = ["RRA_ZEROPAGE_0x67", "RRA_ZEROPAGE_X_0x77", "RRA_INDEXED_INDIRECT_X_0x63", "RRA_INDIRECT_INDEXED_Y_0x73", "RRA_ABSOLUTE_0x6F", "RRA_ABSOLUTE_X_0x7F", "RRA_ABSOLUTE_Y_0x7B", "register_rra_instructions"]
