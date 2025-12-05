#!/usr/bin/env python3
"""BCC instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def bcc_relative_0x90(cpu: MOS6502CPU) -> None:
    """Execute BCC (Branch on Carry Clear) - Relative addressing mode.

    Opcode: 0x90
    Cycles: 2 (+1 if branch taken, +1 more if page boundary crossed)
    Flags: None

    VARIANT: 6502 - Standard BCC behavior
    VARIANT: 6502A - Standard BCC behavior
    VARIANT: 6502C - Standard BCC behavior
    VARIANT: 65C02 - Standard BCC behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Branch on Carry Clear (C = 0)
    offset: int = cpu.fetch_byte()  # Signed byte offset

    # Convert to signed byte (-128 to +127)
    if offset > 127:
        offset = offset - 256

    if cpu.flags[flags.C] == 0:
        # Branch taken
        old_pc: int = cpu.PC
        cpu.PC = (cpu.PC + offset) & 0xFFFF

        # Check for page boundary crossing (adds 1 cycle)
        if (old_pc & 0xFF00) != (cpu.PC & 0xFF00):
            cpu.spend_cpu_cycles(1)

        cpu.spend_cpu_cycles(1)

    cpu.log.info("i")
