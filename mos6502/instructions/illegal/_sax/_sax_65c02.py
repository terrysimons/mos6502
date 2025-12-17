#!/usr/bin/env python3
"""SAX instruction implementation for CMOS 65C02 variant.

On 65C02, all illegal opcodes act as NOPs.

The CMOS 65C02 replaced all illegal opcodes with defined behavior. Most became
NOPs with varying cycle counts. SAX opcodes on 65C02 consume the correct number
of cycles but perform no operation - no registers, flags, or memory are modified.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#SAX
  - https://wilsonminesco.com/NMOS-CMOSdif/
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sax_zeropage_0x87(cpu: "MOS6502CPU") -> None:
    """Execute SAX - Zero Page (acts as NOP on 65C02).

    Opcode: 0x87
    Cycles: 3
    Bytes: 2
    Flags: None affected

    VARIANT: 6502 - Stores A & X to memory (see _sax_6502.py)
    VARIANT: 6502A - Stores A & X to memory (see _sax_6502.py)
    VARIANT: 6502C - Stores A & X to memory (see _sax_6502.py)
    VARIANT: 65C02 - Acts as NOP (no operation)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch operand byte (consumed but not used)
    cpu.fetch_byte()

    # Internal cycles to match cycle count
    cpu.log.info("i")
    cpu.log.info("i")

    # No registers, flags, or memory modified


def sax_zeropage_y_0x97(cpu: "MOS6502CPU") -> None:
    """Execute SAX - Zero Page,Y (acts as NOP on 65C02).

    Opcode: 0x97
    Cycles: 4
    Bytes: 2
    Flags: None affected

    VARIANT: 6502 - Stores A & X to memory (see _sax_6502.py)
    VARIANT: 6502A - Stores A & X to memory (see _sax_6502.py)
    VARIANT: 6502C - Stores A & X to memory (see _sax_6502.py)
    VARIANT: 65C02 - Acts as NOP (no operation)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch operand byte (consumed but not used)
    cpu.fetch_byte()

    # Internal cycles to match cycle count
    cpu.log.info("i")
    cpu.log.info("i")
    cpu.log.info("i")

    # No registers, flags, or memory modified


def sax_indexed_indirect_x_0x83(cpu: "MOS6502CPU") -> None:
    """Execute SAX - (Indirect,X) (acts as NOP on 65C02).

    Opcode: 0x83
    Cycles: 6
    Bytes: 2
    Flags: None affected

    VARIANT: 6502 - Stores A & X to memory (see _sax_6502.py)
    VARIANT: 6502A - Stores A & X to memory (see _sax_6502.py)
    VARIANT: 6502C - Stores A & X to memory (see _sax_6502.py)
    VARIANT: 65C02 - Acts as NOP (no operation)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch operand byte (consumed but not used)
    cpu.fetch_byte()

    # Internal cycles to match cycle count
    for _ in range(5):
        cpu.log.info("i")

    # No registers, flags, or memory modified


def sax_absolute_0x8f(cpu: "MOS6502CPU") -> None:
    """Execute SAX - Absolute (acts as NOP on 65C02).

    Opcode: 0x8F
    Cycles: 4
    Bytes: 3
    Flags: None affected

    VARIANT: 6502 - Stores A & X to memory (see _sax_6502.py)
    VARIANT: 6502A - Stores A & X to memory (see _sax_6502.py)
    VARIANT: 6502C - Stores A & X to memory (see _sax_6502.py)
    VARIANT: 65C02 - Acts as NOP (no operation)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch address bytes (consumed but not used)
    cpu.fetch_word()

    # Internal cycles to match cycle count
    cpu.log.info("i")
    cpu.log.info("i")

    # No registers, flags, or memory modified
