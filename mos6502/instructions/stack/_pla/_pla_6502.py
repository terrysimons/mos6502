#!/usr/bin/env python3
"""PLA instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def pla_implied_0x68(cpu: "MOS6502CPU") -> None:
    """Execute PLA (Pull Accumulator from Stack) - Implied addressing mode.

    Opcode: 0x68
    Cycles: 4
    Flags: N Z

    VARIANT: 6502 - Standard PLA behavior
    VARIANT: 6502A - Standard PLA behavior
    VARIANT: 6502C - Standard PLA behavior
    VARIANT: 65C02 - Standard PLA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.S += 1
    cpu.A = cpu.read_byte(cpu.S)
    cpu.set_load_status_flags("A")
    cpu.log.info("i")
    cpu.spend_cpu_cycles(2)
