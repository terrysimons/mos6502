#!/usr/bin/env python3
"""SHX (SXA, XAS) instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - UNSTABLE

SHX stores X & (high_byte + 1) to memory.

VARIANT: 6502 - Performs X & (H+1) store
VARIANT: 6502A - Performs X & (H+1) store
VARIANT: 6502C - Performs X & (H+1) store
VARIANT: 65C02 - Acts as NOP (see _shx_65c02.py)

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def shx_absolute_y_0x9e(cpu: "MOS6502CPU") -> None:
    """Execute SHX (SXA) - Absolute Y addressing mode.

    Opcode: 0x9E
    Cycles: 5
    Bytes: 3
    Flags: None affected

    UNSTABLE: Behavior varies between chips.

    Operation: Memory = X & (high_byte_of_address + 1)

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

    # Calculate the value to store: X & (high_byte + 1)
    value: int = int(cpu.X) & ((high_byte + 1) & 0xFF)

    # Store the value
    cpu.write_byte(address=effective_address, data=value)

    cpu.log.info("i")
