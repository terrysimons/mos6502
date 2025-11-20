#!/usr/bin/env python3
"""TXS instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def txs_implied_0x9a(cpu: MOS6502CPU) -> None:
    """Execute TXS (Transfer Index X to Stack Pointer) - Implied addressing mode.

    Opcode: 0x9A
    Cycles: 2
    Flags: None

    VARIANT: 6502 - Standard TXS behavior
    VARIANT: 6502A - Standard TXS behavior
    VARIANT: 6502C - Standard TXS behavior
    VARIANT: 65C02 - Standard TXS behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.S = 0x100 | cpu.X
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
