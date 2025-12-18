#!/usr/bin/env python3
"""PHP instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU
    from mos6502.memory import Byte


def php_implied_0x08(cpu: "MOS6502CPU") -> None:
    """Execute PHP (Push Processor Status on Stack) - Implied addressing mode.

    Opcode: 0x08
    Cycles: 3
    Flags: None

    VARIANT: 6502 - Pushes P with B flag set (bits 4 and 5 set)
    VARIANT: 6502A - Pushes P with B flag set (bits 4 and 5 set)
    VARIANT: 6502C - Pushes P with B flag set (bits 4 and 5 set)
    VARIANT: 65C02 - Pushes P with B flag set (bits 4 and 5 set, same as NMOS)

    Note: The B flag (bits 4 and 5) are set when pushing to stack, but don't
    exist as actual flags in the processor status register.

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502.memory import Byte

    # Push processor status with B flag set
    status_with_b: "Byte" = Byte(cpu.flags.value | 0b00110000)
    cpu.write_byte(cpu.S, status_with_b)
    cpu.S -= 1
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
