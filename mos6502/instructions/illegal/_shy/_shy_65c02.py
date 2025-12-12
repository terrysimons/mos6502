#!/usr/bin/env python3
"""SHY (SYA, SAY) instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

VARIANT: 65C02 - Acts as NOP

References:
  - http://www.oxyron.de/html/opcodes02.html
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def shy_absolute_x_0x9c(cpu: MOS6502CPU) -> None:
    """Execute SHY (SYA) - Absolute X addressing mode - 65C02 variant.

    Opcode: 0x9C
    Cycles: 5
    Bytes: 3
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch operands to advance PC
    cpu.fetch_byte()
    cpu.fetch_byte()
    cpu.log.info("i")
