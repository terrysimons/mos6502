#!/usr/bin/env python3
"""Shift and rotate instructions for the MOS 6502 CPU."""

# Import from individual shift instruction modules
from mos6502.instructions.shift._asl import (
    ASL_ABSOLUTE_0x0E,
    ASL_ABSOLUTE_X_0x1E,
    ASL_ACCUMULATOR_0x0A,
    ASL_ZEROPAGE_0x06,
    ASL_ZEROPAGE_X_0x16,
    register_asl_instructions,
)
from mos6502.instructions.shift._lsr import (
    LSR_ABSOLUTE_0x4E,
    LSR_ABSOLUTE_X_0x5E,
    LSR_ACCUMULATOR_0x4A,
    LSR_ZEROPAGE_0x46,
    LSR_ZEROPAGE_X_0x56,
    register_lsr_instructions,
)
from mos6502.instructions.shift._rol import (
    ROL_ABSOLUTE_0x2E,
    ROL_ABSOLUTE_X_0x3E,
    ROL_ACCUMULATOR_0x2A,
    ROL_ZEROPAGE_0x26,
    ROL_ZEROPAGE_X_0x36,
    register_rol_instructions,
)
from mos6502.instructions.shift._ror import (
    ROR_ABSOLUTE_0x6E,
    ROR_ABSOLUTE_X_0x7E,
    ROR_ACCUMULATOR_0x6A,
    ROR_ZEROPAGE_0x66,
    ROR_ZEROPAGE_X_0x76,
    register_ror_instructions,
)

__all__ = [
    # ASL
    "ASL_ACCUMULATOR_0x0A",
    "ASL_ZEROPAGE_0x06",
    "ASL_ZEROPAGE_X_0x16",
    "ASL_ABSOLUTE_0x0E",
    "ASL_ABSOLUTE_X_0x1E",
    "register_asl_instructions",
    # LSR
    "LSR_ACCUMULATOR_0x4A",
    "LSR_ZEROPAGE_0x46",
    "LSR_ZEROPAGE_X_0x56",
    "LSR_ABSOLUTE_0x4E",
    "LSR_ABSOLUTE_X_0x5E",
    "register_lsr_instructions",
    # ROL
    "ROL_ACCUMULATOR_0x2A",
    "ROL_ZEROPAGE_0x26",
    "ROL_ZEROPAGE_X_0x36",
    "ROL_ABSOLUTE_0x2E",
    "ROL_ABSOLUTE_X_0x3E",
    "register_rol_instructions",
    # ROR
    "ROR_ACCUMULATOR_0x6A",
    "ROR_ZEROPAGE_0x66",
    "ROR_ZEROPAGE_X_0x76",
    "ROR_ABSOLUTE_0x6E",
    "ROR_ABSOLUTE_X_0x7E",
    "register_ror_instructions",
]


def register_all_shift_instructions(instruction_set_class, instruction_map: dict) -> None:
    """Register all shift and rotate instructions."""
    register_asl_instructions(instruction_set_class, instruction_map)
    register_lsr_instructions(instruction_set_class, instruction_map)
    register_rol_instructions(instruction_set_class, instruction_map)
    register_ror_instructions(instruction_set_class, instruction_map)
