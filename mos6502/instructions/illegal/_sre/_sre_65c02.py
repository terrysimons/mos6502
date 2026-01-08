#!/usr/bin/env python3
"""SRE instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

On 65C02, the SRE opcodes act as NOPs with the same cycle counts as the
NMOS implementation, but without modifying any registers, flags, or memory.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#SRE
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sre_zeropage_0x47(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - Zero Page addressing mode.

    Opcode: 0x47
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


def sre_zeropage_x_0x57(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - Zero Page,X addressing mode.

    Opcode: 0x57
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


def sre_indexed_indirect_x_0x43(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - (Indirect,X) addressing mode.

    Opcode: 0x43
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


def sre_indirect_indexed_y_0x53(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - (Indirect),Y addressing mode.

    Opcode: 0x53
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


def sre_absolute_0x4f(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - Absolute addressing mode.

    Opcode: 0x4F
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


def sre_absolute_x_0x5f(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - Absolute,X addressing mode.

    Opcode: 0x5F
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


def sre_absolute_y_0x5b(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - Absolute,Y addressing mode.

    Opcode: 0x5B
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
