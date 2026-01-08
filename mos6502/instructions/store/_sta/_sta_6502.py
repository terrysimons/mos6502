#!/usr/bin/env python3
"""STA instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sta_zeropage_0x85(cpu: "MOS6502CPU") -> None:
    """Execute STA (Store Accumulator in Memory) - Zeropage addressing mode.

    Opcode: 0x85
    Cycles: 3
    Flags: None

    VARIANT: 6502 - Standard STA behavior
    VARIANT: 6502A - Standard STA behavior
    VARIANT: 6502C - Standard STA behavior
    VARIANT: 65C02 - Standard STA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address(None)
    cpu.write_byte(address, cpu.A)
    cpu.log.info("i")


def sta_zeropage_x_0x95(cpu: "MOS6502CPU") -> None:
    """Execute STA (Store Accumulator in Memory) - Zeropage,X addressing mode.

    Opcode: 0x95
    Cycles: 4
    Flags: None

    VARIANT: 6502 - Standard STA behavior
    VARIANT: 6502A - Standard STA behavior
    VARIANT: 6502C - Standard STA behavior
    VARIANT: 65C02 - Standard STA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address("X")
    cpu.write_byte(address, cpu.A)
    cpu.log.info("i")


def sta_absolute_0x8d(cpu: "MOS6502CPU") -> None:
    """Execute STA (Store Accumulator in Memory) - Absolute addressing mode.

    Opcode: 0x8D
    Cycles: 4
    Flags: None

    VARIANT: 6502 - Standard STA behavior
    VARIANT: 6502A - Standard STA behavior
    VARIANT: 6502C - Standard STA behavior
    VARIANT: 65C02 - Standard STA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(None)
    cpu.write_byte(address & 0xFFFF, cpu.A)
    cpu.log.info("i")


def sta_absolute_x_0x9d(cpu: "MOS6502CPU") -> None:
    """Execute STA (Store Accumulator in Memory) - Absolute,X addressing mode.

    Opcode: 0x9D
    Cycles: 5
    Flags: None

    VARIANT: 6502 - Standard STA behavior
    VARIANT: 6502A - Standard STA behavior
    VARIANT: 6502C - Standard STA behavior
    VARIANT: 65C02 - Standard STA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address("X")

    # Store operations always take 5 cycles due to a dummy read that occurs
    # before the write, regardless of page boundary crossing
    cpu.spend_cpu_cycles(1)

    cpu.write_byte(address & 0xFFFF, cpu.A)
    cpu.log.info("i")


def sta_absolute_y_0x99(cpu: "MOS6502CPU") -> None:
    """Execute STA (Store Accumulator in Memory) - Absolute,Y addressing mode.

    Opcode: 0x99
    Cycles: 5
    Flags: None

    VARIANT: 6502 - Standard STA behavior
    VARIANT: 6502A - Standard STA behavior
    VARIANT: 6502C - Standard STA behavior
    VARIANT: 65C02 - Standard STA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address("Y")

    # Store operations always take 5 cycles due to a dummy read that occurs
    # before the write, regardless of page boundary crossing
    cpu.spend_cpu_cycles(1)

    cpu.write_byte(address & 0xFFFF, cpu.A)
    cpu.log.info("i")


def sta_indexed_indirect_x_0x81(cpu: "MOS6502CPU") -> None:
    """Execute STA (Store Accumulator in Memory) - (Indirect,X) addressing mode.

    Opcode: 0x81
    Cycles: 6
    Flags: None

    VARIANT: 6502 - Standard STA behavior
    VARIANT: 6502A - Standard STA behavior
    VARIANT: 6502C - Standard STA behavior
    VARIANT: 65C02 - Standard STA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_indexed_indirect_mode_address()
    cpu.write_byte(address & 0xFFFF, cpu.A)
    cpu.log.info("i")


def sta_indirect_indexed_y_0x91(cpu: "MOS6502CPU") -> None:
    """Execute STA (Store Accumulator in Memory) - (Indirect),Y addressing mode.

    Opcode: 0x91
    Cycles: 6
    Flags: None

    VARIANT: 6502 - Standard STA behavior
    VARIANT: 6502A - Standard STA behavior
    VARIANT: 6502C - Standard STA behavior
    VARIANT: 65C02 - Standard STA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_indirect_indexed_mode_address()
    cpu.write_byte(address & 0xFFFF, cpu.A)
    cpu.log.info("i")
