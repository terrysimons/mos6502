#!/usr/bin/env python3
"""SAX instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - NMOS only

SAX (Store A AND X) performs a bitwise AND operation between the accumulator
and X register, then stores the result to memory. Neither A nor X are modified.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#SAX
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sax_zeropage_0x87(cpu: "MOS6502CPU") -> None:
    """Execute SAX (Store A AND X) - Zero Page addressing mode.

    Opcode: 0x87
    Cycles: 3
    Bytes: 2
    Flags: None affected

    VARIANT: 6502 - Stores A & X to memory
    VARIANT: 6502A - Stores A & X to memory
    VARIANT: 6502C - Stores A & X to memory
    VARIANT: 65C02 - Acts as NOP (see _sax_65c02.py)

    Operation: M = A & X

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch zero page address
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)

    # Calculate A & X
    result: int = int(cpu.A) & int(cpu.X)

    # Store to memory
    cpu.write_byte(address=address, data=result)

    # Internal cycle
    cpu.log.info("i")


def sax_zeropage_y_0x97(cpu: "MOS6502CPU") -> None:
    """Execute SAX (Store A AND X) - Zero Page,Y addressing mode.

    Opcode: 0x97
    Cycles: 4
    Bytes: 2
    Flags: None affected

    VARIANT: 6502 - Stores A & X to memory
    VARIANT: 6502A - Stores A & X to memory
    VARIANT: 6502C - Stores A & X to memory
    VARIANT: 65C02 - Acts as NOP (see _sax_65c02.py)

    Operation: M = A & X

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch zero page,Y address
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="Y")

    # Calculate A & X
    result: int = int(cpu.A) & int(cpu.X)

    # Store to memory
    cpu.write_byte(address=address, data=result)

    # Internal cycle
    cpu.log.info("i")


def sax_indexed_indirect_x_0x83(cpu: "MOS6502CPU") -> None:
    """Execute SAX (Store A AND X) - (Indirect,X) addressing mode.

    Opcode: 0x83
    Cycles: 6
    Bytes: 2
    Flags: None affected

    VARIANT: 6502 - Stores A & X to memory
    VARIANT: 6502A - Stores A & X to memory
    VARIANT: 6502C - Stores A & X to memory
    VARIANT: 65C02 - Acts as NOP (see _sax_65c02.py)

    Operation: M = A & X

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Use existing helper for indexed indirect addressing
    address: int = cpu.fetch_indexed_indirect_mode_address()

    # Calculate A & X
    result: int = int(cpu.A) & int(cpu.X)

    # Store to memory
    cpu.write_byte(address=address, data=result)

    # Internal cycle
    cpu.log.info("i")


def sax_absolute_0x8f(cpu: "MOS6502CPU") -> None:
    """Execute SAX (Store A AND X) - Absolute addressing mode.

    Opcode: 0x8F
    Cycles: 4
    Bytes: 3
    Flags: None affected

    VARIANT: 6502 - Stores A & X to memory
    VARIANT: 6502A - Stores A & X to memory
    VARIANT: 6502C - Stores A & X to memory
    VARIANT: 65C02 - Acts as NOP (see _sax_65c02.py)

    Operation: M = A & X

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch absolute address
    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)

    # Calculate A & X
    result: int = int(cpu.A) & int(cpu.X)

    # Store to memory
    cpu.write_byte(address=address & 0xFFFF, data=result)

    # Internal cycle
    cpu.log.info("i")
