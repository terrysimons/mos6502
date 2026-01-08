#!/usr/bin/env python3
"""JMP instruction implementation for 65C02 variant."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU
    from mos6502.memory import Word


def jmp_absolute_0x4c(cpu: "MOS6502CPU") -> None:
    """Execute JMP (Jump to New Location) - Absolute addressing mode.

    Opcode: 0x4C
    Cycles: 3
    Flags: None

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
    """Execute JMP (Jump to New Location) - Indirect addressing mode - 65C02 variant.

    Opcode: 0x6C
    Cycles: 5
    Flags: None

    VARIANT: 6502 - Page boundary bug: JMP ($10FF) reads low byte from $10FF
                    and high byte from $1000 (wraps within page, not $1100)
    VARIANT: 6502A - Page boundary bug (same as 6502)
    VARIANT: 6502C - Page boundary bug (same as 6502)
    VARIANT: 65C02 - Bug FIXED: correctly reads across page boundary

    This 65C02 implementation fixes the page boundary bug. When the indirect
    address is on a page boundary (0xXXFF), it correctly reads the high byte
    from the next page (0xXX+1,00) instead of wrapping within the same page.

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502.memory import Word

    indirect_address: "Word" = cpu.fetch_word()

    # VARIANT: 65C02 - Bug fixed, always correctly reads across page boundary
    # No special handling needed - just read the word normally
    jump_address: "Word" = cpu.read_word(indirect_address)

    cpu.PC = jump_address
    cpu.log.info("i")
    cpu.spend_cpu_cycles(2)
