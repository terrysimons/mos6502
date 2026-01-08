#!/usr/bin/env python3
"""DEX instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def dex_implied_0xca(cpu: "MOS6502CPU") -> None:
    """Execute DEX (Decrement Index X by One) - Implied addressing mode.

    Opcode: 0xCA
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard DEX behavior
    VARIANT: 6502A - Standard DEX behavior
    VARIANT: 6502C - Standard DEX behavior
    VARIANT: 65C02 - Standard DEX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.X = (cpu.X - 1) & 0xFF
    cpu.set_load_status_flags("X")
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
