#!/usr/bin/env python3
"""ROR instruction implementation for all 6502 variants."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def ror_accumulator_0x6a(cpu: MOS6502CPU) -> None:
    """Execute ROR (Rotate Right) - Accumulator addressing mode.

    Opcode: 0x6A
    Cycles: 2
    Flags: N Z C

    Rotate right one bit through carry: bit 0 -> C, C -> bit 7

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    value: int = cpu.A
    carry_in: int = cpu.flags[flags.C]

    # Bit 0 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x01) else 0

    # Rotate right: shift right and add carry to bit 7
    result: int = (value >> 1) | (carry_in << 7)
    cpu.A = result

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("i")


def ror_zeropage_0x66(cpu: MOS6502CPU) -> None:
    """Execute ROR (Rotate Right) - Zero Page addressing mode.

    Opcode: 0x66
    Cycles: 5
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = int(cpu.read_byte(address=address))
    carry_in: int = cpu.flags[flags.C]

    # Bit 0 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x01) else 0

    # Rotate right: shift right and add carry to bit 7
    result: int = (value >> 1) | (carry_in << 7)
    cpu.write_byte(address=address, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("z")


def ror_zeropage_x_0x76(cpu: MOS6502CPU) -> None:
    """Execute ROR (Rotate Right) - Zero Page,X addressing mode.

    Opcode: 0x76
    Cycles: 6
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    value: int = int(cpu.read_byte(address=address))
    carry_in: int = cpu.flags[flags.C]

    # Bit 0 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x01) else 0

    # Rotate right: shift right and add carry to bit 7
    result: int = (value >> 1) | (carry_in << 7)
    cpu.write_byte(address=address, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("zx")


def ror_absolute_0x6e(cpu: MOS6502CPU) -> None:
    """Execute ROR (Rotate Right) - Absolute addressing mode.

    Opcode: 0x6E
    Cycles: 6
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = int(cpu.read_byte(address=address))
    carry_in: int = cpu.flags[flags.C]

    # Bit 0 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x01) else 0

    # Rotate right: shift right and add carry to bit 7
    result: int = (value >> 1) | (carry_in << 7)
    cpu.write_byte(address=address & 0xFFFF, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("a")


def ror_absolute_x_0x7e(cpu: MOS6502CPU) -> None:
    """Execute ROR (Rotate Right) - Absolute,X addressing mode.

    Opcode: 0x7E
    Cycles: 7
    Flags: N Z C
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    value: int = int(cpu.read_byte(address=address))
    carry_in: int = cpu.flags[flags.C]

    # Bit 0 goes to carry flag
    cpu.flags[flags.C] = 1 if (value & 0x01) else 0

    # Rotate right: shift right and add carry to bit 7
    result: int = (value >> 1) | (carry_in << 7)
    cpu.write_byte(address=address & 0xFFFF, data=result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    # Read-Modify-Write with Absolute,X always takes 7 cycles (not conditional on page crossing)
    cpu.spend_cpu_cycles(1)

    cpu.log.info("ax")
