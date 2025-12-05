#!/usr/bin/env python3
"""ARR instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - NMOS only

ARR (AND then Rotate Right) performs a bitwise AND with an immediate value,
then rotates the result right through the carry flag. It sets flags in a
special way different from normal ROR:
- C is set from bit 6 of the result (not bit 0)
- V is set from bit 6 XOR bit 5 of the result

References:
  - https://masswerk.at/6502/6502_instruction_set.html#ARR
  - http://www.oxyron.de/html/opcodes02.html
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def arr_immediate_0x6b(cpu: MOS6502CPU) -> None:
    """Execute ARR (AND then Rotate Right) - Immediate addressing mode.

    Opcode: 0x6B
    Cycles: 2
    Bytes: 2
    Flags: N, Z, C, V (special handling)

    VARIANT: 6502 - ANDs with A, rotates right with special flag handling
    VARIANT: 6502A - ANDs with A, rotates right with special flag handling
    VARIANT: 6502C - ANDs with A, rotates right with special flag handling
    VARIANT: 65C02 - Acts as NOP (see _arr_65c02.py)

    Operation: A = (A & immediate) ROR, C = bit 6, V = bit 6 XOR bit 5

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    value: int = cpu.fetch_byte()
    carry_in: int = cpu.flags[flags.C]

    # AND with accumulator
    result: int = int(cpu.A) & value

    # Rotate right (carry goes to bit 7)
    cpu.A = ((result >> 1) | (carry_in << 7)) & 0xFF

    # Set N and Z flags based on result
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    # Special flag handling for ARR:
    # C is set from bit 6 of the result
    cpu.flags[flags.C] = 1 if (cpu.A & 0x40) else 0

    # V is set from bit 6 XOR bit 5 of the result
    bit6: int = 1 if (cpu.A & 0x40) else 0
    bit5: int = 1 if (cpu.A & 0x20) else 0
    cpu.flags[flags.V] = bit6 ^ bit5

    cpu.log.info("i")
