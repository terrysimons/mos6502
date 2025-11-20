#!/usr/bin/env python3
"""SBX instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

On 65C02, the SBX opcode acts as a NOP with the same cycle count as the
NMOS implementation, but without modifying any registers or flags.

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
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers or flags modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.fetch_byte()
    cpu.log.info("i")
