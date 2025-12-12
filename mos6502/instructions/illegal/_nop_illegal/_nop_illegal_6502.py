#!/usr/bin/env python3
"""Illegal NOP instruction implementations for NMOS 6502 variants.

These undocumented NOP variants consume operand bytes without modifying
registers or flags. They differ only in byte count and cycle count.

VARIANT: 6502 - NOPs with varying byte/cycle counts
VARIANT: 6502A - NOPs with varying byte/cycle counts
VARIANT: 6502C - NOPs with varying byte/cycle counts
VARIANT: 65C02 - Same behavior (see _nop_illegal_65c02.py)

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


# =============================================================================
# 1-byte NOPs (implied mode, 2 cycles)
# =============================================================================

def nop_implied_0x1a(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Implied addressing mode.

    Opcode: 0x1A
    Cycles: 2
    Bytes: 1
    Flags: None affected
    """
    cpu.log.info("i")
    cpu.spend_cpu_cycles(cost=1)


def nop_implied_0x3a(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Implied addressing mode.

    Opcode: 0x3A
    Cycles: 2
    Bytes: 1
    Flags: None affected
    """
    cpu.log.info("i")
    cpu.spend_cpu_cycles(cost=1)


def nop_implied_0x5a(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Implied addressing mode.

    Opcode: 0x5A
    Cycles: 2
    Bytes: 1
    Flags: None affected
    """
    cpu.log.info("i")
    cpu.spend_cpu_cycles(cost=1)


def nop_implied_0x7a(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Implied addressing mode.

    Opcode: 0x7A
    Cycles: 2
    Bytes: 1
    Flags: None affected
    """
    cpu.log.info("i")
    cpu.spend_cpu_cycles(cost=1)


def nop_implied_0xda(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Implied addressing mode.

    Opcode: 0xDA
    Cycles: 2
    Bytes: 1
    Flags: None affected
    """
    cpu.log.info("i")
    cpu.spend_cpu_cycles(cost=1)


def nop_implied_0xfa(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Implied addressing mode.

    Opcode: 0xFA
    Cycles: 2
    Bytes: 1
    Flags: None affected
    """
    cpu.log.info("i")
    cpu.spend_cpu_cycles(cost=1)


# =============================================================================
# 2-byte NOPs (immediate mode, 2 cycles)
# =============================================================================

def nop_immediate_0x80(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Immediate addressing mode.

    Opcode: 0x80
    Cycles: 2
    Bytes: 2
    Flags: None affected
    """
    cpu.fetch_byte()  # Read and discard operand
    cpu.log.info("i")


def nop_immediate_0x82(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Immediate addressing mode.

    Opcode: 0x82
    Cycles: 2
    Bytes: 2
    Flags: None affected
    """
    cpu.fetch_byte()  # Read and discard operand
    cpu.log.info("i")


def nop_immediate_0x89(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Immediate addressing mode.

    Opcode: 0x89
    Cycles: 2
    Bytes: 2
    Flags: None affected
    """
    cpu.fetch_byte()  # Read and discard operand
    cpu.log.info("i")


def nop_immediate_0xc2(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Immediate addressing mode.

    Opcode: 0xC2
    Cycles: 2
    Bytes: 2
    Flags: None affected
    """
    cpu.fetch_byte()  # Read and discard operand
    cpu.log.info("i")


def nop_immediate_0xe2(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Immediate addressing mode.

    Opcode: 0xE2
    Cycles: 2
    Bytes: 2
    Flags: None affected
    """
    cpu.fetch_byte()  # Read and discard operand
    cpu.log.info("i")


# =============================================================================
# 2-byte NOPs (zero page mode, 3 cycles)
# =============================================================================

def nop_zeropage_0x04(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Zero Page addressing mode.

    Opcode: 0x04
    Cycles: 3
    Bytes: 2
    Flags: None affected
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


def nop_zeropage_0x44(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Zero Page addressing mode.

    Opcode: 0x44
    Cycles: 3
    Bytes: 2
    Flags: None affected
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


def nop_zeropage_0x64(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Zero Page addressing mode.

    Opcode: 0x64
    Cycles: 3
    Bytes: 2
    Flags: None affected
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


# =============================================================================
# 2-byte NOPs (zero page,X mode, 4 cycles)
# =============================================================================

def nop_zeropage_x_0x14(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Zero Page,X addressing mode.

    Opcode: 0x14
    Cycles: 4
    Bytes: 2
    Flags: None affected
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


def nop_zeropage_x_0x34(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Zero Page,X addressing mode.

    Opcode: 0x34
    Cycles: 4
    Bytes: 2
    Flags: None affected
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


def nop_zeropage_x_0x54(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Zero Page,X addressing mode.

    Opcode: 0x54
    Cycles: 4
    Bytes: 2
    Flags: None affected
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


def nop_zeropage_x_0x74(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Zero Page,X addressing mode.

    Opcode: 0x74
    Cycles: 4
    Bytes: 2
    Flags: None affected
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


def nop_zeropage_x_0xd4(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Zero Page,X addressing mode.

    Opcode: 0xD4
    Cycles: 4
    Bytes: 2
    Flags: None affected
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


def nop_zeropage_x_0xf4(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Zero Page,X addressing mode.

    Opcode: 0xF4
    Cycles: 4
    Bytes: 2
    Flags: None affected
    """
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


# =============================================================================
# 3-byte NOPs (absolute mode, 4 cycles)
# =============================================================================

def nop_absolute_0x0c(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Absolute addressing mode.

    Opcode: 0x0C
    Cycles: 4
    Bytes: 3
    Flags: None affected
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


# =============================================================================
# 3-byte NOPs (absolute,X mode, 4+ cycles)
# Extra cycle on page boundary crossing
# =============================================================================

def nop_absolute_x_0x1c(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Absolute,X addressing mode.

    Opcode: 0x1C
    Cycles: 4 (5 if page boundary crossed)
    Bytes: 3
    Flags: None affected
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


def nop_absolute_x_0x3c(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Absolute,X addressing mode.

    Opcode: 0x3C
    Cycles: 4 (5 if page boundary crossed)
    Bytes: 3
    Flags: None affected
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


def nop_absolute_x_0x5c(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Absolute,X addressing mode.

    Opcode: 0x5C
    Cycles: 4 (5 if page boundary crossed)
    Bytes: 3
    Flags: None affected
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


def nop_absolute_x_0x7c(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Absolute,X addressing mode.

    Opcode: 0x7C
    Cycles: 4 (5 if page boundary crossed)
    Bytes: 3
    Flags: None affected
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


def nop_absolute_x_0xdc(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Absolute,X addressing mode.

    Opcode: 0xDC
    Cycles: 4 (5 if page boundary crossed)
    Bytes: 3
    Flags: None affected
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")


def nop_absolute_x_0xfc(cpu: MOS6502CPU) -> None:
    """Execute illegal NOP - Absolute,X addressing mode.

    Opcode: 0xFC
    Cycles: 4 (5 if page boundary crossed)
    Bytes: 3
    Flags: None affected
    """
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    cpu.read_byte(address)  # Dummy read
    cpu.log.info("i")
