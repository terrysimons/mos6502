#!/usr/bin/env python3
"""CLD instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def cld_implied_0xd8(cpu: "MOS6502CPU") -> None:
    """Execute CLD (Clear Decimal Mode) - Implied addressing mode.

    Opcode: 0xD8
    Cycles: 2
    Flags: D=0

    VARIANT: 6502 - Standard CLD behavior
    VARIANT: 6502A - Standard CLD behavior
    VARIANT: 6502C - Standard CLD behavior
    VARIANT: 65C02 - Standard CLD behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.D = 0
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
