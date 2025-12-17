#!/usr/bin/env python3
"""JAM (KIL, HLT) instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - Halts the CPU

JAM halts the CPU. On real hardware, this requires a hardware reset to recover.
The PC does not advance and the data bus is set to $FF.

VARIANT: 6502 - Halts CPU, requires reset
VARIANT: 6502A - Halts CPU, requires reset
VARIANT: 6502C - Halts CPU, requires reset
VARIANT: 65C02 - Acts as NOP (see _jam_65c02.py)

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""


from mos6502.compat import TYPE_CHECKING

from mos6502 import errors

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def _jam_common(cpu: "MOS6502CPU", opcode: int) -> None:
    """Common JAM implementation for all NMOS variants.

    Sets the halted flag and raises CPUHaltError.

    Arguments:
    ---------
        cpu: The CPU instance to operate on
        opcode: The specific JAM opcode that was executed
    """
    # The PC was already incremented past the opcode by the fetch
    # Move it back to point at the JAM instruction
    jam_address = int(cpu.PC) - 1

    # Set the halted flag
    cpu.halted = True

    # Log the halt
    cpu.log.warning(f"JAM instruction ${opcode:02X} executed at ${jam_address:04X} - CPU halted")

    # Raise the halt exception
    raise errors.CPUHaltError(opcode=opcode, address=jam_address)


def jam_implied_0x02(cpu: "MOS6502CPU") -> None:
    """Execute JAM - Halt CPU. Opcode: 0x02"""
    _jam_common(cpu, 0x02)


def jam_implied_0x12(cpu: "MOS6502CPU") -> None:
    """Execute JAM - Halt CPU. Opcode: 0x12"""
    _jam_common(cpu, 0x12)


def jam_implied_0x22(cpu: "MOS6502CPU") -> None:
    """Execute JAM - Halt CPU. Opcode: 0x22"""
    _jam_common(cpu, 0x22)


def jam_implied_0x32(cpu: "MOS6502CPU") -> None:
    """Execute JAM - Halt CPU. Opcode: 0x32"""
    _jam_common(cpu, 0x32)


def jam_implied_0x42(cpu: "MOS6502CPU") -> None:
    """Execute JAM - Halt CPU. Opcode: 0x42"""
    _jam_common(cpu, 0x42)


def jam_implied_0x52(cpu: "MOS6502CPU") -> None:
    """Execute JAM - Halt CPU. Opcode: 0x52"""
    _jam_common(cpu, 0x52)


def jam_implied_0x62(cpu: "MOS6502CPU") -> None:
    """Execute JAM - Halt CPU. Opcode: 0x62"""
    _jam_common(cpu, 0x62)


def jam_implied_0x72(cpu: "MOS6502CPU") -> None:
    """Execute JAM - Halt CPU. Opcode: 0x72"""
    _jam_common(cpu, 0x72)


def jam_implied_0x92(cpu: "MOS6502CPU") -> None:
    """Execute JAM - Halt CPU. Opcode: 0x92"""
    _jam_common(cpu, 0x92)


def jam_implied_0xb2(cpu: "MOS6502CPU") -> None:
    """Execute JAM - Halt CPU. Opcode: 0xB2"""
    _jam_common(cpu, 0xB2)


def jam_implied_0xd2(cpu: "MOS6502CPU") -> None:
    """Execute JAM - Halt CPU. Opcode: 0xD2"""
    _jam_common(cpu, 0xD2)


def jam_implied_0xf2(cpu: "MOS6502CPU") -> None:
    """Execute JAM - Halt CPU. Opcode: 0xF2"""
    _jam_common(cpu, 0xF2)
