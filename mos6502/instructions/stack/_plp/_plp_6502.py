#!/usr/bin/env python3
"""PLP instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def plp_implied_0x28(cpu: MOS6502CPU) -> None:
    """Execute PLP (Pull Processor Status from Stack) - Implied addressing mode.

    Opcode: 0x28
    Cycles: 4
    Flags: All flags restored from stack

    VARIANT: 6502 - Standard PLP behavior
    VARIANT: 6502A - Standard PLP behavior
    VARIANT: 6502C - Standard PLP behavior
    VARIANT: 65C02 - Standard PLP behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502.memory import Byte

    cpu.S += 1
    status_byte: int = cpu.read_byte(address=cpu.S)
    # Restore all flags from stack by replacing the entire Byte
    cpu._flags = Byte(status_byte)
    cpu.log.info("i")
    cpu.spend_cpu_cycles(2)
