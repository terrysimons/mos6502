#!/usr/bin/env python3
"""TXA instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def txa_implied_0x8a(cpu: MOS6502CPU) -> None:
    """Execute TXA (Transfer Index X to Accumulator) - Implied addressing mode.

    Opcode: 0x8A
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard TXA behavior
    VARIANT: 6502A - Standard TXA behavior
    VARIANT: 6502C - Standard TXA behavior
    VARIANT: 65C02 - Standard TXA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.A = cpu.X
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
