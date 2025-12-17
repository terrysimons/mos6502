#!/usr/bin/env python3
"""DCP instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

On 65C02, the DCP opcodes act as NOPs with the same cycle counts as the
NMOS implementation, but without modifying any registers, flags, or memory.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#DCP
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def dcp_zeropage_0xc7(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - Zero Page addressing mode.

    Opcode: 0xC7
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


def dcp_zeropage_x_0xd7(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - Zero Page,X addressing mode.

    Opcode: 0xD7
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


def dcp_indexed_indirect_x_0xc3(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - (Indirect,X) addressing mode.

    Opcode: 0xC3
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


def dcp_indirect_indexed_y_0xd3(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - (Indirect),Y addressing mode.

    Opcode: 0xD3
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


def dcp_absolute_0xcf(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - Absolute addressing mode.

    Opcode: 0xCF
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


def dcp_absolute_x_0xdf(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - Absolute,X addressing mode.

    Opcode: 0xDF
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


def dcp_absolute_y_0xdb(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - Absolute,Y addressing mode.

    Opcode: 0xDB
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
