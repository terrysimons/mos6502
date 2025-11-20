#!/usr/bin/env python3
"""SEC instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sec_implied_0x38(cpu: MOS6502CPU) -> None:
    """Execute SEC (Set Carry Flag) - Implied addressing mode.

    Opcode: 0x38
    Cycles: 2
    Flags: C=1

    VARIANT: 6502 - Standard SEC behavior
    VARIANT: 6502A - Standard SEC behavior
    VARIANT: 6502C - Standard SEC behavior
    VARIANT: 65C02 - Standard SEC behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.C = 1
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
