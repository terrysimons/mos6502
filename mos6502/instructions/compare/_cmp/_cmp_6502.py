#!/usr/bin/env python3
"""CMP instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU
    from mos6502 import flags


def cmp_immediate_0xc9(cpu: MOS6502CPU) -> None:
    """Execute CMP (Compare Accumulator with Memory) - Immediate addressing mode.

    Opcode: 0xC9
    Cycles: 2
    Flags: N Z C

    VARIANT: 6502 - Standard CMP behavior
    VARIANT: 6502A - Standard CMP behavior
    VARIANT: 6502C - Standard CMP behavior
    VARIANT: 65C02 - Standard CMP behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    value: int = int(cpu.fetch_byte())
    result: int = (cpu.A - value) & 0xFF

    # Set flags based on comparison
    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.A >= value else 0  # C=1 if A >= M (no borrow)

    cpu.log.info("i")


def cmp_zeropage_0xc5(cpu: MOS6502CPU) -> None:
    """Execute CMP (Compare Accumulator with Memory) - Zeropage addressing mode.

    Opcode: 0xC5
    Cycles: 3
    Flags: N Z C

    VARIANT: 6502 - Standard CMP behavior
    VARIANT: 6502A - Standard CMP behavior
    VARIANT: 6502C - Standard CMP behavior
    VARIANT: 65C02 - Standard CMP behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = int(cpu.read_byte(address=address))
    result: int = (cpu.A - value) & 0xFF

    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.A >= value else 0

    cpu.log.info("i")


def cmp_zeropage_x_0xd5(cpu: MOS6502CPU) -> None:
    """Execute CMP (Compare Accumulator with Memory) - Zeropage,X addressing mode.

    Opcode: 0xD5
    Cycles: 4
    Flags: N Z C

    VARIANT: 6502 - Standard CMP behavior
    VARIANT: 6502A - Standard CMP behavior
    VARIANT: 6502C - Standard CMP behavior
    VARIANT: 65C02 - Standard CMP behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    value: int = int(cpu.read_byte(address=address))
    result: int = (cpu.A - value) & 0xFF

    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.A >= value else 0

    cpu.log.info("i")


def cmp_absolute_0xcd(cpu: MOS6502CPU) -> None:
    """Execute CMP (Compare Accumulator with Memory) - Absolute addressing mode.

    Opcode: 0xCD
    Cycles: 4
    Flags: N Z C

    VARIANT: 6502 - Standard CMP behavior
    VARIANT: 6502A - Standard CMP behavior
    VARIANT: 6502C - Standard CMP behavior
    VARIANT: 65C02 - Standard CMP behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = int(cpu.read_byte(address=address))
    result: int = (cpu.A - value) & 0xFF

    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.A >= value else 0

    cpu.log.info("i")


def cmp_absolute_x_0xdd(cpu: MOS6502CPU) -> None:
    """Execute CMP (Compare Accumulator with Memory) - Absolute,X addressing mode.

    Opcode: 0xDD
    Cycles: 4*
    Flags: N Z C

    VARIANT: 6502 - Standard CMP behavior
    VARIANT: 6502A - Standard CMP behavior
    VARIANT: 6502C - Standard CMP behavior
    VARIANT: 65C02 - Standard CMP behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    value: int = int(cpu.read_byte(address=address))
    result: int = (cpu.A - value) & 0xFF

    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.A >= value else 0

    cpu.log.info("i")


def cmp_absolute_y_0xd9(cpu: MOS6502CPU) -> None:
    """Execute CMP (Compare Accumulator with Memory) - Absolute,Y addressing mode.

    Opcode: 0xD9
    Cycles: 4*
    Flags: N Z C

    VARIANT: 6502 - Standard CMP behavior
    VARIANT: 6502A - Standard CMP behavior
    VARIANT: 6502C - Standard CMP behavior
    VARIANT: 65C02 - Standard CMP behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="Y")
    value: int = int(cpu.read_byte(address=address))
    result: int = (cpu.A - value) & 0xFF

    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.A >= value else 0

    cpu.log.info("i")


def cmp_indexed_indirect_x_0xc1(cpu: MOS6502CPU) -> None:
    """Execute CMP (Compare Accumulator with Memory) - (Indirect,X) addressing mode.

    Opcode: 0xC1
    Cycles: 6
    Flags: N Z C

    VARIANT: 6502 - Standard CMP behavior
    VARIANT: 6502A - Standard CMP behavior
    VARIANT: 6502C - Standard CMP behavior
    VARIANT: 65C02 - Standard CMP behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_indexed_indirect_mode_address()
    value: int = int(cpu.read_byte(address=address))
    result: int = (cpu.A - value) & 0xFF

    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.A >= value else 0

    cpu.log.info("i")


def cmp_indirect_indexed_y_0xd1(cpu: MOS6502CPU) -> None:
    """Execute CMP (Compare Accumulator with Memory) - (Indirect),Y addressing mode.

    Opcode: 0xD1
    Cycles: 5*
    Flags: N Z C

    VARIANT: 6502 - Standard CMP behavior
    VARIANT: 6502A - Standard CMP behavior
    VARIANT: 6502C - Standard CMP behavior
    VARIANT: 65C02 - Standard CMP behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_indirect_indexed_mode_address()
    value: int = int(cpu.read_byte(address=address))
    result: int = (cpu.A - value) & 0xFF

    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.A >= value else 0

    cpu.log.info("i")
