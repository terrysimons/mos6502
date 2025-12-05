#!/usr/bin/env python3
"""ADC instruction implementation for CMOS 65C02 variant."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def adc_immediate_0x69(cpu: MOS6502CPU) -> None:
    """Execute ADC (Add with Carry) - Immediate addressing mode - 65C02 variant.

    Opcode: 0x69
    Cycles: 2
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    value: int = cpu.fetch_byte()

    if cpu.flags[flags.D]:
        # BCD (Decimal) mode addition
        result, carry_out, overflow, binary_result = cpu._adc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result

        # VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result, not BCD result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        # Binary mode addition
        result: int = cpu.A + value + cpu.flags[flags.C]

        # Set Carry flag if result > 255
        cpu.flags[flags.C] = 1 if result > 0xFF else 0

        # Set Overflow flag: V = (A^result) & (M^result) & 0x80
        # Overflow occurs if both operands have same sign and result has different sign
        cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (value ^ result) & 0x80) else 0

        # Store result (masked to 8 bits)
        cpu.A = result & 0xFF

        # Set N and Z flags from binary result
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def adc_zeropage_0x65(cpu: MOS6502CPU) -> None:
    """Execute ADC (Add with Carry) - Zero Page addressing mode - 65C02 variant.

    Opcode: 0x65
    Cycles: 3
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._adc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A + value + cpu.flags[flags.C]
        cpu.flags[flags.C] = 1 if result > 0xFF else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (value ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("z")


def adc_zeropage_x_0x75(cpu: MOS6502CPU) -> None:
    """Execute ADC (Add with Carry) - Zero Page,X addressing mode - 65C02 variant.

    Opcode: 0x75
    Cycles: 4
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._adc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A + value + cpu.flags[flags.C]
        cpu.flags[flags.C] = 1 if result > 0xFF else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (value ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("zx")


def adc_absolute_0x6d(cpu: MOS6502CPU) -> None:
    """Execute ADC (Add with Carry) - Absolute addressing mode - 65C02 variant.

    Opcode: 0x6D
    Cycles: 4
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._adc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A + value + cpu.flags[flags.C]
        cpu.flags[flags.C] = 1 if result > 0xFF else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (value ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("a")


def adc_absolute_x_0x7d(cpu: MOS6502CPU) -> None:
    """Execute ADC (Add with Carry) - Absolute,X addressing mode - 65C02 variant.

    Opcode: 0x7D
    Cycles: 4* (add 1 if page boundary crossed)
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._adc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A + value + cpu.flags[flags.C]
        cpu.flags[flags.C] = 1 if result > 0xFF else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (value ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ax")


def adc_absolute_y_0x79(cpu: MOS6502CPU) -> None:
    """Execute ADC (Add with Carry) - Absolute,Y addressing mode - 65C02 variant.

    Opcode: 0x79
    Cycles: 4* (add 1 if page boundary crossed)
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name="Y")
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._adc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A + value + cpu.flags[flags.C]
        cpu.flags[flags.C] = 1 if result > 0xFF else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (value ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ay")


def adc_indexed_indirect_x_0x61(cpu: MOS6502CPU) -> None:
    """Execute ADC (Add with Carry) - Indexed Indirect (X) addressing mode - 65C02 variant.

    Opcode: 0x61
    Cycles: 6
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_indexed_indirect_mode_address()
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._adc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A + value + cpu.flags[flags.C]
        cpu.flags[flags.C] = 1 if result > 0xFF else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (value ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ix")


def adc_indirect_indexed_y_0x71(cpu: MOS6502CPU) -> None:
    """Execute ADC (Add with Carry) - Indirect Indexed (Y) addressing mode - 65C02 variant.

    Opcode: 0x71
    Cycles: 5* (add 1 if page boundary crossed)
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_indirect_indexed_mode_address()
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._adc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A + value + cpu.flags[flags.C]
        cpu.flags[flags.C] = 1 if result > 0xFF else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (value ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("iy")
