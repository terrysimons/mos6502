#!/usr/bin/env python3
"""JAM (KIL, HLT) - Halt the CPU.

ILLEGAL INSTRUCTION - NMOS 6502 only
On 65C02 (CMOS), these opcodes act as NOPs.

JAM halts the CPU. On real hardware, this requires a hardware reset to recover.
The data bus is set to $FF and the CPU stops executing.

There are 12 JAM opcodes, all with identical behavior:
0x02, 0x12, 0x22, 0x32, 0x42, 0x52, 0x62, 0x72, 0x92, 0xB2, 0xD2, 0xF2

WARNING: Executing JAM will halt the emulated CPU. Call reset() to recover.

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# All JAM opcodes - they all halt the CPU
JAM_IMPLIED_0x02 = InstructionOpcode(0x02, "mos6502.instructions.illegal._jam", "jam_implied_0x02")
JAM_IMPLIED_0x12 = InstructionOpcode(0x12, "mos6502.instructions.illegal._jam", "jam_implied_0x12")
JAM_IMPLIED_0x22 = InstructionOpcode(0x22, "mos6502.instructions.illegal._jam", "jam_implied_0x22")
JAM_IMPLIED_0x32 = InstructionOpcode(0x32, "mos6502.instructions.illegal._jam", "jam_implied_0x32")
JAM_IMPLIED_0x42 = InstructionOpcode(0x42, "mos6502.instructions.illegal._jam", "jam_implied_0x42")
JAM_IMPLIED_0x52 = InstructionOpcode(0x52, "mos6502.instructions.illegal._jam", "jam_implied_0x52")
JAM_IMPLIED_0x62 = InstructionOpcode(0x62, "mos6502.instructions.illegal._jam", "jam_implied_0x62")
JAM_IMPLIED_0x72 = InstructionOpcode(0x72, "mos6502.instructions.illegal._jam", "jam_implied_0x72")
JAM_IMPLIED_0x92 = InstructionOpcode(0x92, "mos6502.instructions.illegal._jam", "jam_implied_0x92")
JAM_IMPLIED_0xB2 = InstructionOpcode(0xB2, "mos6502.instructions.illegal._jam", "jam_implied_0xb2")
JAM_IMPLIED_0xD2 = InstructionOpcode(0xD2, "mos6502.instructions.illegal._jam", "jam_implied_0xd2")
JAM_IMPLIED_0xF2 = InstructionOpcode(0xF2, "mos6502.instructions.illegal._jam", "jam_implied_0xf2")

# All JAM opcodes as a list for convenience
ALL_JAM_OPCODES = [
    JAM_IMPLIED_0x02, JAM_IMPLIED_0x12, JAM_IMPLIED_0x22, JAM_IMPLIED_0x32,
    JAM_IMPLIED_0x42, JAM_IMPLIED_0x52, JAM_IMPLIED_0x62, JAM_IMPLIED_0x72,
    JAM_IMPLIED_0x92, JAM_IMPLIED_0xB2, JAM_IMPLIED_0xD2, JAM_IMPLIED_0xF2,
]


def add_jam_to_instruction_set_enum(instruction_set_class) -> None:
    """Add JAM instructions to the InstructionSet enum dynamically."""
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

    jam_opcodes = [
        (JAM_IMPLIED_0x02, "JAM_IMPLIED_0x02"),
        (JAM_IMPLIED_0x12, "JAM_IMPLIED_0x12"),
        (JAM_IMPLIED_0x22, "JAM_IMPLIED_0x22"),
        (JAM_IMPLIED_0x32, "JAM_IMPLIED_0x32"),
        (JAM_IMPLIED_0x42, "JAM_IMPLIED_0x42"),
        (JAM_IMPLIED_0x52, "JAM_IMPLIED_0x52"),
        (JAM_IMPLIED_0x62, "JAM_IMPLIED_0x62"),
        (JAM_IMPLIED_0x72, "JAM_IMPLIED_0x72"),
        (JAM_IMPLIED_0x92, "JAM_IMPLIED_0x92"),
        (JAM_IMPLIED_0xB2, "JAM_IMPLIED_0xB2"),
        (JAM_IMPLIED_0xD2, "JAM_IMPLIED_0xD2"),
        (JAM_IMPLIED_0xF2, "JAM_IMPLIED_0xF2"),
    ]

    for opcode, name in jam_opcodes:
        member = PseudoEnumMember(opcode, name)
        instruction_set_class._value2member_map_[opcode] = member
        setattr(instruction_set_class, name, opcode)


def register_jam_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register JAM illegal instructions in the InstructionSet map."""
    add_jam_to_instruction_set_enum(instruction_set_class)

    # JAM doesn't modify any flags (CPU halts)
    jam_flags: Byte = Byte()

    for opcode in ALL_JAM_OPCODES:
        instruction_map[opcode] = {
            "addressing": "implied",
            "assembler": "JAM",
            "opc": opcode,
            "bytes": "1",
            "cycles": "-",  # CPU halts, no defined cycle count
            "flags": jam_flags,
        }


__all__ = [
    "JAM_IMPLIED_0x02",
    "JAM_IMPLIED_0x12",
    "JAM_IMPLIED_0x22",
    "JAM_IMPLIED_0x32",
    "JAM_IMPLIED_0x42",
    "JAM_IMPLIED_0x52",
    "JAM_IMPLIED_0x62",
    "JAM_IMPLIED_0x72",
    "JAM_IMPLIED_0x92",
    "JAM_IMPLIED_0xB2",
    "JAM_IMPLIED_0xD2",
    "JAM_IMPLIED_0xF2",
    "ALL_JAM_OPCODES",
    "register_jam_instructions",
]
