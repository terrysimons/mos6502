#!/usr/bin/env python3
"""TAS (XAS, SHS) instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - UNSTABLE

TAS performs:
1. S = A & X (store A AND X into stack pointer)
2. Memory = A & X & (high_byte + 1)

VARIANT: 6502 - Performs both operations
VARIANT: 6502A - Performs both operations
VARIANT: 6502C - Performs both operations
VARIANT: 65C02 - Acts as NOP (see _tas_65c02.py)

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def tas_absolute_y_0x9b(cpu: "MOS6502CPU") -> None:
    """Execute TAS (XAS, SHS) - Absolute Y addressing mode.

    Opcode: 0x9B
    Cycles: 5
    Bytes: 3
    Flags: None affected

    UNSTABLE: Behavior varies between chips.

    Operation:
    1. S = A & X
    2. Memory = A & X & (high_byte_of_address + 1)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Check if unstable stores are enabled
    if not cpu.unstable_config.unstable_stores_enabled:
        # Act as NOP - just fetch operands to advance PC
        cpu.fetch_byte()
        cpu.fetch_byte()
        cpu.log.info("i")
        return

    # Fetch absolute address
    low_byte: int = cpu.fetch_byte()
    high_byte: int = cpu.fetch_byte()

    # Calculate A & X
    a_and_x: int = int(cpu.A) & int(cpu.X)

    # Operation 1: S = A & X
    # Note: Stack pointer is stored with 0x100 offset internally
    cpu.S = 0x100 | (a_and_x & 0xFF)

    # Calculate effective address
    base_address: int = (high_byte << 8) | low_byte
    effective_address: int = (base_address + int(cpu.Y)) & 0xFFFF

    # Operation 2: Memory = A & X & (high_byte + 1)
    value: int = a_and_x & ((high_byte + 1) & 0xFF)

    # Store the value
    cpu.write_byte(effective_address, value)

    cpu.log.info("i")
