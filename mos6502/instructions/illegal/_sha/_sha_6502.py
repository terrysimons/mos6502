#!/usr/bin/env python3
"""SHA (AHX, AXA) instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - UNSTABLE

SHA stores A & X & (high_byte + 1) to memory.

The "high_byte + 1" component makes this instruction behave unusually.
On page boundary crossing, the behavior may vary.

VARIANT: 6502 - Performs A & X & (H+1) store
VARIANT: 6502A - Performs A & X & (H+1) store
VARIANT: 6502C - Performs A & X & (H+1) store
VARIANT: 65C02 - Acts as NOP (see _sha_65c02.py)

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sha_indirect_indexed_y_0x93(cpu: "MOS6502CPU") -> None:
    """Execute SHA (AHX) - Indirect Indexed Y addressing mode.

    Opcode: 0x93
    Cycles: 6
    Bytes: 2
    Flags: None affected

    UNSTABLE: Behavior varies between chips.

    Operation: Memory = A & X & (high_byte_of_address + 1)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Check if unstable stores are enabled
    if not cpu.unstable_config.unstable_stores_enabled:
        # Act as NOP - just fetch operand to advance PC
        cpu.fetch_byte()
        cpu.log.info("i")
        return

    # Fetch zero page address
    zp_address: int = cpu.fetch_byte()

    # Read the base address from zero page (little endian)
    low_byte: int = cpu.read_byte(zp_address)
    high_byte: int = cpu.read_byte((zp_address + 1) & 0xFF)  # Wrap within zero page

    # Calculate effective address
    base_address: int = (high_byte << 8) | low_byte
    effective_address: int = (base_address + int(cpu.Y)) & 0xFFFF

    # Calculate the value to store: A & X & (high_byte + 1)
    # Note: We use the high byte of the base address, not the effective address
    value: int = int(cpu.A) & int(cpu.X) & ((high_byte + 1) & 0xFF)

    # Store the value
    cpu.write_byte(effective_address, value)

    cpu.log.info("i")


def sha_absolute_y_0x9f(cpu: "MOS6502CPU") -> None:
    """Execute SHA (AHX) - Absolute Y addressing mode.

    Opcode: 0x9F
    Cycles: 5
    Bytes: 3
    Flags: None affected

    UNSTABLE: Behavior varies between chips.

    Operation: Memory = A & X & (high_byte_of_address + 1)

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

    # Calculate effective address
    base_address: int = (high_byte << 8) | low_byte
    effective_address: int = (base_address + int(cpu.Y)) & 0xFFFF

    # Calculate the value to store: A & X & (high_byte + 1)
    value: int = int(cpu.A) & int(cpu.X) & ((high_byte + 1) & 0xFF)

    # Store the value
    cpu.write_byte(effective_address, value)

    cpu.log.info("i")
