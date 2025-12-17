#!/usr/bin/env python3
"""LAS instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - NMOS only (UNSTABLE)

LAS (Load A, X, and S) performs M & S and stores the result in A, X, and S.
This is an unstable instruction and may behave unpredictably on real hardware.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#LAS
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def las_absolute_y_0xbb(cpu: "MOS6502CPU") -> None:
    """Execute LAS (Load A, X, and S) - Absolute,Y addressing mode.

    Opcode: 0xBB
    Cycles: 4*
    Bytes: 3
    Flags: N, Z

    VARIANT: 6502 - Loads (M & S) into A, X, and S (UNSTABLE)
    VARIANT: 6502A - Loads (M & S) into A, X, and S (UNSTABLE)
    VARIANT: 6502C - Loads (M & S) into A, X, and S (UNSTABLE)
    VARIANT: 65C02 - Acts as NOP (see _las_65c02.py)

    Operation: A, X, S = M & S

    WARNING: This is an unstable instruction with unpredictable behavior.

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name="Y")
    value: int = cpu.read_byte(address=address)

    # Perform M & S
    result: int = value & int(cpu.S)

    # Store result in A, X, and S
    cpu.A = result
    cpu.X = result
    cpu.S = result

    # Set N and Z flags based on result
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("ay")
