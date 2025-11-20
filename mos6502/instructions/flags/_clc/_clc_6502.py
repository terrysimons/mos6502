#!/usr/bin/env python3
"""CLC instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def clc_implied_0x18(cpu: MOS6502CPU) -> None:
    """Execute CLC (Clear Carry Flag) - Implied addressing mode.

    Opcode: 0x18
    Cycles: 2
    Flags: C=0

    VARIANT: 6502 - Standard CLC behavior
    VARIANT: 6502A - Standard CLC behavior
    VARIANT: 6502C - Standard CLC behavior
    VARIANT: 65C02 - Standard CLC behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.C = 0
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
