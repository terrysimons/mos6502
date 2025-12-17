#!/usr/bin/env python3
"""CLI instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def cli_implied_0x58(cpu: "MOS6502CPU") -> None:
    """Execute CLI (Clear Interrupt Disable Bit) - Implied addressing mode.

    Opcode: 0x58
    Cycles: 2
    Flags: I=0

    VARIANT: 6502 - Standard CLI behavior
    VARIANT: 6502A - Standard CLI behavior
    VARIANT: 6502C - Standard CLI behavior
    VARIANT: 65C02 - Standard CLI behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.I = 0
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
