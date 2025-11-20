#!/usr/bin/env python3
"""BPL instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def bpl_relative_0x10(cpu: MOS6502CPU) -> None:
    """Execute BPL (Branch on Plus/Positive) - Relative addressing mode.

    Opcode: 0x10
    Cycles: 2 (+1 if branch taken, +1 more if page boundary crossed)
    Flags: None

    VARIANT: 6502 - Standard BPL behavior
    VARIANT: 6502A - Standard BPL behavior
    VARIANT: 6502C - Standard BPL behavior
    VARIANT: 65C02 - Standard BPL behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    offset: int = int(cpu.fetch_byte())

    if offset > 127:
        offset = offset - 256

    if cpu.flags[flags.N] == 0:
        old_pc: int = cpu.PC
        cpu.PC = (cpu.PC + offset) & 0xFFFF

        if (old_pc & 0xFF00) != (cpu.PC & 0xFF00):
            cpu.spend_cpu_cycles(1)

        cpu.spend_cpu_cycles(1)

    cpu.log.info("i")
