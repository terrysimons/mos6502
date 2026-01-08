#!/usr/bin/env python3
"""TSX instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def tsx_implied_0xba(cpu: "MOS6502CPU") -> None:
    """Execute TSX (Transfer Stack Pointer to Index X) - Implied addressing mode.

    Opcode: 0xBA
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard TSX behavior
    VARIANT: 6502A - Standard TSX behavior
    VARIANT: 6502C - Standard TSX behavior
    VARIANT: 65C02 - Standard TSX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.X = cpu.S & 0xFF
    cpu.set_load_status_flags("X")
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
