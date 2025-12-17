#!/usr/bin/env python3
"""BVC instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def bvc_relative_0x50(cpu: "MOS6502CPU") -> None:
    """Execute BVC (Branch on Overflow Clear) - Relative addressing mode.

    Opcode: 0x50
    Cycles: 2 (+1 if branch taken, +1 more if page boundary crossed)
    Flags: None

    VARIANT: 6502 - Standard BVC behavior
    VARIANT: 6502A - Standard BVC behavior
    VARIANT: 6502C - Standard BVC behavior
    VARIANT: 65C02 - Standard BVC behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    offset: int = cpu.fetch_byte()

    if offset > 127:
        offset = offset - 256

    if cpu.flags[flags.V] == 0:
        old_pc: int = cpu.PC
        cpu.PC = (cpu.PC + offset) & 0xFFFF

        if (old_pc & 0xFF00) != (cpu.PC & 0xFF00):
            cpu.spend_cpu_cycles(1)

        cpu.spend_cpu_cycles(1)

    cpu.log.info("i")
