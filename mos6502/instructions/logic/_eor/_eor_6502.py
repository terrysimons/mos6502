#!/usr/bin/env python3
"""EOR instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def eor_immediate_0x49(cpu: MOS6502CPU) -> None:
    """Execute EOR (Exclusive OR with Accumulator) - Immediate addressing mode.

    Opcode: 0x49
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard EOR behavior
    VARIANT: 6502A - Standard EOR behavior
    VARIANT: 6502C - Standard EOR behavior
    VARIANT: 65C02 - Standard EOR behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    value: int = cpu.fetch_byte()
    cpu.A = cpu.A ^ value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def eor_zeropage_0x45(cpu: MOS6502CPU) -> None:
    """Execute EOR (Exclusive OR with Accumulator) - Zeropage addressing mode.

    Opcode: 0x45
    Cycles: 3
    Flags: N Z

    VARIANT: 6502 - Standard EOR behavior
    VARIANT: 6502A - Standard EOR behavior
    VARIANT: 6502C - Standard EOR behavior
    VARIANT: 65C02 - Standard EOR behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)
    cpu.A = cpu.A ^ value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def eor_zeropage_x_0x55(cpu: MOS6502CPU) -> None:
    """Execute EOR (Exclusive OR with Accumulator) - Zeropage,X addressing mode.

    Opcode: 0x55
    Cycles: 4
    Flags: N Z

    VARIANT: 6502 - Standard EOR behavior
    VARIANT: 6502A - Standard EOR behavior
    VARIANT: 6502C - Standard EOR behavior
    VARIANT: 65C02 - Standard EOR behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    value: int = cpu.read_byte(address=address)
    cpu.A = cpu.A ^ value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def eor_absolute_0x4d(cpu: MOS6502CPU) -> None:
    """Execute EOR (Exclusive OR with Accumulator) - Absolute addressing mode.

    Opcode: 0x4D
    Cycles: 4
    Flags: N Z

    VARIANT: 6502 - Standard EOR behavior
    VARIANT: 6502A - Standard EOR behavior
    VARIANT: 6502C - Standard EOR behavior
    VARIANT: 65C02 - Standard EOR behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)
    cpu.A = cpu.A ^ value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def eor_absolute_x_0x5d(cpu: MOS6502CPU) -> None:
    """Execute EOR (Exclusive OR with Accumulator) - Absolute,X addressing mode.

    Opcode: 0x5D
    Cycles: 4*
    Flags: N Z

    VARIANT: 6502 - Standard EOR behavior
    VARIANT: 6502A - Standard EOR behavior
    VARIANT: 6502C - Standard EOR behavior
    VARIANT: 65C02 - Standard EOR behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    value: int = cpu.read_byte(address=address)
    cpu.A = cpu.A ^ value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def eor_absolute_y_0x59(cpu: MOS6502CPU) -> None:
    """Execute EOR (Exclusive OR with Accumulator) - Absolute,Y addressing mode.

    Opcode: 0x59
    Cycles: 4*
    Flags: N Z

    VARIANT: 6502 - Standard EOR behavior
    VARIANT: 6502A - Standard EOR behavior
    VARIANT: 6502C - Standard EOR behavior
    VARIANT: 65C02 - Standard EOR behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="Y")
    value: int = cpu.read_byte(address=address)
    cpu.A = cpu.A ^ value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def eor_indexed_indirect_x_0x41(cpu: MOS6502CPU) -> None:
    """Execute EOR (Exclusive OR with Accumulator) - (Indirect,X) addressing mode.

    Opcode: 0x41
    Cycles: 6
    Flags: N Z

    VARIANT: 6502 - Standard EOR behavior
    VARIANT: 6502A - Standard EOR behavior
    VARIANT: 6502C - Standard EOR behavior
    VARIANT: 65C02 - Standard EOR behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_indexed_indirect_mode_address()
    value: int = cpu.read_byte(address=address)
    cpu.A = cpu.A ^ value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")


def eor_indirect_indexed_y_0x51(cpu: MOS6502CPU) -> None:
    """Execute EOR (Exclusive OR with Accumulator) - (Indirect),Y addressing mode.

    Opcode: 0x51
    Cycles: 5*
    Flags: N Z

    VARIANT: 6502 - Standard EOR behavior
    VARIANT: 6502A - Standard EOR behavior
    VARIANT: 6502C - Standard EOR behavior
    VARIANT: 65C02 - Standard EOR behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_indirect_indexed_mode_address()
    value: int = cpu.read_byte(address=address)
    cpu.A = cpu.A ^ value
    cpu.set_load_status_flags(register_name="A")
    cpu.log.info("i")
