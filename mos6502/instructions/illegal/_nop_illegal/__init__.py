#!/usr/bin/env python3
"""Illegal NOP instructions.

These undocumented NOP variants exist on both NMOS and CMOS 6502.
They consume operand bytes but do not modify registers or flags.

On NMOS: These are true NOPs but with varying byte/cycle counts.
On CMOS (65C02): Same behavior - these slots are officially NOPs.

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""

from mos6502.instructions import InstructionOpcode
from mos6502.memory import Byte

# =============================================================================
# 1-byte NOPs (implied mode, 2 cycles)
# =============================================================================
NOP_IMPLIED_0x1A = InstructionOpcode(0x1A, "mos6502.instructions.illegal._nop_illegal", "nop_implied_0x1a")
NOP_IMPLIED_0x3A = InstructionOpcode(0x3A, "mos6502.instructions.illegal._nop_illegal", "nop_implied_0x3a")
NOP_IMPLIED_0x5A = InstructionOpcode(0x5A, "mos6502.instructions.illegal._nop_illegal", "nop_implied_0x5a")
NOP_IMPLIED_0x7A = InstructionOpcode(0x7A, "mos6502.instructions.illegal._nop_illegal", "nop_implied_0x7a")
NOP_IMPLIED_0xDA = InstructionOpcode(0xDA, "mos6502.instructions.illegal._nop_illegal", "nop_implied_0xda")
NOP_IMPLIED_0xFA = InstructionOpcode(0xFA, "mos6502.instructions.illegal._nop_illegal", "nop_implied_0xfa")

# =============================================================================
# 2-byte NOPs (immediate mode, 2 cycles)
# =============================================================================
NOP_IMMEDIATE_0x80 = InstructionOpcode(0x80, "mos6502.instructions.illegal._nop_illegal", "nop_immediate_0x80")
NOP_IMMEDIATE_0x82 = InstructionOpcode(0x82, "mos6502.instructions.illegal._nop_illegal", "nop_immediate_0x82")
NOP_IMMEDIATE_0x89 = InstructionOpcode(0x89, "mos6502.instructions.illegal._nop_illegal", "nop_immediate_0x89")
NOP_IMMEDIATE_0xC2 = InstructionOpcode(0xC2, "mos6502.instructions.illegal._nop_illegal", "nop_immediate_0xc2")
NOP_IMMEDIATE_0xE2 = InstructionOpcode(0xE2, "mos6502.instructions.illegal._nop_illegal", "nop_immediate_0xe2")

# =============================================================================
# 2-byte NOPs (zero page mode, 3 cycles)
# =============================================================================
NOP_ZEROPAGE_0x04 = InstructionOpcode(0x04, "mos6502.instructions.illegal._nop_illegal", "nop_zeropage_0x04")
NOP_ZEROPAGE_0x44 = InstructionOpcode(0x44, "mos6502.instructions.illegal._nop_illegal", "nop_zeropage_0x44")
NOP_ZEROPAGE_0x64 = InstructionOpcode(0x64, "mos6502.instructions.illegal._nop_illegal", "nop_zeropage_0x64")

# =============================================================================
# 2-byte NOPs (zero page,X mode, 4 cycles)
# =============================================================================
NOP_ZEROPAGE_X_0x14 = InstructionOpcode(0x14, "mos6502.instructions.illegal._nop_illegal", "nop_zeropage_x_0x14")
NOP_ZEROPAGE_X_0x34 = InstructionOpcode(0x34, "mos6502.instructions.illegal._nop_illegal", "nop_zeropage_x_0x34")
NOP_ZEROPAGE_X_0x54 = InstructionOpcode(0x54, "mos6502.instructions.illegal._nop_illegal", "nop_zeropage_x_0x54")
NOP_ZEROPAGE_X_0x74 = InstructionOpcode(0x74, "mos6502.instructions.illegal._nop_illegal", "nop_zeropage_x_0x74")
NOP_ZEROPAGE_X_0xD4 = InstructionOpcode(0xD4, "mos6502.instructions.illegal._nop_illegal", "nop_zeropage_x_0xd4")
NOP_ZEROPAGE_X_0xF4 = InstructionOpcode(0xF4, "mos6502.instructions.illegal._nop_illegal", "nop_zeropage_x_0xf4")

# =============================================================================
# 3-byte NOPs (absolute mode, 4 cycles)
# =============================================================================
NOP_ABSOLUTE_0x0C = InstructionOpcode(0x0C, "mos6502.instructions.illegal._nop_illegal", "nop_absolute_0x0c")

# =============================================================================
# 3-byte NOPs (absolute,X mode, 4+ cycles - extra cycle on page boundary)
# =============================================================================
NOP_ABSOLUTE_X_0x1C = InstructionOpcode(0x1C, "mos6502.instructions.illegal._nop_illegal", "nop_absolute_x_0x1c")
NOP_ABSOLUTE_X_0x3C = InstructionOpcode(0x3C, "mos6502.instructions.illegal._nop_illegal", "nop_absolute_x_0x3c")
NOP_ABSOLUTE_X_0x5C = InstructionOpcode(0x5C, "mos6502.instructions.illegal._nop_illegal", "nop_absolute_x_0x5c")
NOP_ABSOLUTE_X_0x7C = InstructionOpcode(0x7C, "mos6502.instructions.illegal._nop_illegal", "nop_absolute_x_0x7c")
NOP_ABSOLUTE_X_0xDC = InstructionOpcode(0xDC, "mos6502.instructions.illegal._nop_illegal", "nop_absolute_x_0xdc")
NOP_ABSOLUTE_X_0xFC = InstructionOpcode(0xFC, "mos6502.instructions.illegal._nop_illegal", "nop_absolute_x_0xfc")


def add_nop_illegal_to_instruction_set_enum(instruction_set_class) -> None:
    """Add illegal NOP instructions to the InstructionSet enum dynamically."""
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

    # All illegal NOP opcodes
    all_nops = [
        # 1-byte implied
        (NOP_IMPLIED_0x1A, "NOP_IMPLIED_0x1A"),
        (NOP_IMPLIED_0x3A, "NOP_IMPLIED_0x3A"),
        (NOP_IMPLIED_0x5A, "NOP_IMPLIED_0x5A"),
        (NOP_IMPLIED_0x7A, "NOP_IMPLIED_0x7A"),
        (NOP_IMPLIED_0xDA, "NOP_IMPLIED_0xDA"),
        (NOP_IMPLIED_0xFA, "NOP_IMPLIED_0xFA"),
        # 2-byte immediate
        (NOP_IMMEDIATE_0x80, "NOP_IMMEDIATE_0x80"),
        (NOP_IMMEDIATE_0x82, "NOP_IMMEDIATE_0x82"),
        (NOP_IMMEDIATE_0x89, "NOP_IMMEDIATE_0x89"),
        (NOP_IMMEDIATE_0xC2, "NOP_IMMEDIATE_0xC2"),
        (NOP_IMMEDIATE_0xE2, "NOP_IMMEDIATE_0xE2"),
        # 2-byte zero page
        (NOP_ZEROPAGE_0x04, "NOP_ZEROPAGE_0x04"),
        (NOP_ZEROPAGE_0x44, "NOP_ZEROPAGE_0x44"),
        (NOP_ZEROPAGE_0x64, "NOP_ZEROPAGE_0x64"),
        # 2-byte zero page,X
        (NOP_ZEROPAGE_X_0x14, "NOP_ZEROPAGE_X_0x14"),
        (NOP_ZEROPAGE_X_0x34, "NOP_ZEROPAGE_X_0x34"),
        (NOP_ZEROPAGE_X_0x54, "NOP_ZEROPAGE_X_0x54"),
        (NOP_ZEROPAGE_X_0x74, "NOP_ZEROPAGE_X_0x74"),
        (NOP_ZEROPAGE_X_0xD4, "NOP_ZEROPAGE_X_0xD4"),
        (NOP_ZEROPAGE_X_0xF4, "NOP_ZEROPAGE_X_0xF4"),
        # 3-byte absolute
        (NOP_ABSOLUTE_0x0C, "NOP_ABSOLUTE_0x0C"),
        # 3-byte absolute,X
        (NOP_ABSOLUTE_X_0x1C, "NOP_ABSOLUTE_X_0x1C"),
        (NOP_ABSOLUTE_X_0x3C, "NOP_ABSOLUTE_X_0x3C"),
        (NOP_ABSOLUTE_X_0x5C, "NOP_ABSOLUTE_X_0x5C"),
        (NOP_ABSOLUTE_X_0x7C, "NOP_ABSOLUTE_X_0x7C"),
        (NOP_ABSOLUTE_X_0xDC, "NOP_ABSOLUTE_X_0xDC"),
        (NOP_ABSOLUTE_X_0xFC, "NOP_ABSOLUTE_X_0xFC"),
    ]

    for opcode, name in all_nops:
        member = PseudoEnumMember(opcode, name)
        instruction_set_class._value2member_map_[opcode] = member
        setattr(instruction_set_class, name, opcode)


def register_nop_illegal_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register all illegal NOP instructions in the InstructionSet map."""
    add_nop_illegal_to_instruction_set_enum(instruction_set_class)

    # NOPs don't modify any flags
    nop_flags: Byte = Byte()

    # 1-byte implied NOPs (2 cycles)
    for opcode in [NOP_IMPLIED_0x1A, NOP_IMPLIED_0x3A, NOP_IMPLIED_0x5A,
                   NOP_IMPLIED_0x7A, NOP_IMPLIED_0xDA, NOP_IMPLIED_0xFA]:
        instruction_map[opcode] = {
            "addressing": "implied",
            "assembler": "NOP",
            "opc": opcode,
            "bytes": "1",
            "cycles": "2",
            "flags": nop_flags,
        }

    # 2-byte immediate NOPs (2 cycles)
    for opcode in [NOP_IMMEDIATE_0x80, NOP_IMMEDIATE_0x82, NOP_IMMEDIATE_0x89,
                   NOP_IMMEDIATE_0xC2, NOP_IMMEDIATE_0xE2]:
        instruction_map[opcode] = {
            "addressing": "immediate",
            "assembler": "NOP #{oper}",
            "opc": opcode,
            "bytes": "2",
            "cycles": "2",
            "flags": nop_flags,
        }

    # 2-byte zero page NOPs (3 cycles)
    for opcode in [NOP_ZEROPAGE_0x04, NOP_ZEROPAGE_0x44, NOP_ZEROPAGE_0x64]:
        instruction_map[opcode] = {
            "addressing": "zeropage",
            "assembler": "NOP {oper}",
            "opc": opcode,
            "bytes": "2",
            "cycles": "3",
            "flags": nop_flags,
        }

    # 2-byte zero page,X NOPs (4 cycles)
    for opcode in [NOP_ZEROPAGE_X_0x14, NOP_ZEROPAGE_X_0x34, NOP_ZEROPAGE_X_0x54,
                   NOP_ZEROPAGE_X_0x74, NOP_ZEROPAGE_X_0xD4, NOP_ZEROPAGE_X_0xF4]:
        instruction_map[opcode] = {
            "addressing": "zeropage,X",
            "assembler": "NOP {oper},X",
            "opc": opcode,
            "bytes": "2",
            "cycles": "4",
            "flags": nop_flags,
        }

    # 3-byte absolute NOPs (4 cycles)
    instruction_map[NOP_ABSOLUTE_0x0C] = {
        "addressing": "absolute",
        "assembler": "NOP {oper}",
        "opc": NOP_ABSOLUTE_0x0C,
        "bytes": "3",
        "cycles": "4",
        "flags": nop_flags,
    }

    # 3-byte absolute,X NOPs (4+ cycles - extra on page boundary)
    for opcode in [NOP_ABSOLUTE_X_0x1C, NOP_ABSOLUTE_X_0x3C, NOP_ABSOLUTE_X_0x5C,
                   NOP_ABSOLUTE_X_0x7C, NOP_ABSOLUTE_X_0xDC, NOP_ABSOLUTE_X_0xFC]:
        instruction_map[opcode] = {
            "addressing": "absolute,X",
            "assembler": "NOP {oper},X",
            "opc": opcode,
            "bytes": "3",
            "cycles": "4+",
            "flags": nop_flags,
        }


__all__ = [
    # 1-byte implied
    "NOP_IMPLIED_0x1A",
    "NOP_IMPLIED_0x3A",
    "NOP_IMPLIED_0x5A",
    "NOP_IMPLIED_0x7A",
    "NOP_IMPLIED_0xDA",
    "NOP_IMPLIED_0xFA",
    # 2-byte immediate
    "NOP_IMMEDIATE_0x80",
    "NOP_IMMEDIATE_0x82",
    "NOP_IMMEDIATE_0x89",
    "NOP_IMMEDIATE_0xC2",
    "NOP_IMMEDIATE_0xE2",
    # 2-byte zero page
    "NOP_ZEROPAGE_0x04",
    "NOP_ZEROPAGE_0x44",
    "NOP_ZEROPAGE_0x64",
    # 2-byte zero page,X
    "NOP_ZEROPAGE_X_0x14",
    "NOP_ZEROPAGE_X_0x34",
    "NOP_ZEROPAGE_X_0x54",
    "NOP_ZEROPAGE_X_0x74",
    "NOP_ZEROPAGE_X_0xD4",
    "NOP_ZEROPAGE_X_0xF4",
    # 3-byte absolute
    "NOP_ABSOLUTE_0x0C",
    # 3-byte absolute,X
    "NOP_ABSOLUTE_X_0x1C",
    "NOP_ABSOLUTE_X_0x3C",
    "NOP_ABSOLUTE_X_0x5C",
    "NOP_ABSOLUTE_X_0x7C",
    "NOP_ABSOLUTE_X_0xDC",
    "NOP_ABSOLUTE_X_0xFC",
    # Registration function
    "register_nop_illegal_instructions",
]
