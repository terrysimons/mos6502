#!/usr/bin/env python3
"""SHA (AHX, AXA) instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

On 65C02, the SHA opcodes act as NOPs with their respective byte counts.

VARIANT: 65C02 - Acts as NOP (no registers, flags, or memory modified)

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sha_indirect_indexed_y_0x93(cpu: "MOS6502CPU") -> None:
    """Execute SHA (AHX) - Indirect Indexed Y addressing mode - 65C02 variant.

    Opcode: 0x93
    Cycles: 6
    Bytes: 2
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch operand to advance PC
    cpu.fetch_byte()
    cpu.log.info("i")


def sha_absolute_y_0x9f(cpu: "MOS6502CPU") -> None:
    """Execute SHA (AHX) - Absolute Y addressing mode - 65C02 variant.

    Opcode: 0x9F
    Cycles: 5
    Bytes: 3
    Flags: None affected

    VARIANT: 65C02 - Acts as NOP

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch operands to advance PC
    cpu.fetch_byte()
    cpu.fetch_byte()
    cpu.log.info("i")
