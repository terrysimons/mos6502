#!/usr/bin/env python3
"""ISC instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

On 65C02, the ISC opcodes act as NOPs with the same cycle counts as the
NMOS implementation, but without modifying any registers, flags, or memory.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#ISC
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def isc_zeropage_0xe7(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - Zero Page addressing mode.

    Opcode: 0xE7
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


def isc_zeropage_x_0xf7(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - Zero Page,X addressing mode.

    Opcode: 0xF7
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


def isc_indexed_indirect_x_0xe3(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - (Indirect,X) addressing mode.

    Opcode: 0xE3
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


def isc_indirect_indexed_y_0xf3(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - (Indirect),Y addressing mode.

    Opcode: 0xF3
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


def isc_absolute_0xef(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - Absolute addressing mode.

    Opcode: 0xEF
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


def isc_absolute_x_0xff(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - Absolute,X addressing mode.

    Opcode: 0xFF
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


def isc_absolute_y_0xfb(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - Absolute,Y addressing mode.

    Opcode: 0xFB
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
