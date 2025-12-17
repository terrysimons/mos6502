#!/usr/bin/env python3
"""Illegal SBC instruction - duplicate of 0xE9.

Opcode 0xEB is an undocumented duplicate of SBC Immediate (0xE9).
It behaves identically on all 6502 variants.

On NMOS: Identical to SBC #imm (0xE9)
On CMOS (65C02): Identical to SBC #imm (0xE9) - this opcode is officially NOP on
                 some documentation but actually behaves as SBC on real 65C02.

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# SBC Immediate duplicate
# Identical behavior to 0xE9 SBC Immediate
SBC_IMMEDIATE_0xEB = InstructionOpcode(
    0xEB,
    "mos6502.instructions.illegal._sbc_illegal",
    "sbc_immediate_0xeb"
)


def add_sbc_illegal_to_instruction_set_enum(instruction_set_class) -> None:
    """Add illegal SBC instruction to the InstructionSet enum dynamically."""
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

    member = PseudoEnumMember(SBC_IMMEDIATE_0xEB, "SBC_IMMEDIATE_0xEB")
    instruction_set_class._value2member_map_[SBC_IMMEDIATE_0xEB] = member
    setattr(instruction_set_class, "SBC_IMMEDIATE_0xEB", SBC_IMMEDIATE_0xEB)


def register_sbc_illegal_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register illegal SBC instruction in the InstructionSet map."""
    add_sbc_illegal_to_instruction_set_enum(instruction_set_class)

    from mos6502 import flags
    sbc_can_modify_flags: Byte = Byte()
    sbc_can_modify_flags[flags.N] = 1
    sbc_can_modify_flags[flags.Z] = 1
    sbc_can_modify_flags[flags.C] = 1
    sbc_can_modify_flags[flags.V] = 1

    instruction_map[SBC_IMMEDIATE_0xEB] = {
        "addressing": "immediate",
        "assembler": "SBC #{oper}",
        "opc": SBC_IMMEDIATE_0xEB,
        "bytes": "2",
        "cycles": "2",
        "flags": sbc_can_modify_flags,
    }


__all__ = ["SBC_IMMEDIATE_0xEB", "register_sbc_illegal_instructions"]
