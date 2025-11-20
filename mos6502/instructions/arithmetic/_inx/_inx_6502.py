#!/usr/bin/env python3
"""INX instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def inx_implied_0xe8(cpu: MOS6502CPU) -> None:
    """Execute INX (Increment Index X by One) - Implied addressing mode.

    Opcode: 0xE8
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard INX behavior
    VARIANT: 6502A - Standard INX behavior
    VARIANT: 6502C - Standard INX behavior
    VARIANT: 65C02 - Standard INX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.X = (cpu.X + 1) & 0xFF
    cpu.set_load_status_flags(register_name="X")
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
