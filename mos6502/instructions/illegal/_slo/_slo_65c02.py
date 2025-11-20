#!/usr/bin/env python3
"""SLO instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

On 65C02, the SLO opcodes act as NOPs with the same cycle counts as the
NMOS implementation, but without modifying any registers, flags, or memory.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#SLO
  - http://www.oxyron.de/html/opcodes02.html
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def slo_zeropage_0x07(cpu: MOS6502CPU) -> None:
    """Execute SLO (Shift Left and OR) - Zero Page addressing mode.

    Opcode: 0x07
    Cycles: 5
    Bytes: 2
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Consume operand byte
    cpu.fetch_byte()

    # Internal cycles to match NMOS timing
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")


def slo_zeropage_x_0x17(cpu: MOS6502CPU) -> None:
    """Execute SLO (Shift Left and OR) - Zero Page,X addressing mode.

    Opcode: 0x17
    Cycles: 6
    Bytes: 2
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Consume operand byte
    cpu.fetch_byte()

    # Internal cycles to match NMOS timing
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")


def slo_indexed_indirect_x_0x03(cpu: MOS6502CPU) -> None:
    """Execute SLO (Shift Left and OR) - (Indirect,X) addressing mode.

    Opcode: 0x03
    Cycles: 8
    Bytes: 2
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Consume operand byte
    cpu.fetch_byte()

    # Internal cycles to match NMOS timing
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")


def slo_indirect_indexed_y_0x13(cpu: MOS6502CPU) -> None:
    """Execute SLO (Shift Left and OR) - (Indirect),Y addressing mode.

    Opcode: 0x13
    Cycles: 8
    Bytes: 2
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Consume operand byte
    cpu.fetch_byte()

    # Internal cycles to match NMOS timing
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")


def slo_absolute_0x0f(cpu: MOS6502CPU) -> None:
    """Execute SLO (Shift Left and OR) - Absolute addressing mode.

    Opcode: 0x0F
    Cycles: 6
    Bytes: 3
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Consume operand bytes
    cpu.fetch_byte()
    cpu.fetch_byte()

    # Internal cycles to match NMOS timing
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")


def slo_absolute_x_0x1f(cpu: MOS6502CPU) -> None:
    """Execute SLO (Shift Left and OR) - Absolute,X addressing mode.

    Opcode: 0x1F
    Cycles: 7
    Bytes: 3
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Consume operand bytes
    cpu.fetch_byte()
    cpu.fetch_byte()

    # Internal cycles to match NMOS timing
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")


def slo_absolute_y_0x1b(cpu: MOS6502CPU) -> None:
    """Execute SLO (Shift Left and OR) - Absolute,Y addressing mode.

    Opcode: 0x1B
    Cycles: 7
    Bytes: 3
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Consume operand bytes
    cpu.fetch_byte()
    cpu.fetch_byte()

    # Internal cycles to match NMOS timing
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
