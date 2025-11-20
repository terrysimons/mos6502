#!/usr/bin/env python3
"""BRK instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def brk_implied_0x00(cpu: MOS6502CPU) -> None:
    """Execute BRK (Force Break) - Implied addressing mode.

    Opcode: 0x00
    Cycles: 7
    Flags: I is set

    VARIANT: 6502 - D (decimal) flag is NOT cleared by BRK or any interrupt
    VARIANT: 6502A - D (decimal) flag is NOT cleared by BRK or any interrupt
    VARIANT: 6502C - D (decimal) flag is NOT cleared by BRK or any interrupt
    VARIANT: 65C02 - D (decimal) flag IS cleared by BRK and all interrupts

    Note: This 6502 implementation does not clear the D flag (NMOS behavior).
    A 65C02 variant would need to clear the D flag.

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags
    from mos6502.memory import Byte

    # BRK pushes PC+2, then SR (with B flag set), then sets I flag
    # Total: 7 cycles (1 for fetch + 2 for write_word + 1 for write_byte + 3 for overhead)
    # BRK is documented as pushing PC+2, but after fetch_byte(), PC is already +1
    # So we push PC (current value, which is already original PC+1)
    cpu.write_word(address=cpu.S - 1, data=cpu.PC)
    cpu.S -= 2

    # Push status register with B flag set
    # Create a copy of flags with B flag set
    status_with_break: Byte = Byte(cpu._flags.value | (1 << flags.B))
    cpu.write_byte(address=cpu.S, data=status_with_break)
    cpu.S -= 1

    # Set interrupt disable flag
    cpu.I = flags.ProcessorStatusFlags.I[flags.I]

    # Load PC from IRQ vector at 0xFFFE/0xFFFF
    # (In a real system, this would jump to the interrupt handler)
    # For our emulator, we'll raise an exception instead
    # We've spent 4 cycles so far (1 fetch + 2 write_word + 1 write_byte)
    # Need 3 more to total 7
    cpu.spend_cpu_cycles(cost=3)

    cpu.log.info("i")
