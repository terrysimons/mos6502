#!/usr/bin/env python3
"""RRA instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

On 65C02, the RRA opcodes act as NOPs with the same cycle counts as the
NMOS implementation, but without modifying any registers, flags, or memory.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#RRA
  - http://www.oxyron.de/html/opcodes02.html
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def rra_zeropage_0x67(cpu: MOS6502CPU) -> None:
    """Execute RRA (Rotate Right and Add with Carry) - Zero Page addressing mode.

    Opcode: 0x67
    Cycles: 5
    Bytes: 2
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.fetch_byte()
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")


def rra_zeropage_x_0x77(cpu: MOS6502CPU) -> None:
    """Execute RRA (Rotate Right and Add with Carry) - Zero Page,X addressing mode.

    Opcode: 0x77
    Cycles: 6
    Bytes: 2
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.fetch_byte()
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")


def rra_indexed_indirect_x_0x63(cpu: MOS6502CPU) -> None:
    """Execute RRA (Rotate Right and Add with Carry) - (Indirect,X) addressing mode.

    Opcode: 0x63
    Cycles: 8
    Bytes: 2
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.fetch_byte()
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")


def rra_indirect_indexed_y_0x73(cpu: MOS6502CPU) -> None:
    """Execute RRA (Rotate Right and Add with Carry) - (Indirect),Y addressing mode.

    Opcode: 0x73
    Cycles: 8
    Bytes: 2
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.fetch_byte()
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")


def rra_absolute_0x6f(cpu: MOS6502CPU) -> None:
    """Execute RRA (Rotate Right and Add with Carry) - Absolute addressing mode.

    Opcode: 0x6F
    Cycles: 6
    Bytes: 3
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.fetch_byte()
    cpu.fetch_byte()
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")


def rra_absolute_x_0x7f(cpu: MOS6502CPU) -> None:
    """Execute RRA (Rotate Right and Add with Carry) - Absolute,X addressing mode.

    Opcode: 0x7F
    Cycles: 7
    Bytes: 3
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.fetch_byte()
    cpu.fetch_byte()
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")


def rra_absolute_y_0x7b(cpu: MOS6502CPU) -> None:
    """Execute RRA (Rotate Right and Add with Carry) - Absolute,Y addressing mode.

    Opcode: 0x7B
    Cycles: 7
    Bytes: 3
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP (no operation performed)

    Operation: NOP (no registers, flags, or memory modified)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    cpu.fetch_byte()
    cpu.fetch_byte()
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")
