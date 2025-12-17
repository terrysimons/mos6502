#!/usr/bin/env python3
"""NOP instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def nop_implied_0xea(cpu: "MOS6502CPU") -> None:
    """Execute NOP (No Operation) - Implied addressing mode.

    Opcode: 0xEA
    Cycles: 2
    Flags: None affected

    VARIANT: 6502 - Standard NOP behavior
    VARIANT: 6502A - Standard NOP behavior
    VARIANT: 6502C - Standard NOP behavior
    VARIANT: 65C02 - Standard NOP behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.log.info("i")
    cpu.spend_cpu_cycles(cost=1)
