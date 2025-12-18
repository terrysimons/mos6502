#!/usr/bin/env python3
"""CPX instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def cpx_immediate_0xe0(cpu: "MOS6502CPU") -> None:
    """Execute CPX (Compare X Register with Memory) - Immediate addressing mode.

    Opcode: 0xE0
    Cycles: 2
    Flags: N Z C

    VARIANT: 6502 - Standard CPX behavior
    VARIANT: 6502A - Standard CPX behavior
    VARIANT: 6502C - Standard CPX behavior
    VARIANT: 65C02 - Standard CPX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    value: int = cpu.fetch_byte()
    result: int = (cpu.X - value) & 0xFF

    # Set flags based on comparison
    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.X >= value else 0  # C=1 if X >= M (no borrow)

    cpu.log.info("i")


def cpx_zeropage_0xe4(cpu: "MOS6502CPU") -> None:
    """Execute CPX (Compare X Register with Memory) - Zeropage addressing mode.

    Opcode: 0xE4
    Cycles: 3
    Flags: N Z C

    VARIANT: 6502 - Standard CPX behavior
    VARIANT: 6502A - Standard CPX behavior
    VARIANT: 6502C - Standard CPX behavior
    VARIANT: 65C02 - Standard CPX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_zeropage_mode_address(None)
    value: int = cpu.read_byte(address)
    result: int = (cpu.X - value) & 0xFF

    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.X >= value else 0

    cpu.log.info("i")


def cpx_absolute_0xec(cpu: "MOS6502CPU") -> None:
    """Execute CPX (Compare X Register with Memory) - Absolute addressing mode.

    Opcode: 0xEC
    Cycles: 4
    Flags: N Z C

    VARIANT: 6502 - Standard CPX behavior
    VARIANT: 6502A - Standard CPX behavior
    VARIANT: 6502C - Standard CPX behavior
    VARIANT: 65C02 - Standard CPX behavior (same as NMOS)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    address: int = cpu.fetch_absolute_mode_address(None)
    value: int = cpu.read_byte(address)
    result: int = (cpu.X - value) & 0xFF

    from mos6502 import flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if cpu.X >= value else 0

    cpu.log.info("i")
