#!/usr/bin/env python3
"""STX instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def stx_zeropage_0x86(cpu: MOS6502CPU) -> None:
    """Execute STX (Store X Register in Memory) - Zeropage addressing mode.

    Opcode: 0x86
    Cycles: 3
    Flags: None

    VARIANT: 6502 - Standard STX behavior
    VARIANT: 6502A - Standard STX behavior
    VARIANT: 6502C - Standard STX behavior
    VARIANT: 65C02 - Standard STX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    cpu.write_byte(address=address, data=cpu.X)
    cpu.log.info("i")


def stx_zeropage_y_0x96(cpu: MOS6502CPU) -> None:
    """Execute STX (Store X Register in Memory) - Zeropage,Y addressing mode.

    Opcode: 0x96
    Cycles: 4
    Flags: None

    VARIANT: 6502 - Standard STX behavior
    VARIANT: 6502A - Standard STX behavior
    VARIANT: 6502C - Standard STX behavior
    VARIANT: 65C02 - Standard STX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="Y")
    cpu.write_byte(address=address, data=cpu.X)
    cpu.log.info("i")


def stx_absolute_0x8e(cpu: MOS6502CPU) -> None:
    """Execute STX (Store X Register in Memory) - Absolute addressing mode.

    Opcode: 0x8E
    Cycles: 4
    Flags: None

    VARIANT: 6502 - Standard STX behavior
    VARIANT: 6502A - Standard STX behavior
    VARIANT: 6502C - Standard STX behavior
    VARIANT: 65C02 - Standard STX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    cpu.write_byte(address=address & 0xFFFF, data=cpu.X)
    cpu.log.info("i")
