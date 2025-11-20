#!/usr/bin/env python3
"""LSR instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def lsr_accumulator_0x4a(cpu: MOS6502CPU) -> None:
    """Execute LSR (Logical Shift Right) - Accumulator addressing mode.

    Opcode: 0x4A
    Cycles: 2
    Flags: N Z C

    Shift right one bit: 0 -> bit 7, bit 0 -> C

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    value: int = cpu.A

    # Bit 0 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x01) else 0

    result: int = (value >> 1) & 0xFF
    cpu.A = result

    # Set N and Z flags (N is always 0 for LSR since bit 7 becomes 0)
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 0

    cpu.log.info("i")


def lsr_zeropage_0x46(cpu: MOS6502CPU) -> None:
    """Execute LSR (Logical Shift Right) - Zero Page addressing mode.

    Opcode: 0x46
    Cycles: 5
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = int(cpu.read_byte(address=address))

    # Bit 0 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x01) else 0

    result: int = (value >> 1) & 0xFF
    cpu.write_byte(address=address, data=result)

    # Set N and Z flags (N is always 0 for LSR since bit 7 becomes 0)
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 0

    cpu.log.info("z")


def lsr_zeropage_x_0x56(cpu: MOS6502CPU) -> None:
    """Execute LSR (Logical Shift Right) - Zero Page,X addressing mode.

    Opcode: 0x56
    Cycles: 6
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    value: int = int(cpu.read_byte(address=address))

    # Bit 0 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x01) else 0

    result: int = (value >> 1) & 0xFF
    cpu.write_byte(address=address, data=result)

    # Set N and Z flags (N is always 0 for LSR since bit 7 becomes 0)
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 0

    cpu.log.info("zx")


def lsr_absolute_0x4e(cpu: MOS6502CPU) -> None:
    """Execute LSR (Logical Shift Right) - Absolute addressing mode.

    Opcode: 0x4E
    Cycles: 6
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = int(cpu.read_byte(address=address))

    # Read-Modify-Write operations have an internal processing cycle
    cpu.spend_cpu_cycles(1)

    # Bit 0 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x01) else 0

    result: int = (value >> 1) & 0xFF
    cpu.write_byte(address=address & 0xFFFF, data=result)

    # Set N and Z flags (N is always 0 for LSR since bit 7 becomes 0)
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 0

    cpu.log.info("a")


def lsr_absolute_x_0x5e(cpu: MOS6502CPU) -> None:
    """Execute LSR (Logical Shift Right) - Absolute,X addressing mode.

    Opcode: 0x5E
    Cycles: 7
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")

    # Read-Modify-Write with Absolute,X always does a dummy read regardless of page crossing
    cpu.spend_cpu_cycles(1)

    value: int = int(cpu.read_byte(address=address))

    # Internal processing cycle for RMW operation
    cpu.spend_cpu_cycles(1)

    # Bit 0 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x01) else 0

    result: int = (value >> 1) & 0xFF
    cpu.write_byte(address=address & 0xFFFF, data=result)

    # Set N and Z flags (N is always 0 for LSR since bit 7 becomes 0)
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 0

    cpu.log.info("ax")
