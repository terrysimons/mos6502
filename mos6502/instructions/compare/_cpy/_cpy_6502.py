#!/usr/bin/env python3
"""CPY instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def cpy_immediate_0xc0(cpu: MOS6502CPU) -> None:
    """Execute CPY (Compare Y Register with Memory) - Immediate addressing mode.

    Opcode: 0xC0
    Cycles: 2
    Flags: N Z C

    VARIANT: 6502 - Standard CPY behavior
    VARIANT: 6502A - Standard CPY behavior
    VARIANT: 6502C - Standard CPY behavior
    VARIANT: 65C02 - Standard CPY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    value: int = cpu.fetch_byte()
    result: int = (cpu.Y - value) & 0xFF

    # Set flags based on comparison
    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.Y >= value else 0  # C=1 if Y >= M (no borrow)

    cpu.log.info("i")


def cpy_zeropage_0xc4(cpu: MOS6502CPU) -> None:
    """Execute CPY (Compare Y Register with Memory) - Zeropage addressing mode.

    Opcode: 0xC4
    Cycles: 3
    Flags: N Z C

    VARIANT: 6502 - Standard CPY behavior
    VARIANT: 6502A - Standard CPY behavior
    VARIANT: 6502C - Standard CPY behavior
    VARIANT: 65C02 - Standard CPY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)
    result: int = (cpu.Y - value) & 0xFF

    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.Y >= value else 0

    cpu.log.info("i")


def cpy_absolute_0xcc(cpu: MOS6502CPU) -> None:
    """Execute CPY (Compare Y Register with Memory) - Absolute addressing mode.

    Opcode: 0xCC
    Cycles: 4
    Flags: N Z C

    VARIANT: 6502 - Standard CPY behavior
    VARIANT: 6502A - Standard CPY behavior
    VARIANT: 6502C - Standard CPY behavior
    VARIANT: 65C02 - Standard CPY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)
    result: int = (cpu.Y - value) & 0xFF

    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.Y >= value else 0

    cpu.log.info("i")
