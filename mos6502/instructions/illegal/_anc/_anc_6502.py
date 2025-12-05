#!/usr/bin/env python3
"""ANC instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - NMOS only

ANC (AND with Carry) performs a bitwise AND with an immediate value, then
sets the carry flag to match the negative flag (bit 7 of the result).

References:
  - https://masswerk.at/6502/6502_instruction_set.html#ANC
  - http://www.oxyron.de/html/opcodes02.html
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def anc_immediate_0x0b(cpu: MOS6502CPU) -> None:
    """Execute ANC (AND with Carry) - Immediate addressing mode.

    Opcode: 0x0B
    Cycles: 2
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - ANDs with A, sets C to bit 7 of result
    VARIANT: 6502A - ANDs with A, sets C to bit 7 of result
    VARIANT: 6502C - ANDs with A, sets C to bit 7 of result
    VARIANT: 65C02 - Acts as NOP (see _anc_65c02.py)

    Operation: A = A & immediate, C = N

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    value: int = cpu.fetch_byte()

    # AND with accumulator
    cpu.A = int(cpu.A) & value

    # Set N and Z flags based on result
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    # Set C flag to match N flag (bit 7 of result)
    cpu.flags[flags.C] = cpu.flags[flags.N]

    cpu.log.info("i")


def anc_immediate_0x2b(cpu: MOS6502CPU) -> None:
    """Execute ANC (AND with Carry) - Immediate addressing mode (duplicate).

    Opcode: 0x2B
    Cycles: 2
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - ANDs with A, sets C to bit 7 of result
    VARIANT: 6502A - ANDs with A, sets C to bit 7 of result
    VARIANT: 6502C - ANDs with A, sets C to bit 7 of result
    VARIANT: 65C02 - Acts as NOP (see _anc_65c02.py)

    Operation: A = A & immediate, C = N

    Note: This is a duplicate opcode that performs the same operation as 0x0B

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    value: int = cpu.fetch_byte()

    cpu.A = int(cpu.A) & value

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0
    cpu.flags[flags.C] = cpu.flags[flags.N]

    cpu.log.info("i")
