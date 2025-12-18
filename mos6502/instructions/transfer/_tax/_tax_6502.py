#!/usr/bin/env python3
"""TAX instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def tax_implied_0xaa(cpu: "MOS6502CPU") -> None:
    """Execute TAX (Transfer Accumulator to Index X) - Implied addressing mode.

    Opcode: 0xAA
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard TAX behavior
    VARIANT: 6502A - Standard TAX behavior
    VARIANT: 6502C - Standard TAX behavior
    VARIANT: 65C02 - Standard TAX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.X = cpu.A
    cpu.set_load_status_flags("X")
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
