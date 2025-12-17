#!/usr/bin/env python3
"""Illegal SBC (0xEB) instruction implementation for NMOS 6502 variants.

This is a duplicate of the legal SBC Immediate (0xE9) instruction.
Behavior is identical on all NMOS variants.

VARIANT: 6502 - Identical to SBC #imm (0xE9)
VARIANT: 6502A - Identical to SBC #imm (0xE9)
VARIANT: 6502C - Identical to SBC #imm (0xE9)

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sbc_immediate_0xeb(cpu: "MOS6502CPU") -> None:
    """Execute SBC (Subtract with Carry) - Immediate addressing mode.

    Opcode: 0xEB (illegal duplicate of 0xE9)
    Cycles: 2
    Bytes: 2
    Flags: N, Z, C, V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    value: int = cpu.fetch_byte()

    if cpu.flags[flags.D]:
        # BCD (Decimal) mode subtraction
        result, carry_out, overflow, _ = cpu._sbc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
    else:
        # Binary mode subtraction
        result: int = cpu.A - value - (1 - cpu.flags[flags.C])

        # Set Carry flag (inverted borrow): C=1 if no borrow (A >= M)
        cpu.flags[flags.C] = 1 if result >= 0 else 0

        # Set Overflow flag: V = (A^M) & (A^result) & 0x80
        # Overflow occurs if operands have different signs and result has different sign from A
        cpu.flags[flags.V] = 1 if ((cpu.A ^ value) & (cpu.A ^ result) & 0x80) else 0

        # Store result (masked to 8 bits)
        cpu.A = result & 0xFF

    # VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")
