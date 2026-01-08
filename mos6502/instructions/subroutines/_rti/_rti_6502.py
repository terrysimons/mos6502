#!/usr/bin/env python3
"""RTI instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def rti_implied_0x40(cpu: "MOS6502CPU") -> None:
    """Execute RTI (Return from Interrupt) - Implied addressing mode.

    Opcode: 0x40
    Cycles: 6
    Flags: All flags restored from stack

    VARIANT: 6502 - Standard RTI behavior
    VARIANT: 6502A - Standard RTI behavior
    VARIANT: 6502C - Standard RTI behavior
    VARIANT: 65C02 - Standard RTI behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502.flags import FlagsRegister

    # Pull status register from stack
    # S is incremented first, then we read from the new S location.
    # The S setter ensures S stays in page 1 ($0100-$01FF), so cpu.S is always valid.
    cpu.S += 1
    cpu._flags = FlagsRegister(cpu.read_byte(cpu.S))

    # Pull PC from stack (2 bytes: low byte first, then high byte)
    # IMPORTANT: Stack always wraps within page 1 ($0100-$01FF)
    # We must read byte-by-byte to ensure proper wrapping at page boundary
    cpu.S += 1
    pc_low = cpu.read_byte(cpu.S)
    cpu.S += 1
    pc_high = cpu.read_byte(cpu.S)
    return_pc = (pc_high << 8) | pc_low
    cpu.PC = return_pc

    cpu.log.info(f"*** RTI: Returning to ${return_pc:04X}, I flag={'1' if cpu.I else '0'} ***")
    cpu.spend_cpu_cycles(6)
