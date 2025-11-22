#!/usr/bin/env python3
"""RTI instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def rti_implied_0x40(cpu: MOS6502CPU) -> None:
    """Execute RTI (Return from Interrupt) - Implied addressing mode.

    Opcode: 0x40
    Cycles: 6
    Flags: All flags restored from stack

    VARIANT: 6502 - Standard RTI behavior
    VARIANT: 6502A - Standard RTI behavior
    VARIANT: 6502C - Standard RTI behavior
    VARIANT: 65C02 - Standard RTI behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502.flags import FlagsRegister

    # Pull status register from stack
    cpu.S += 1
    cpu._flags = FlagsRegister(cpu.read_byte(address=cpu.S))

    # Pull PC from stack
    cpu.S += 1
    return_pc = cpu.read_word(address=cpu.S)
    cpu.PC = return_pc
    cpu.S += 1

    cpu.log.info(f"*** RTI: Returning to ${return_pc:04X}, I flag={'1' if cpu.I else '0'} ***")
    cpu.spend_cpu_cycles(4)
