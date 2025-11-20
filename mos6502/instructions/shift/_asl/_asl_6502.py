#!/usr/bin/env python3
"""ASL instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def asl_accumulator_0x0a(cpu: MOS6502CPU) -> None:
    """Execute ASL (Arithmetic Shift Left) - Accumulator addressing mode.

    Opcode: 0x0A
    Cycles: 2
    Flags: N Z C

    Shift left one bit: bit 7 -> C, 0 -> bit 0

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    value: int = cpu.A

    # Bit 7 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0

    result: int = (value << 1) & 0xFF
    cpu.A = result

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("i")


def asl_zeropage_0x06(cpu: MOS6502CPU) -> None:
    """Execute ASL (Arithmetic Shift Left) - Zero Page addressing mode.

    Opcode: 0x06
    Cycles: 5
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = int(cpu.read_byte(address=address))

    # Bit 7 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0

    result: int = (value << 1) & 0xFF
    cpu.write_byte(address=address, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("z")


def asl_zeropage_x_0x16(cpu: MOS6502CPU) -> None:
    """Execute ASL (Arithmetic Shift Left) - Zero Page,X addressing mode.

    Opcode: 0x16
    Cycles: 6
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    value: int = int(cpu.read_byte(address=address))

    # Bit 7 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0

    result: int = (value << 1) & 0xFF
    cpu.write_byte(address=address, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("zx")


def asl_absolute_0x0e(cpu: MOS6502CPU) -> None:
    """Execute ASL (Arithmetic Shift Left) - Absolute addressing mode.

    Opcode: 0x0E
    Cycles: 6
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = int(cpu.read_byte(address=address))

    # Bit 7 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0

    result: int = (value << 1) & 0xFF
    cpu.write_byte(address=address & 0xFFFF, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("a")


def asl_absolute_x_0x1e(cpu: MOS6502CPU) -> None:
    """Execute ASL (Arithmetic Shift Left) - Absolute,X addressing mode.

    Opcode: 0x1E
    Cycles: 7
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    value: int = int(cpu.read_byte(address=address))

    # Bit 7 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0

    result: int = (value << 1) & 0xFF
    cpu.write_byte(address=address & 0xFFFF, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    # Read-Modify-Write with Absolute,X always takes 7 cycles (not conditional on page crossing)
    cpu.spend_cpu_cycles(1)

    cpu.log.info("ax")
