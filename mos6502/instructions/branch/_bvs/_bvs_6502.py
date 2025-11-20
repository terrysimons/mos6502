#!/usr/bin/env python3
"""BVS instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def bvs_relative_0x70(cpu: MOS6502CPU) -> None:
    """Execute BVS (Branch on Overflow Set) - Relative addressing mode.

    Opcode: 0x70
    Cycles: 2 (+1 if branch taken, +1 more if page boundary crossed)
    Flags: None

    VARIANT: 6502 - Standard BVS behavior
    VARIANT: 6502A - Standard BVS behavior
    VARIANT: 6502C - Standard BVS behavior
    VARIANT: 65C02 - Standard BVS behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    offset: int = int(cpu.fetch_byte())

    if offset > 127:
        offset = offset - 256

    if cpu.flags[flags.V] == 1:
        old_pc: int = cpu.PC
        cpu.PC = (cpu.PC + offset) & 0xFFFF

        if (old_pc & 0xFF00) != (cpu.PC & 0xFF00):
            cpu.spend_cpu_cycles(1)

        cpu.spend_cpu_cycles(1)

    cpu.log.info("i")
