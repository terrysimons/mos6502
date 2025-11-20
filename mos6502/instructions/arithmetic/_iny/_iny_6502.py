#!/usr/bin/env python3
"""INY instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def iny_implied_0xc8(cpu: MOS6502CPU) -> None:
    """Execute INY (Increment Index Y by One) - Implied addressing mode.

    Opcode: 0xC8
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard INY behavior
    VARIANT: 6502A - Standard INY behavior
    VARIANT: 6502C - Standard INY behavior
    VARIANT: 65C02 - Standard INY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.Y = (cpu.Y + 1) & 0xFF
    cpu.set_load_status_flags(register_name="Y")
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
