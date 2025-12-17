#!/usr/bin/env python3
"""ANE (XAA) instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - HIGHLY UNSTABLE

ANE performs: A = (A | CONST) & X & immediate

The CONST value is configurable via cpu.unstable_config.ane_const to allow
emulating different chip behaviors.

VARIANT: 6502 - Uses configurable CONST (default 0xFF)
VARIANT: 6502A - Uses configurable CONST (default 0xFF)
VARIANT: 6502C - Uses configurable CONST (default 0xEE)
VARIANT: 65C02 - Acts as NOP (see _ane_65c02.py)

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes#Highly_unstable_opcodes
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def ane_immediate_0x8b(cpu: "MOS6502CPU") -> None:
    """Execute ANE (XAA) - Immediate addressing mode.

    Opcode: 0x8B
    Cycles: 2
    Bytes: 2
    Flags: N, Z

    HIGHLY UNSTABLE: Behavior varies between chips and conditions.

    Operation: A = (A | CONST) & X & immediate

    The CONST value comes from cpu.unstable_config.ane_const.
    Default is 0xFF for 6502/6502A, 0xEE for 6502C.

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    immediate: int = cpu.fetch_byte()

    # Get the "magic" CONST value from configuration
    const: int = cpu.unstable_config.ane_const
    if const is None:
        # Shouldn't happen for NMOS, but handle gracefully
        const = 0xFF

    # ANE operation: A = (A | CONST) & X & immediate
    result: int = (int(cpu.A) | const) & int(cpu.X) & immediate
    cpu.A = result & 0xFF

    # Set N and Z flags based on result
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")
