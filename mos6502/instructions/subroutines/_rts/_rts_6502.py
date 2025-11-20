#!/usr/bin/env python3
"""RTS instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def rts_implied_0x60(cpu: MOS6502CPU) -> None:
    """Execute RTS (Return from Subroutine) - Implied addressing mode.

    Opcode: 0x60
    Cycles: 6
    Flags: None

    VARIANT: 6502 - Standard RTS behavior
    VARIANT: 6502A - Standard RTS behavior
    VARIANT: 6502C - Standard RTS behavior
    VARIANT: 65C02 - Standard RTS behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.log.info("i")
    cpu.spend_cpu_cycles(cost=1)
    cpu.PC = cpu.read_word(address=cpu.S + 1)
    cpu.S += 2
