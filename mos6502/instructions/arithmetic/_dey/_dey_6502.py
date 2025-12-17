#!/usr/bin/env python3
"""DEY instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def dey_implied_0x88(cpu: "MOS6502CPU") -> None:
    """Execute DEY (Decrement Index Y by One) - Implied addressing mode.

    Opcode: 0x88
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard DEY behavior
    VARIANT: 6502A - Standard DEY behavior
    VARIANT: 6502C - Standard DEY behavior
    VARIANT: 65C02 - Standard DEY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.Y = (cpu.Y - 1) & 0xFF
    cpu.set_load_status_flags(register_name="Y")
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
