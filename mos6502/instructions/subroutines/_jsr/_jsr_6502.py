#!/usr/bin/env python3
"""JSR instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def jsr_absolute_0x20(cpu: "MOS6502CPU") -> None:
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

    # JSR pushes the return address minus 1 (PC-1) to the stack
    # After fetch_word(), PC points to the byte after the JSR instruction
    # So we push PC-1, which is the address of the last byte of the JSR instruction
    #
    # IMPORTANT: Stack always wraps within page 1 ($0100-$01FF)
    # We must write byte-by-byte to ensure proper wrapping at page boundary
    # Push high byte first (6502 is little-endian, stack grows down)
    return_addr = cpu.PC - 1
    pc_high = (return_addr >> 8) & 0xFF
    pc_low = return_addr & 0xFF

    # Push high byte first, then low byte
    cpu.write_byte(address=cpu.S, data=pc_high)
    cpu.S -= 1
    cpu.write_byte(address=cpu.S, data=pc_low)
    cpu.S -= 1
    cpu.PC = subroutine_address
    cpu.log.info("i")
    cpu.spend_cpu_cycles(1)
