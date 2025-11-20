#!/usr/bin/env python3
"""CLV instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def clv_implied_0xb8(cpu: MOS6502CPU) -> None:
    """Execute CLV (Clear Overflow Flag) - Implied addressing mode.

    Opcode: 0xB8
    Cycles: 2
    Flags: V=0

    VARIANT: 6502 - Standard CLV behavior
    VARIANT: 6502A - Standard CLV behavior
    VARIANT: 6502C - Standard CLV behavior
    VARIANT: 65C02 - Standard CLV behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.V = 0
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
