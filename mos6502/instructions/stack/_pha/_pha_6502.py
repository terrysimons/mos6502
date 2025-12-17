#!/usr/bin/env python3
"""PHA instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def pha_implied_0x48(cpu: "MOS6502CPU") -> None:
    """Execute PHA (Push Accumulator on Stack) - Implied addressing mode.

    Opcode: 0x48
    Cycles: 3
    Flags: None

    VARIANT: 6502 - Standard PHA behavior
    VARIANT: 6502A - Standard PHA behavior
    VARIANT: 6502C - Standard PHA behavior
    VARIANT: 65C02 - Standard PHA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.write_byte(address=cpu.S, data=cpu.A)
    cpu.S -= 1
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
