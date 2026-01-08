#!/usr/bin/env python3
"""STY instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sty_zeropage_0x84(cpu: "MOS6502CPU") -> None:
    """Execute STY (Store Y Register in Memory) - Zeropage addressing mode.

    Opcode: 0x84
    Cycles: 3
    Flags: None

    VARIANT: 6502 - Standard STY behavior
    VARIANT: 6502A - Standard STY behavior
    VARIANT: 6502C - Standard STY behavior
    VARIANT: 65C02 - Standard STY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address(None)
    cpu.write_byte(address, cpu.Y)
    cpu.log.info("i")


def sty_zeropage_x_0x94(cpu: "MOS6502CPU") -> None:
    """Execute STY (Store Y Register in Memory) - Zeropage,X addressing mode.

    Opcode: 0x94
    Cycles: 4
    Flags: None

    VARIANT: 6502 - Standard STY behavior
    VARIANT: 6502A - Standard STY behavior
    VARIANT: 6502C - Standard STY behavior
    VARIANT: 65C02 - Standard STY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address("X")
    cpu.write_byte(address, cpu.Y)
    cpu.log.info("i")


def sty_absolute_0x8c(cpu: "MOS6502CPU") -> None:
    """Execute STY (Store Y Register in Memory) - Absolute addressing mode.

    Opcode: 0x8C
    Cycles: 4
    Flags: None

    VARIANT: 6502 - Standard STY behavior
    VARIANT: 6502A - Standard STY behavior
    VARIANT: 6502C - Standard STY behavior
    VARIANT: 65C02 - Standard STY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(None)
    cpu.write_byte(address & 0xFFFF, cpu.Y)
    cpu.log.info("i")
