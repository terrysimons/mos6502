#!/usr/bin/env python3
"""LAS instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

On 65C02, the LAS opcode acts as a NOP.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#LAS
  - http://www.oxyron.de/html/opcodes02.html
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def las_absolute_y_0xbb(cpu: MOS6502CPU) -> None:
    """Execute LAS (Load A, X, and S) - Absolute,Y addressing mode.

    Opcode: 0xBB
    Cycles: 4*
    Bytes: 3
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers or flags modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.fetch_byte()
    cpu.fetch_byte()
    cpu.log.info("i")
