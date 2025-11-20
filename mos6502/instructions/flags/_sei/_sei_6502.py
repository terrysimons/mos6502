#!/usr/bin/env python3
"""SEI instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sei_implied_0x78(cpu: MOS6502CPU) -> None:
    """Execute SEI (Set Interrupt Disable Status) - Implied addressing mode.

    Opcode: 0x78
    Cycles: 2
    Flags: I=1

    VARIANT: 6502 - Standard SEI behavior
    VARIANT: 6502A - Standard SEI behavior
    VARIANT: 6502C - Standard SEI behavior
    VARIANT: 65C02 - Standard SEI behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.I = 1
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
