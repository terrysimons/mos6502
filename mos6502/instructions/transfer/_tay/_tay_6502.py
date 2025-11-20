#!/usr/bin/env python3
"""TAY instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def tay_implied_0xa8(cpu: MOS6502CPU) -> None:
    """Execute TAY (Transfer Accumulator to Index Y) - Implied addressing mode.

    Opcode: 0xA8
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard TAY behavior
    VARIANT: 6502A - Standard TAY behavior
    VARIANT: 6502C - Standard TAY behavior
    VARIANT: 65C02 - Standard TAY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.Y = cpu.A
    cpu.set_load_status_flags(register_name="Y")
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
