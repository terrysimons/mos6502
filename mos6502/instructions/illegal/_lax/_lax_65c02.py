#!/usr/bin/env python3
"""LAX instruction implementation for CMOS 65C02 variant.

On 65C02, all illegal opcodes act as NOPs.

The CMOS 65C02 replaced all illegal opcodes with defined behavior. Most became
NOPs with varying cycle counts. LAX opcodes on 65C02 consume the correct number
of cycles but perform no operation - no registers, flags, or memory are modified.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#LAX
  - https://wilsonminesco.com/NMOS-CMOSdif/
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def lax_zeropage_0xa7(cpu: MOS6502CPU) -> None:
    """Execute LAX - Zero Page (acts as NOP on 65C02).

    Opcode: 0xA7
    Cycles: 3
    Bytes: 2
    Flags: None affected

    VARIANT: 6502 - Loads memory into both A and X (see _lax_6502.py)
    VARIANT: 6502A - Loads memory into both A and X (see _lax_6502.py)
    VARIANT: 6502C - Loads memory into both A and X (see _lax_6502.py)
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


def lax_zeropage_y_0xb7(cpu: MOS6502CPU) -> None:
    """Execute LAX - Zero Page,Y (acts as NOP on 65C02).

    Opcode: 0xB7
    Cycles: 4
    Bytes: 2
    Flags: None affected

    VARIANT: 6502 - Loads memory into both A and X (see _lax_6502.py)
    VARIANT: 6502A - Loads memory into both A and X (see _lax_6502.py)
    VARIANT: 6502C - Loads memory into both A and X (see _lax_6502.py)
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


def lax_indexed_indirect_x_0xa3(cpu: MOS6502CPU) -> None:
    """Execute LAX - (Indirect,X) (acts as NOP on 65C02).

    Opcode: 0xA3
    Cycles: 6
    Bytes: 2
    Flags: None affected

    VARIANT: 6502 - Loads memory into both A and X (see _lax_6502.py)
    VARIANT: 6502A - Loads memory into both A and X (see _lax_6502.py)
    VARIANT: 6502C - Loads memory into both A and X (see _lax_6502.py)
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


def lax_indirect_indexed_y_0xb3(cpu: MOS6502CPU) -> None:
    """Execute LAX - (Indirect),Y (acts as NOP on 65C02).

    Opcode: 0xB3
    Cycles: 5*
    Bytes: 2
    Flags: None affected

    VARIANT: 6502 - Loads memory into both A and X (see _lax_6502.py)
    VARIANT: 6502A - Loads memory into both A and X (see _lax_6502.py)
    VARIANT: 6502C - Loads memory into both A and X (see _lax_6502.py)
    VARIANT: 65C02 - Acts as NOP (no operation)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch operand byte (consumed but not used)
    cpu.fetch_byte()

    # Internal cycles to match cycle count
    for _ in range(4):
        cpu.log.info("i")

    # No registers, flags, or memory modified


def lax_absolute_0xaf(cpu: MOS6502CPU) -> None:
    """Execute LAX - Absolute (acts as NOP on 65C02).

    Opcode: 0xAF
    Cycles: 4
    Bytes: 3
    Flags: None affected

    VARIANT: 6502 - Loads memory into both A and X (see _lax_6502.py)
    VARIANT: 6502A - Loads memory into both A and X (see _lax_6502.py)
    VARIANT: 6502C - Loads memory into both A and X (see _lax_6502.py)
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


def lax_absolute_y_0xbf(cpu: MOS6502CPU) -> None:
    """Execute LAX - Absolute,Y (acts as NOP on 65C02).

    Opcode: 0xBF
    Cycles: 4*
    Bytes: 3
    Flags: None affected

    VARIANT: 6502 - Loads memory into both A and X (see _lax_6502.py)
    VARIANT: 6502A - Loads memory into both A and X (see _lax_6502.py)
    VARIANT: 6502C - Loads memory into both A and X (see _lax_6502.py)
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


def lax_immediate_0xab(cpu: MOS6502CPU) -> None:
    """Execute LAX - Immediate (acts as NOP on 65C02).

    Opcode: 0xAB
    Cycles: 2
    Bytes: 2
    Flags: None affected

    VARIANT: 6502 - UNSTABLE illegal instruction (see _lax_6502.py)
    VARIANT: 6502A - UNSTABLE illegal instruction (see _lax_6502.py)
    VARIANT: 6502C - UNSTABLE illegal instruction (see _lax_6502.py)
    VARIANT: 65C02 - Acts as NOP (no operation)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch operand byte (consumed but not used)
    cpu.fetch_byte()

    # Internal cycle to match cycle count
    cpu.log.info("i")

    # No registers, flags, or memory modified
