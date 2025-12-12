#!/usr/bin/env python3
"""ANE (XAA) instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

On 65C02, the ANE opcode acts as a 2-byte, 2-cycle NOP.

VARIANT: 65C02 - Acts as NOP (no registers or flags modified)

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def ane_immediate_0x8b(cpu: MOS6502CPU) -> None:
    """Execute ANE (XAA) - Immediate addressing mode - 65C02 variant.

    Opcode: 0x8B
    Cycles: 2
    Bytes: 2
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch operand to advance PC, but don't use it
    cpu.fetch_byte()
    cpu.log.info("i")
