#!/usr/bin/env python3
"""RLA instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

On 65C02, the RLA opcodes act as NOPs with the same cycle counts as the
NMOS implementation, but without modifying any registers, flags, or memory.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#RLA
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def rla_zeropage_0x27(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - Zero Page addressing mode.

    Opcode: 0x27
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


def rla_zeropage_x_0x37(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - Zero Page,X addressing mode.

    Opcode: 0x37
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


def rla_indexed_indirect_x_0x23(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - (Indirect,X) addressing mode.

    Opcode: 0x23
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


def rla_indirect_indexed_y_0x33(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - (Indirect),Y addressing mode.

    Opcode: 0x33
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


def rla_absolute_0x2f(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - Absolute addressing mode.

    Opcode: 0x2F
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


def rla_absolute_x_0x3f(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - Absolute,X addressing mode.

    Opcode: 0x3F
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


def rla_absolute_y_0x3b(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - Absolute,Y addressing mode.

    Opcode: 0x3B
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
