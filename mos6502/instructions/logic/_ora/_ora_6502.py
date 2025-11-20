#!/usr/bin/env python3
"""ORA instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def ora_immediate_0x09(cpu: MOS6502CPU) -> None:
    """Execute ORA (Bitwise OR with Accumulator) - Immediate addressing mode.

    Opcode: 0x09
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard ORA behavior
    VARIANT: 6502A - Standard ORA behavior
    VARIANT: 6502C - Standard ORA behavior
    VARIANT: 65C02 - Standard ORA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    value: int = int(cpu.fetch_byte())
    cpu.A = cpu.A | value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def ora_zeropage_0x05(cpu: MOS6502CPU) -> None:
    """Execute ORA (Bitwise OR with Accumulator) - Zeropage addressing mode.

    Opcode: 0x05
    Cycles: 3
    Flags: N Z

    VARIANT: 6502 - Standard ORA behavior
    VARIANT: 6502A - Standard ORA behavior
    VARIANT: 6502C - Standard ORA behavior
    VARIANT: 65C02 - Standard ORA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = int(cpu.read_byte(address=address))
    cpu.A = cpu.A | value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def ora_zeropage_x_0x15(cpu: MOS6502CPU) -> None:
    """Execute ORA (Bitwise OR with Accumulator) - Zeropage,X addressing mode.

    Opcode: 0x15
    Cycles: 4
    Flags: N Z

    VARIANT: 6502 - Standard ORA behavior
    VARIANT: 6502A - Standard ORA behavior
    VARIANT: 6502C - Standard ORA behavior
    VARIANT: 65C02 - Standard ORA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    value: int = int(cpu.read_byte(address=address))
    cpu.A = cpu.A | value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def ora_absolute_0x0d(cpu: MOS6502CPU) -> None:
    """Execute ORA (Bitwise OR with Accumulator) - Absolute addressing mode.

    Opcode: 0x0D
    Cycles: 4
    Flags: N Z

    VARIANT: 6502 - Standard ORA behavior
    VARIANT: 6502A - Standard ORA behavior
    VARIANT: 6502C - Standard ORA behavior
    VARIANT: 65C02 - Standard ORA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = int(cpu.read_byte(address=address))
    cpu.A = cpu.A | value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def ora_absolute_x_0x1d(cpu: MOS6502CPU) -> None:
    """Execute ORA (Bitwise OR with Accumulator) - Absolute,X addressing mode.

    Opcode: 0x1D
    Cycles: 4*
    Flags: N Z

    VARIANT: 6502 - Standard ORA behavior
    VARIANT: 6502A - Standard ORA behavior
    VARIANT: 6502C - Standard ORA behavior
    VARIANT: 65C02 - Standard ORA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    value: int = int(cpu.read_byte(address=address))
    cpu.A = cpu.A | value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def ora_absolute_y_0x19(cpu: MOS6502CPU) -> None:
    """Execute ORA (Bitwise OR with Accumulator) - Absolute,Y addressing mode.

    Opcode: 0x19
    Cycles: 4*
    Flags: N Z

    VARIANT: 6502 - Standard ORA behavior
    VARIANT: 6502A - Standard ORA behavior
    VARIANT: 6502C - Standard ORA behavior
    VARIANT: 65C02 - Standard ORA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="Y")
    value: int = int(cpu.read_byte(address=address))
    cpu.A = cpu.A | value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def ora_indexed_indirect_x_0x01(cpu: MOS6502CPU) -> None:
    """Execute ORA (Bitwise OR with Accumulator) - (Indirect,X) addressing mode.

    Opcode: 0x01
    Cycles: 6
    Flags: N Z

    VARIANT: 6502 - Standard ORA behavior
    VARIANT: 6502A - Standard ORA behavior
    VARIANT: 6502C - Standard ORA behavior
    VARIANT: 65C02 - Standard ORA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_indexed_indirect_mode_address()
    value: int = int(cpu.read_byte(address=address))
    cpu.A = cpu.A | value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def ora_indirect_indexed_y_0x11(cpu: MOS6502CPU) -> None:
    """Execute ORA (Bitwise OR with Accumulator) - (Indirect),Y addressing mode.

    Opcode: 0x11
    Cycles: 5*
    Flags: N Z

    VARIANT: 6502 - Standard ORA behavior
    VARIANT: 6502A - Standard ORA behavior
    VARIANT: 6502C - Standard ORA behavior
    VARIANT: 65C02 - Standard ORA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_indirect_indexed_mode_address()
    value: int = int(cpu.read_byte(address=address))
    cpu.A = cpu.A | value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")
