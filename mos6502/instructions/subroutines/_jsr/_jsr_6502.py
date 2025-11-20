#!/usr/bin/env python3
"""JSR instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def jsr_absolute_0x20(cpu: MOS6502CPU) -> None:
    """Execute JSR (Jump to New Location Saving Return Address) - Absolute addressing mode.

    Opcode: 0x20
    Cycles: 6
    Flags: None

    VARIANT: 6502 - Standard JSR behavior
    VARIANT: 6502A - Standard JSR behavior
    VARIANT: 6502C - Standard JSR behavior
    VARIANT: 65C02 - Standard JSR behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502.memory import Word

    subroutine_address: Word = cpu.fetch_word()

    # The stack is top-down, so starts at 0x1FF, so we need to
    # write to S - 1
    # JSR pushes the return address minus 1 (PC-1) to the stack
    # After fetch_word(), PC points to the byte after the JSR instruction
    # So we push PC-1, which is the address of the last byte of the JSR instruction
    cpu.write_word(address=cpu.S - 1, data=cpu.PC - 1)

    # Since we wrote a word, we need to decrement by 2
    # so our stack pointer would be 0xFD if it started at 0xFF here
    cpu.S -= 2
    cpu.PC = subroutine_address
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
