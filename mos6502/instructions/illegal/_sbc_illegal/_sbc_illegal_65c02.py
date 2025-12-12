#!/usr/bin/env python3
"""Illegal SBC (0xEB) instruction implementation for CMOS 65C02 variant.

This is a duplicate of the legal SBC Immediate (0xE9) instruction.
Behavior is identical to 0xE9 on 65C02.

VARIANT: 65C02 - Identical to SBC #imm (0xE9), N and Z from binary result in BCD mode

References:
  - http://www.oxyron.de/html/opcodes02.html
  - https://www.nesdev.org/wiki/CPU_unofficial_opcodes
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sbc_immediate_0xeb(cpu: MOS6502CPU) -> None:
    """Execute SBC (Subtract with Carry) - Immediate addressing mode - 65C02 variant.

    Opcode: 0xEB (illegal duplicate of 0xE9)
    Cycles: 2
    Bytes: 2
    Flags: N, Z, C, V

    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    value: int = cpu.fetch_byte()

    if cpu.flags[flags.D]:
        # BCD (Decimal) mode subtraction
        result, carry_out, overflow, binary_result = cpu._sbc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result

        # VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result, not BCD result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
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

        # Set N and Z flags from binary result
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")
