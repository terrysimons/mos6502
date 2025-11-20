#!/usr/bin/env python3
"""ROL instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def rol_accumulator_0x2a(cpu: MOS6502CPU) -> None:
    """Execute ROL (Rotate Left) - Accumulator addressing mode.

    Opcode: 0x2A
    Cycles: 2
    Flags: N Z C

    Rotate left one bit through carry: C -> bit 0, bit 7 -> C

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    value: int = cpu.A
    carry_in: int = cpu.flags[flags.C]

    # Bit 7 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0

    # Rotate left: shift left and add carry to bit 0
    result: int = ((value << 1) | carry_in) & 0xFF
    cpu.A = result

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("i")


def rol_zeropage_0x26(cpu: MOS6502CPU) -> None:
    """Execute ROL (Rotate Left) - Zero Page addressing mode.

    Opcode: 0x26
    Cycles: 5
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = int(cpu.read_byte(address=address))
    carry_in: int = cpu.flags[flags.C]

    # Bit 7 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0

    # Rotate left: shift left and add carry to bit 0
    result: int = ((value << 1) | carry_in) & 0xFF
    cpu.write_byte(address=address, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("z")


def rol_zeropage_x_0x36(cpu: MOS6502CPU) -> None:
    """Execute ROL (Rotate Left) - Zero Page,X addressing mode.

    Opcode: 0x36
    Cycles: 6
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    value: int = int(cpu.read_byte(address=address))
    carry_in: int = cpu.flags[flags.C]

    # Bit 7 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0

    # Rotate left: shift left and add carry to bit 0
    result: int = ((value << 1) | carry_in) & 0xFF
    cpu.write_byte(address=address, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("zx")


def rol_absolute_0x2e(cpu: MOS6502CPU) -> None:
    """Execute ROL (Rotate Left) - Absolute addressing mode.

    Opcode: 0x2E
    Cycles: 6
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = int(cpu.read_byte(address=address))
    carry_in: int = cpu.flags[flags.C]

    # Bit 7 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0

    # Rotate left: shift left and add carry to bit 0
    result: int = ((value << 1) | carry_in) & 0xFF
    cpu.write_byte(address=address & 0xFFFF, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("a")


def rol_absolute_x_0x3e(cpu: MOS6502CPU) -> None:
    """Execute ROL (Rotate Left) - Absolute,X addressing mode.

    Opcode: 0x3E
    Cycles: 7
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    value: int = int(cpu.read_byte(address=address))
    carry_in: int = cpu.flags[flags.C]

    # Bit 7 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0

    # Rotate left: shift left and add carry to bit 0
    result: int = ((value << 1) | carry_in) & 0xFF
    cpu.write_byte(address=address & 0xFFFF, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("ax")
