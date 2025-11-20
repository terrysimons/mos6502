#!/usr/bin/env python3
"""RTS instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def rts_implied_0x60(cpu: MOS6502CPU) -> None:
    """Execute RTS (Return from Subroutine) - Implied addressing mode.

    Opcode: 0x60
    Cycles: 6
    Flags: None

    VARIANT: 6502 - Standard RTS behavior
    VARIANT: 6502A - Standard RTS behavior
    VARIANT: 6502C - Standard RTS behavior
    VARIANT: 65C02 - Standard RTS behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.log.info("i")
    # RTS takes 6 cycles total:
    # 1. Opcode fetch (already done by execute())
    # 2. Read and increment stack pointer (1 cycle)
    cpu.spend_cpu_cycles(cost=1)
    # 3-4. Read return address from stack (2 cycles, done by read_word())
    # RTS pops the return address minus 1 from the stack and adds 1 to get the actual return address
    # JSR pushes PC-1, so RTS must add 1 back
    return_address = cpu.read_word(address=cpu.S + 1) + 1
    cpu.S += 2
    # 5. Increment PC (1 cycle)
    cpu.spend_cpu_cycles(cost=1)
    # 6. Final PC increment (1 cycle)
    cpu.spend_cpu_cycles(cost=1)
    cpu.PC = return_address
