#!/usr/bin/env python3
"""BIT instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


# Bit masks for testing specific bits
BYTE_BIT_7_MASK = 0b10000000
BYTE_BIT_6_MASK = 0b01000000


def bit_zeropage_0x24(cpu: MOS6502CPU) -> None:
    """Execute BIT (Test Bits in Memory with Accumulator) - Zeropage addressing mode.

    Opcode: 0x24
    Cycles: 3
    Flags: N Z V

    VARIANT: 6502 - Standard BIT behavior
    VARIANT: 6502A - Standard BIT behavior
    VARIANT: 6502C - Standard BIT behavior
    VARIANT: 65C02 - Standard BIT behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Bit Test - AND A with memory, set flags but don't store result
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)

    # Z flag set based on A AND memory
    result: int = cpu.A & value
    cpu.flags[flags.Z] = 1 if result == 0 else 0

    # N flag = bit 7 of memory
    cpu.flags[flags.N] = 1 if (value & BYTE_BIT_7_MASK) else 0

    # V flag = bit 6 of memory
    cpu.flags[flags.V] = 1 if (value & BYTE_BIT_6_MASK) else 0

    cpu.log.info("i")


def bit_absolute_0x2c(cpu: MOS6502CPU) -> None:
    """Execute BIT (Test Bits in Memory with Accumulator) - Absolute addressing mode.

    Opcode: 0x2C
    Cycles: 4
    Flags: N Z V

    VARIANT: 6502 - Standard BIT behavior
    VARIANT: 6502A - Standard BIT behavior
    VARIANT: 6502C - Standard BIT behavior
    VARIANT: 65C02 - Standard BIT behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Bit Test - AND A with memory, set flags but don't store result
    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)

    # Z flag set based on A AND memory
    result: int = cpu.A & value
    cpu.flags[flags.Z] = 1 if result == 0 else 0

    # N flag = bit 7 of memory
    cpu.flags[flags.N] = 1 if (value & BYTE_BIT_7_MASK) else 0

    # V flag = bit 6 of memory
    cpu.flags[flags.V] = 1 if (value & BYTE_BIT_6_MASK) else 0

    cpu.log.info("i")
