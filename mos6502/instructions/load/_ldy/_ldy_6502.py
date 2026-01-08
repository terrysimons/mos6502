#!/usr/bin/env python3
"""LDY instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def ldy_immediate_0xa0(cpu: "MOS6502CPU") -> None:
    """Execute LDY (Load Y Register with Memory) - Immediate addressing mode.

    Opcode: 0xA0
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard LDY behavior
    VARIANT: 6502A - Standard LDY behavior
    VARIANT: 6502C - Standard LDY behavior
    VARIANT: 65C02 - Standard LDY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    data: int = int(cpu.fetch_immediate_mode_address())
    cpu.Y = data
    cpu.set_load_status_flags("Y")
    cpu.log.info("i")


def ldy_zeropage_0xa4(cpu: "MOS6502CPU") -> None:
    """Execute LDY (Load Y Register with Memory) - Zeropage addressing mode.

    Opcode: 0xA4
    Cycles: 3
    Flags: N Z

    VARIANT: 6502 - Standard LDY behavior
    VARIANT: 6502A - Standard LDY behavior
    VARIANT: 6502C - Standard LDY behavior
    VARIANT: 65C02 - Standard LDY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(None)
    data: int = cpu.read_byte(address)
    cpu.Y = data
    cpu.set_load_status_flags("Y")
    cpu.log.info("i")


def ldy_zeropage_x_0xb4(cpu: "MOS6502CPU") -> None:
    """Execute LDY (Load Y Register with Memory) - Zeropage,X addressing mode.

    Opcode: 0xB4
    Cycles: 4
    Flags: N Z

    VARIANT: 6502 - Standard LDY behavior
    VARIANT: 6502A - Standard LDY behavior
    VARIANT: 6502C - Standard LDY behavior
    VARIANT: 65C02 - Standard LDY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address("X")
    data: int = cpu.read_byte(address)
    cpu.Y = data
    cpu.set_load_status_flags("Y")
    cpu.log.info("i")


def ldy_absolute_0xac(cpu: "MOS6502CPU") -> None:
    """Execute LDY (Load Y Register with Memory) - Absolute addressing mode.

    Opcode: 0xAC
    Cycles: 4
    Flags: N Z

    VARIANT: 6502 - Standard LDY behavior
    VARIANT: 6502A - Standard LDY behavior
    VARIANT: 6502C - Standard LDY behavior
    VARIANT: 65C02 - Standard LDY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(None)
    data: int = cpu.read_byte(address)
    cpu.Y = data
    cpu.set_load_status_flags("Y")
    cpu.log.info("i")


def ldy_absolute_x_0xbc(cpu: "MOS6502CPU") -> None:
    """Execute LDY (Load Y Register with Memory) - Absolute,X addressing mode.

    Opcode: 0xBC
    Cycles: 4 (+1 if page boundary crossed)
    Flags: N Z

    VARIANT: 6502 - Standard LDY behavior
    VARIANT: 6502A - Standard LDY behavior
    VARIANT: 6502C - Standard LDY behavior
    VARIANT: 65C02 - Standard LDY behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address("X")
    data: int = cpu.read_byte(address)
    cpu.Y = data
    cpu.set_load_status_flags("Y")
    cpu.log.info("i")
