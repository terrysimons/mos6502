#!/usr/bin/env python3
"""TAS (XAS, SHS) instruction implementation for CMOS 65C02 variant.

ILLEGAL INSTRUCTION - Acts as NOP on CMOS

VARIANT: 65C02 - Acts as NOP

References:
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def tas_absolute_y_0x9b(cpu: "MOS6502CPU") -> None:
    """Execute TAS (XAS, SHS) - Absolute Y addressing mode - 65C02 variant.

    Opcode: 0x9B
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
