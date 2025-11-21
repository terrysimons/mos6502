#!/usr/bin/env python3
"""BRK instruction implementation for 65C02 variant."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def brk_implied_0x00(cpu: MOS6502CPU) -> None:
    """Execute BRK (Force Break) - Implied addressing mode - 65C02 variant.

    Opcode: 0x00
    Cycles: 7
    Flags: I is set, D is cleared

    VARIANT: 65C02 - D (decimal) flag IS cleared by BRK and all interrupts

    This is the key difference from NMOS 6502 variants:
    - NMOS (6502/6502A/6502C): D flag is NOT cleared
    - CMOS (65C02): D flag IS cleared

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags
    from mos6502.memory import Byte

    # BRK pushes PC+2, then SR (with B flag set), then sets I flag and clears D flag
    # Total: 7 cycles (1 for fetch + 3 for stack pushes + 3 for IRQ vector read/jump)
    # BRK is a 2-byte instruction (opcode + signature byte)
    # After fetch_byte(), PC points to the signature byte
    # We need to push PC+1 to skip the signature byte (making it PC+2 from original PC)

    # Calculate return address (PC+1 to skip signature byte)
    return_addr = cpu.PC + 1
    pc_high = (return_addr >> 8) & 0xFF
    pc_low = return_addr & 0xFF

    # Push PC high byte first (6502 pushes high byte before low byte)
    cpu.write_byte(address=cpu.S, data=pc_high)
    cpu.S -= 1

    # Push PC low byte
    cpu.write_byte(address=cpu.S, data=pc_low)
    cpu.S -= 1

    # Push status register with B flag set
    # Create a copy of flags with B flag set
    status_with_break: Byte = Byte(cpu._flags.value | (1 << flags.B))
    cpu.write_byte(address=cpu.S, data=status_with_break)
    cpu.S -= 1

    # Set interrupt disable flag
    cpu.I = flags.ProcessorStatusFlags.I[flags.I]

    # 65C02 VARIANT: Clear decimal mode flag
    # This is the key difference from NMOS variants
    cpu.D = 0

    # Load PC from IRQ vector at 0xFFFE/0xFFFF
    # Read the IRQ vector (2 cycles)
    irq_vector = cpu.peek_word(0xFFFE)
    cpu.spend_cpu_cycles(cost=2)

    # Jump to IRQ handler (1 cycle)
    cpu.PC = irq_vector
    cpu.spend_cpu_cycles(cost=1)

    cpu.log.info("i")
