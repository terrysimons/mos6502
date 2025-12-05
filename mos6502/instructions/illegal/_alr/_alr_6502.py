#!/usr/bin/env python3
"""ALR instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - NMOS only

ALR (AND then Logical Shift Right) performs a bitwise AND with an immediate
value, then shifts the result right by one bit (LSR operation).

References:
  - https://masswerk.at/6502/6502_instruction_set.html#ALR
  - http://www.oxyron.de/html/opcodes02.html
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def alr_immediate_0x4b(cpu: MOS6502CPU) -> None:
    """Execute ALR (AND then Logical Shift Right) - Immediate addressing mode.

    Opcode: 0x4B
    Cycles: 2
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - ANDs with A, then shifts right
    VARIANT: 6502A - ANDs with A, then shifts right
    VARIANT: 6502C - ANDs with A, then shifts right
    VARIANT: 65C02 - Acts as NOP (see _alr_65c02.py)

    Operation: A = (A & immediate) >> 1

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    value: int = cpu.fetch_byte()

    # AND with accumulator
    result: int = int(cpu.A) & value

    # Shift right (bit 0 goes to carry)
    cpu.flags[flags.C] = 1 if (result & 0x01) else 0
    cpu.A = (result >> 1) & 0xFF

    # Set N and Z flags based on result
    # Note: N is always 0 after LSR since bit 7 becomes 0
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 0

    cpu.log.info("i")
