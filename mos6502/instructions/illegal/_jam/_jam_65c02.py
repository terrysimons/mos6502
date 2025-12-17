#!/usr/bin/env python3
"""JAM (KIL, HLT) instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

On 65C02, the JAM opcodes act as 1-byte, 1-cycle NOPs instead of halting.

VARIANT: 65C02 - Acts as NOP

References:
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def _jam_nop(cpu: "MOS6502CPU") -> None:
    """Common JAM NOP implementation for 65C02.

    Does nothing - opcode was already fetched, PC already advanced.
    """
    cpu.log.info("i")


def jam_implied_0x02(cpu: "MOS6502CPU") -> None:
    """Execute JAM as NOP - 65C02 variant. Opcode: 0x02"""
    _jam_nop(cpu)


def jam_implied_0x12(cpu: "MOS6502CPU") -> None:
    """Execute JAM as NOP - 65C02 variant. Opcode: 0x12"""
    _jam_nop(cpu)


def jam_implied_0x22(cpu: "MOS6502CPU") -> None:
    """Execute JAM as NOP - 65C02 variant. Opcode: 0x22"""
    _jam_nop(cpu)


def jam_implied_0x32(cpu: "MOS6502CPU") -> None:
    """Execute JAM as NOP - 65C02 variant. Opcode: 0x32"""
    _jam_nop(cpu)


def jam_implied_0x42(cpu: "MOS6502CPU") -> None:
    """Execute JAM as NOP - 65C02 variant. Opcode: 0x42"""
    _jam_nop(cpu)


def jam_implied_0x52(cpu: "MOS6502CPU") -> None:
    """Execute JAM as NOP - 65C02 variant. Opcode: 0x52"""
    _jam_nop(cpu)


def jam_implied_0x62(cpu: "MOS6502CPU") -> None:
    """Execute JAM as NOP - 65C02 variant. Opcode: 0x62"""
    _jam_nop(cpu)


def jam_implied_0x72(cpu: "MOS6502CPU") -> None:
    """Execute JAM as NOP - 65C02 variant. Opcode: 0x72"""
    _jam_nop(cpu)


def jam_implied_0x92(cpu: "MOS6502CPU") -> None:
    """Execute JAM as NOP - 65C02 variant. Opcode: 0x92"""
    _jam_nop(cpu)


def jam_implied_0xb2(cpu: "MOS6502CPU") -> None:
    """Execute JAM as NOP - 65C02 variant. Opcode: 0xB2"""
    _jam_nop(cpu)


def jam_implied_0xd2(cpu: "MOS6502CPU") -> None:
    """Execute JAM as NOP - 65C02 variant. Opcode: 0xD2"""
    _jam_nop(cpu)


def jam_implied_0xf2(cpu: "MOS6502CPU") -> None:
    """Execute JAM as NOP - 65C02 variant. Opcode: 0xF2"""
    _jam_nop(cpu)
