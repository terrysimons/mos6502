#!/usr/bin/env python3
"""LDA instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def lda_immediate_0xa9(cpu: "MOS6502CPU") -> None:
    """Execute LDA (Load Accumulator with Memory) - Immediate addressing mode.

    Opcode: 0xA9
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard LDA behavior
    VARIANT: 6502A - Standard LDA behavior
    VARIANT: 6502C - Standard LDA behavior
    VARIANT: 65C02 - Standard LDA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    data: int = int(cpu.fetch_immediate_mode_address())
    cpu.A = data
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def lda_zeropage_0xa5(cpu: "MOS6502CPU") -> None:
    """Execute LDA (Load Accumulator with Memory) - Zeropage addressing mode.

    Opcode: 0xA5
    Cycles: 3
    Flags: N Z

    VARIANT: 6502 - Standard LDA behavior
    VARIANT: 6502A - Standard LDA behavior
    VARIANT: 6502C - Standard LDA behavior
    VARIANT: 65C02 - Standard LDA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(None)
    data: int = cpu.read_byte(address)
    cpu.A = data
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def lda_zeropage_x_0xb5(cpu: "MOS6502CPU") -> None:
    """Execute LDA (Load Accumulator with Memory) - Zeropage,X addressing mode.

    Opcode: 0xB5
    Cycles: 4
    Flags: N Z

    VARIANT: 6502 - Standard LDA behavior
    VARIANT: 6502A - Standard LDA behavior
    VARIANT: 6502C - Standard LDA behavior
    VARIANT: 65C02 - Standard LDA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address("X")
    data: int = cpu.read_byte(address)
    cpu.A = data
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def lda_absolute_0xad(cpu: "MOS6502CPU") -> None:
    """Execute LDA (Load Accumulator with Memory) - Absolute addressing mode.

    Opcode: 0xAD
    Cycles: 4
    Flags: N Z

    VARIANT: 6502 - Standard LDA behavior
    VARIANT: 6502A - Standard LDA behavior
    VARIANT: 6502C - Standard LDA behavior
    VARIANT: 65C02 - Standard LDA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(None)
    data: int = cpu.read_byte(address)
    cpu.A = data
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def lda_absolute_x_0xbd(cpu: "MOS6502CPU") -> None:
    """Execute LDA (Load Accumulator with Memory) - Absolute,X addressing mode.

    Opcode: 0xBD
    Cycles: 4 (+1 if page boundary crossed)
    Flags: N Z

    VARIANT: 6502 - Standard LDA behavior
    VARIANT: 6502A - Standard LDA behavior
    VARIANT: 6502C - Standard LDA behavior
    VARIANT: 65C02 - Standard LDA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address("X")
    data: int = cpu.read_byte(address)
    cpu.A = data
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def lda_absolute_y_0xb9(cpu: "MOS6502CPU") -> None:
    """Execute LDA (Load Accumulator with Memory) - Absolute,Y addressing mode.

    Opcode: 0xB9
    Cycles: 4 (+1 if page boundary crossed)
    Flags: N Z

    VARIANT: 6502 - Standard LDA behavior
    VARIANT: 6502A - Standard LDA behavior
    VARIANT: 6502C - Standard LDA behavior
    VARIANT: 65C02 - Standard LDA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address("Y")
    data: int = cpu.read_byte(address)
    cpu.A = data
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def lda_indexed_indirect_x_0xa1(cpu: "MOS6502CPU") -> None:
    """Execute LDA (Load Accumulator with Memory) - (Indirect,X) addressing mode.

    Opcode: 0xA1
    Cycles: 6
    Flags: N Z

    VARIANT: 6502 - Standard LDA behavior
    VARIANT: 6502A - Standard LDA behavior
    VARIANT: 6502C - Standard LDA behavior
    VARIANT: 65C02 - Standard LDA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_indexed_indirect_mode_address()
    data: int = cpu.read_byte(address)
    cpu.A = data
    cpu.set_load_status_flags("A")
    cpu.log.info("i")


def lda_indirect_indexed_y_0xb1(cpu: "MOS6502CPU") -> None:
    """Execute LDA (Load Accumulator with Memory) - (Indirect),Y addressing mode.

    Opcode: 0xB1
    Cycles: 5 (+1 if page boundary crossed)
    Flags: N Z

    VARIANT: 6502 - Standard LDA behavior
    VARIANT: 6502A - Standard LDA behavior
    VARIANT: 6502C - Standard LDA behavior
    VARIANT: 65C02 - Standard LDA behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_indirect_indexed_mode_address()
    data: int = cpu.read_byte(address)
    cpu.A = data
    cpu.set_load_status_flags("A")
    cpu.log.info("i")
