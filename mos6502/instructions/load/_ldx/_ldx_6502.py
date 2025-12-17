#!/usr/bin/env python3
"""LDX instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def ldx_immediate_0xa2(cpu: "MOS6502CPU") -> None:
    """Execute LDX (Load X Register with Memory) - Immediate addressing mode.

    Opcode: 0xA2
    Cycles: 2
    Flags: N Z

    VARIANT: 6502 - Standard LDX behavior
    VARIANT: 6502A - Standard LDX behavior
    VARIANT: 6502C - Standard LDX behavior
    VARIANT: 65C02 - Standard LDX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    data: int = int(cpu.fetch_immediate_mode_address())
    cpu.X = data
    cpu.set_load_status_flags(register_name="X")
    cpu.log.info("i")


def ldx_zeropage_0xa6(cpu: "MOS6502CPU") -> None:
    """Execute LDX (Load X Register with Memory) - Zeropage addressing mode.

    Opcode: 0xA6
    Cycles: 3
    Flags: N Z

    VARIANT: 6502 - Standard LDX behavior
    VARIANT: 6502A - Standard LDX behavior
    VARIANT: 6502C - Standard LDX behavior
    VARIANT: 65C02 - Standard LDX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    data: int = cpu.read_byte(address=address)
    cpu.X = data
    cpu.set_load_status_flags(register_name="X")
    cpu.log.info("i")


def ldx_zeropage_y_0xb6(cpu: "MOS6502CPU") -> None:
    """Execute LDX (Load X Register with Memory) - Zeropage,Y addressing mode.

    Opcode: 0xB6
    Cycles: 4
    Flags: N Z

    VARIANT: 6502 - Standard LDX behavior
    VARIANT: 6502A - Standard LDX behavior
    VARIANT: 6502C - Standard LDX behavior
    VARIANT: 65C02 - Standard LDX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="Y")
    data: int = cpu.read_byte(address=address)
    cpu.X = data
    cpu.set_load_status_flags(register_name="X")
    cpu.log.info("i")


def ldx_absolute_0xae(cpu: "MOS6502CPU") -> None:
    """Execute LDX (Load X Register with Memory) - Absolute addressing mode.

    Opcode: 0xAE
    Cycles: 4
    Flags: N Z

    VARIANT: 6502 - Standard LDX behavior
    VARIANT: 6502A - Standard LDX behavior
    VARIANT: 6502C - Standard LDX behavior
    VARIANT: 65C02 - Standard LDX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    data: int = cpu.read_byte(address=address)
    cpu.X = data
    cpu.set_load_status_flags(register_name="X")
    cpu.log.info("i")


def ldx_absolute_y_0xbe(cpu: "MOS6502CPU") -> None:
    """Execute LDX (Load X Register with Memory) - Absolute,Y addressing mode.

    Opcode: 0xBE
    Cycles: 4 (+1 if page boundary crossed)
    Flags: N Z

    VARIANT: 6502 - Standard LDX behavior
    VARIANT: 6502A - Standard LDX behavior
    VARIANT: 6502C - Standard LDX behavior
    VARIANT: 65C02 - Standard LDX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name="Y")
    data: int = cpu.read_byte(address=address)
    cpu.X = data
    cpu.set_load_status_flags(register_name="X")
    cpu.log.info("i")
