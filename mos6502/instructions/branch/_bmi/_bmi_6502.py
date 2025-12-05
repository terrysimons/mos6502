#!/usr/bin/env python3
"""BMI instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def bmi_relative_0x30(cpu: MOS6502CPU) -> None:
    """Execute BMI (Branch on Minus/Negative) - Relative addressing mode.

    Opcode: 0x30
    Cycles: 2 (+1 if branch taken, +1 more if page boundary crossed)
    Flags: None

    VARIANT: 6502 - Standard BMI behavior
    VARIANT: 6502A - Standard BMI behavior
    VARIANT: 6502C - Standard BMI behavior
    VARIANT: 65C02 - Standard BMI behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    offset: int = cpu.fetch_byte()

    if offset > 127:
        offset = offset - 256

    if cpu.flags[flags.N] == 1:
        old_pc: int = cpu.PC
        cpu.PC = (cpu.PC + offset) & 0xFFFF

        if (old_pc & 0xFF00) != (cpu.PC & 0xFF00):
            cpu.spend_cpu_cycles(1)

        cpu.spend_cpu_cycles(1)

    cpu.log.info("i")
