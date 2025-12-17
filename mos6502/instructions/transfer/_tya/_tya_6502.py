#!/usr/bin/env python3
"""TYA instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def tya_implied_0x98(cpu: "MOS6502CPU") -> None:
    """Execute TYA (Transfer Index Y to Accumulator) - Implied addressing mode.

    Opcode: 0x98
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard TYA behavior
    VARIANT: 6502A - Standard TYA behavior
    VARIANT: 6502C - Standard TYA behavior
    VARIANT: 65C02 - Standard TYA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.A = cpu.Y
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
