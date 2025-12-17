#!/usr/bin/env python3
"""JMP instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU
    from mos6502.memory import Word


def jmp_absolute_0x4c(cpu: "MOS6502CPU") -> None:
    """Execute JMP (Jump to New Location) - Absolute addressing mode.

    Opcode: 0x4C
    Cycles: 3
    Flags: None

    VARIANT: 6502 - Standard JMP absolute behavior
    VARIANT: 6502A - Standard JMP absolute behavior
    VARIANT: 6502C - Standard JMP absolute behavior
    VARIANT: 65C02 - Standard JMP absolute behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502.memory import Word

    jump_address: "Word" = cpu.fetch_word()
    cpu.PC = jump_address
    cpu.log.info("i")
    # No additional cycles - fetch_word already spent 2


def jmp_indirect_0x6c(cpu: "MOS6502CPU") -> None:
    """Execute JMP (Jump to New Location) - Indirect addressing mode.

    Opcode: 0x6C
    Cycles: 5
    Flags: None

    VARIANT: 6502 - Page boundary bug: JMP ($10FF) reads low byte from $10FF
                    and high byte from $1000 (wraps within page, not $1100)
    VARIANT: 6502A - Page boundary bug (same as 6502)
    VARIANT: 6502C - Page boundary bug (same as 6502)
    VARIANT: 65C02 - Bug FIXED: correctly reads across page boundary

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502.memory import Word

    indirect_address: "Word" = cpu.fetch_word()

    # VARIANT: 6502/6502A/6502C - Page boundary bug
    # If indirect_address is 0xXXFF, the 6502 wraps within the page
    # instead of crossing to the next page for the high byte.
    # Example: JMP ($10FF) reads low byte from $10FF and high byte
    # from $1000 (not $1100 as expected).
    # VARIANT: 65C02 - Bug fixed, correctly reads across page boundary

    if (indirect_address & 0xFF) == 0xFF:
        # On page boundary - 6502 has the bug
        low_byte = cpu.read_byte(address=indirect_address)
        # Wrap to start of same page instead of next page
        high_byte = cpu.read_byte(address=indirect_address & 0xFF00)
        jump_address: int = (high_byte << 8) | low_byte
    else:
        # Not on page boundary - all variants behave the same
        jump_address: "Word" = cpu.read_word(address=indirect_address)

    cpu.PC = jump_address
    cpu.log.info("i")
    cpu.spend_cpu_cycles(2)
