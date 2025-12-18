#!/usr/bin/env python3
"""AND instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def and_immediate_0x29(cpu: "MOS6502CPU") -> None:
    """Execute AND (Logical AND with Accumulator) - Immediate addressing mode.

    Opcode: 0x29
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard AND behavior
    VARIANT: 6502A - Standard AND behavior
    VARIANT: 6502C - Standard AND behavior
    VARIANT: 65C02 - Standard AND behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    value: int = cpu.fetch_byte()
    cpu.A = cpu.A & value
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def and_zeropage_0x25(cpu: "MOS6502CPU") -> None:
    """Execute AND (Logical AND with Accumulator) - Zeropage addressing mode.

    Opcode: 0x25
    Cycles: 3
    Flags: N Z

    VARIANT: 6502 - Standard AND behavior
    VARIANT: 6502A - Standard AND behavior
    VARIANT: 6502C - Standard AND behavior
    VARIANT: 65C02 - Standard AND behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address(None)
    value: int = cpu.read_byte(address)
    cpu.A = cpu.A & value
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def and_zeropage_x_0x35(cpu: "MOS6502CPU") -> None:
    """Execute AND (Logical AND with Accumulator) - Zeropage,X addressing mode.

    Opcode: 0x35
    Cycles: 4
    Flags: N Z

    VARIANT: 6502 - Standard AND behavior
    VARIANT: 6502A - Standard AND behavior
    VARIANT: 6502C - Standard AND behavior
    VARIANT: 65C02 - Standard AND behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address("X")
    value: int = cpu.read_byte(address)
    cpu.A = cpu.A & value
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def and_absolute_0x2d(cpu: "MOS6502CPU") -> None:
    """Execute AND (Logical AND with Accumulator) - Absolute addressing mode.

    Opcode: 0x2D
    Cycles: 4
    Flags: N Z

    VARIANT: 6502 - Standard AND behavior
    VARIANT: 6502A - Standard AND behavior
    VARIANT: 6502C - Standard AND behavior
    VARIANT: 65C02 - Standard AND behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(None)
    value: int = cpu.read_byte(address)
    cpu.A = cpu.A & value
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def and_absolute_x_0x3d(cpu: "MOS6502CPU") -> None:
    """Execute AND (Logical AND with Accumulator) - Absolute,X addressing mode.

    Opcode: 0x3D
    Cycles: 4*
    Flags: N Z

    VARIANT: 6502 - Standard AND behavior
    VARIANT: 6502A - Standard AND behavior
    VARIANT: 6502C - Standard AND behavior
    VARIANT: 65C02 - Standard AND behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address("X")
    value: int = cpu.read_byte(address)
    cpu.A = cpu.A & value
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def and_absolute_y_0x39(cpu: "MOS6502CPU") -> None:
    """Execute AND (Logical AND with Accumulator) - Absolute,Y addressing mode.

    Opcode: 0x39
    Cycles: 4*
    Flags: N Z

    VARIANT: 6502 - Standard AND behavior
    VARIANT: 6502A - Standard AND behavior
    VARIANT: 6502C - Standard AND behavior
    VARIANT: 65C02 - Standard AND behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address("Y")
    value: int = cpu.read_byte(address)
    cpu.A = cpu.A & value
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def and_indexed_indirect_x_0x21(cpu: "MOS6502CPU") -> None:
    """Execute AND (Logical AND with Accumulator) - (Indirect,X) addressing mode.

    Opcode: 0x21
    Cycles: 6
    Flags: N Z

    VARIANT: 6502 - Standard AND behavior
    VARIANT: 6502A - Standard AND behavior
    VARIANT: 6502C - Standard AND behavior
    VARIANT: 65C02 - Standard AND behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_indexed_indirect_mode_address()
    value: int = cpu.read_byte(address)
    cpu.A = cpu.A & value
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def and_indirect_indexed_y_0x31(cpu: "MOS6502CPU") -> None:
    """Execute AND (Logical AND with Accumulator) - (Indirect),Y addressing mode.

    Opcode: 0x31
    Cycles: 5*
    Flags: N Z

    VARIANT: 6502 - Standard AND behavior
    VARIANT: 6502A - Standard AND behavior
    VARIANT: 6502C - Standard AND behavior
    VARIANT: 65C02 - Standard AND behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_indirect_indexed_mode_address()
    value: int = cpu.read_byte(address)
    cpu.A = cpu.A & value
    cpu.set_load_status_flags("A")
    cpu.log.info("i")
