#!/usr/bin/env python3
"""LAX instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - NMOS only

LAX (Load A and X) loads a byte of memory into both the accumulator and
X register simultaneously. This is functionally equivalent to executing
LDA followed by LDX with the same operand, but in a single instruction.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#LAX
  - http://www.oxyron.de/html/opcodes02.html
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def lax_zeropage_0xa7(cpu: MOS6502CPU) -> None:
    """Execute LAX (Load A and X) - Zero Page addressing mode.

    Opcode: 0xA7
    Cycles: 3
    Bytes: 2
    Flags: N, Z

    VARIANT: 6502 - Loads memory into both A and X
    VARIANT: 6502A - Loads memory into both A and X
    VARIANT: 6502C - Loads memory into both A and X
    VARIANT: 65C02 - Acts as NOP (see _lax_65c02.py)

    Operation: A = M, X = M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch zero page address and read value
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)

    # Load into both A and X
    cpu.A = value
    cpu.X = value

    # Set flags based on loaded value
    cpu.Z = (value == 0x00)
    cpu.N = bool(value & 0x80)

    # Internal cycle
    cpu.log.info("i")


def lax_zeropage_y_0xb7(cpu: MOS6502CPU) -> None:
    """Execute LAX (Load A and X) - Zero Page,Y addressing mode.

    Opcode: 0xB7
    Cycles: 4
    Bytes: 2
    Flags: N, Z

    VARIANT: 6502 - Loads memory into both A and X
    VARIANT: 6502A - Loads memory into both A and X
    VARIANT: 6502C - Loads memory into both A and X
    VARIANT: 65C02 - Acts as NOP (see _lax_65c02.py)

    Operation: A = M, X = M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch zero page,Y address and read value
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="Y")
    value: int = cpu.read_byte(address=address)

    # Load into both A and X
    cpu.A = value
    cpu.X = value

    # Set flags based on loaded value
    cpu.Z = (value == 0x00)
    cpu.N = bool(value & 0x80)

    # Internal cycle
    cpu.log.info("i")


def lax_indexed_indirect_x_0xa3(cpu: MOS6502CPU) -> None:
    """Execute LAX (Load A and X) - (Indirect,X) addressing mode.

    Opcode: 0xA3
    Cycles: 6
    Bytes: 2
    Flags: N, Z

    VARIANT: 6502 - Loads memory into both A and X
    VARIANT: 6502A - Loads memory into both A and X
    VARIANT: 6502C - Loads memory into both A and X
    VARIANT: 65C02 - Acts as NOP (see _lax_65c02.py)

    Operation: A = M, X = M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Use existing helper for indexed indirect addressing
    address: int = cpu.fetch_indexed_indirect_mode_address()
    value: int = cpu.read_byte(address=address)

    # Load into both A and X
    cpu.A = value
    cpu.X = value

    # Set flags based on loaded value
    cpu.Z = (value == 0x00)
    cpu.N = bool(value & 0x80)

    # Internal cycle
    cpu.log.info("i")


def lax_indirect_indexed_y_0xb3(cpu: MOS6502CPU) -> None:
    """Execute LAX (Load A and X) - (Indirect),Y addressing mode.

    Opcode: 0xB3
    Cycles: 5*
    Bytes: 2
    Flags: N, Z

    VARIANT: 6502 - Loads memory into both A and X
    VARIANT: 6502A - Loads memory into both A and X
    VARIANT: 6502C - Loads memory into both A and X
    VARIANT: 65C02 - Acts as NOP (see _lax_65c02.py)

    Operation: A = M, X = M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Use existing helper for indirect indexed addressing
    address: int = cpu.fetch_indirect_indexed_mode_address()
    value: int = cpu.read_byte(address=address)

    # Load into both A and X
    cpu.A = value
    cpu.X = value

    # Set flags based on loaded value
    cpu.Z = (value == 0x00)
    cpu.N = bool(value & 0x80)

    # Internal cycle
    cpu.log.info("i")


def lax_absolute_0xaf(cpu: MOS6502CPU) -> None:
    """Execute LAX (Load A and X) - Absolute addressing mode.

    Opcode: 0xAF
    Cycles: 4
    Bytes: 3
    Flags: N, Z

    VARIANT: 6502 - Loads memory into both A and X
    VARIANT: 6502A - Loads memory into both A and X
    VARIANT: 6502C - Loads memory into both A and X
    VARIANT: 65C02 - Acts as NOP (see _lax_65c02.py)

    Operation: A = M, X = M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch absolute address and read value
    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)

    # Load into both A and X
    cpu.A = value
    cpu.X = value

    # Set flags based on loaded value
    cpu.Z = (value == 0x00)
    cpu.N = bool(value & 0x80)

    # Internal cycle
    cpu.log.info("i")


def lax_absolute_y_0xbf(cpu: MOS6502CPU) -> None:
    """Execute LAX (Load A and X) - Absolute,Y addressing mode.

    Opcode: 0xBF
    Cycles: 4*
    Bytes: 3
    Flags: N, Z

    VARIANT: 6502 - Loads memory into both A and X
    VARIANT: 6502A - Loads memory into both A and X
    VARIANT: 6502C - Loads memory into both A and X
    VARIANT: 65C02 - Acts as NOP (see _lax_65c02.py)

    Operation: A = M, X = M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Use existing helper for absolute Y addressing
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="Y")
    value: int = cpu.read_byte(address=address)

    # Load into both A and X
    cpu.A = value
    cpu.X = value

    # Set flags based on loaded value
    cpu.Z = (value == 0x00)
    cpu.N = bool(value & 0x80)

    # Internal cycle
    cpu.log.info("i")


def lax_immediate_0xab(cpu: MOS6502CPU) -> None:
    """Execute LAX (Load A and X) - Immediate addressing mode.

    Opcode: 0xAB
    Cycles: 2
    Bytes: 2
    Flags: N, Z

    WARNING: HIGHLY UNSTABLE INSTRUCTION
    This opcode is extremely unstable and may produce different results
    on different chip revisions, temperatures, and manufacturing runs.

    The actual operation is: (A | CONST) & immediate → A → X
    where CONST is an undefined magic constant that varies by chip.

    VARIANT: 6502 - UNSTABLE - behavior varies
    VARIANT: 6502A - UNSTABLE - behavior varies
    VARIANT: 6502C - UNSTABLE - behavior varies
    VARIANT: 65C02 - Acts as NOP (see _lax_65c02.py)

    DO NOT USE THIS INSTRUCTION IN PRODUCTION CODE

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    # Fetch immediate value
    value: int = int(cpu.fetch_immediate_mode_address())

    # UNSTABLE BEHAVIOR WARNING
    # Real hardware: result = (cpu.A | MAGIC_CONST) & value
    # MAGIC_CONST varies and is unpredictable
    # For emulation, we use 0xFF (most permissive) with a warning
    cpu.log.warning(
        "LAX #$%02X: UNSTABLE illegal instruction - "
        "behavior may differ from real hardware", value
    )

    # Simplified emulation: use current A value ORed with 0xFF
    # Real hardware behavior is more complex and unpredictable
    result: int = (int(cpu.A) | 0xFF) & value

    # Load into both A and X
    cpu.A = result
    cpu.X = result

    # Set flags based on result
    cpu.Z = (result == 0x00)
    cpu.N = bool(result & 0x80)

    # Internal cycle
    cpu.log.info("i")
