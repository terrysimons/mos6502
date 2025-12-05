#!/usr/bin/env python3
"""SBX instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - NMOS only

SBX (Subtract from X) computes (A & X) - immediate and stores the result in X.
It sets the carry flag as if performing a compare operation.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#SBX
  - http://www.oxyron.de/html/opcodes02.html
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sbx_immediate_0xcb(cpu: MOS6502CPU) -> None:
    """Execute SBX (Subtract from X) - Immediate addressing mode.

    Opcode: 0xCB
    Cycles: 2
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Computes (A & X) - immediate, stores in X
    VARIANT: 6502A - Computes (A & X) - immediate, stores in X
    VARIANT: 6502C - Computes (A & X) - immediate, stores in X
    VARIANT: 65C02 - Acts as NOP (see _sbx_65c02.py)

    Operation: X = (A & X) - immediate

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    value: int = cpu.fetch_byte()

    # Compute (A & X)
    temp: int = int(cpu.A) & int(cpu.X)

    # Subtract immediate value (no borrow)
    result: int = temp - value

    # Set carry flag if no borrow (result >= 0)
    cpu.flags[flags.C] = 1 if result >= 0 else 0

    # Store result in X (masked to 8 bits)
    cpu.X = result & 0xFF

    # Set N and Z flags based on result
    cpu.flags[flags.Z] = 1 if cpu.X == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.X & 0x80) else 0

    cpu.log.info("i")
