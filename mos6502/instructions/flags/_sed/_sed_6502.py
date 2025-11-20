#!/usr/bin/env python3
"""SED instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sed_implied_0xf8(cpu: MOS6502CPU) -> None:
    """Execute SED (Set Decimal Flag) - Implied addressing mode.

    Opcode: 0xF8
    Cycles: 2
    Flags: D=1

    VARIANT: 6502 - Standard SED behavior
    VARIANT: 6502A - Standard SED behavior
    VARIANT: 6502C - Standard SED behavior
    VARIANT: 65C02 - Standard SED behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.D = 1
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
