#!/usr/bin/env python3
"""DEC instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def dec_zeropage_0xc6(cpu: MOS6502CPU) -> None:
    """Execute DEC (Decrement Memory) - Zero Page addressing mode.

    Opcode: 0xC6
    Cycles: 5
    Flags: N Z

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)

    result: int = (value - 1) & 0xFF
    cpu.write_byte(address=address, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("z")


def dec_zeropage_x_0xd6(cpu: MOS6502CPU) -> None:
    """Execute DEC (Decrement Memory) - Zero Page,X addressing mode.

    Opcode: 0xD6
    Cycles: 6
    Flags: N Z
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    value: int = cpu.read_byte(address=address)

    result: int = (value - 1) & 0xFF
    cpu.write_byte(address=address, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("zx")


def dec_absolute_0xce(cpu: MOS6502CPU) -> None:
    """Execute DEC (Decrement Memory) - Absolute addressing mode.

    Opcode: 0xCE
    Cycles: 6
    Flags: N Z
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)

    # Read-Modify-Write operations have an internal processing cycle
    cpu.spend_cpu_cycles(1)

    result: int = (value - 1) & 0xFF
    cpu.write_byte(address=address & 0xFFFF, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("a")


def dec_absolute_x_0xde(cpu: MOS6502CPU) -> None:
    """Execute DEC (Decrement Memory) - Absolute,X addressing mode.

    Opcode: 0xDE
    Cycles: 7
    Flags: N Z
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")

    # Read-Modify-Write with Absolute,X always does a dummy read regardless of page crossing
    cpu.spend_cpu_cycles(1)

    value: int = cpu.read_byte(address=address)

    # Internal processing cycle for RMW operation
    cpu.spend_cpu_cycles(1)

    result: int = (value - 1) & 0xFF
    cpu.write_byte(address=address & 0xFFFF, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("ax")
