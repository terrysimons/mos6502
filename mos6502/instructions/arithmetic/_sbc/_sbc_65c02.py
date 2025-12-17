#!/usr/bin/env python3
"""SBC instruction implementation for CMOS 65C02 variant."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sbc_immediate_0xe9(cpu: "MOS6502CPU") -> None:
    """Execute SBC (Subtract with Carry) - Immediate addressing mode - 65C02 variant.

    Opcode: 0xE9
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


def sbc_zeropage_0xe5(cpu: "MOS6502CPU") -> None:
    """Execute SBC (Subtract with Carry) - Zero Page addressing mode - 65C02 variant.

    Opcode: 0xE5
    Cycles: 3
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._sbc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A - value - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ value) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("z")


def sbc_zeropage_x_0xf5(cpu: "MOS6502CPU") -> None:
    """Execute SBC (Subtract with Carry) - Zero Page,X addressing mode - 65C02 variant.

    Opcode: 0xF5
    Cycles: 4
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._sbc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A - value - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ value) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("zx")


def sbc_absolute_0xed(cpu: "MOS6502CPU") -> None:
    """Execute SBC (Subtract with Carry) - Absolute addressing mode - 65C02 variant.

    Opcode: 0xED
    Cycles: 4
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._sbc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A - value - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ value) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("a")


def sbc_absolute_x_0xfd(cpu: "MOS6502CPU") -> None:
    """Execute SBC (Subtract with Carry) - Absolute,X addressing mode - 65C02 variant.

    Opcode: 0xFD
    Cycles: 4* (add 1 if page boundary crossed)
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._sbc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A - value - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ value) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ax")


def sbc_absolute_y_0xf9(cpu: "MOS6502CPU") -> None:
    """Execute SBC (Subtract with Carry) - Absolute,Y addressing mode - 65C02 variant.

    Opcode: 0xF9
    Cycles: 4* (add 1 if page boundary crossed)
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name="Y")
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._sbc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A - value - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ value) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ay")


def sbc_indexed_indirect_x_0xe1(cpu: "MOS6502CPU") -> None:
    """Execute SBC (Subtract with Carry) - Indexed Indirect (X) addressing mode - 65C02 variant.

    Opcode: 0xE1
    Cycles: 6
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_indexed_indirect_mode_address()
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._sbc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A - value - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ value) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ix")


def sbc_indirect_indexed_y_0xf1(cpu: "MOS6502CPU") -> None:
    """Execute SBC (Subtract with Carry) - Indirect Indexed (Y) addressing mode - 65C02 variant.

    Opcode: 0xF1
    Cycles: 5* (add 1 if page boundary crossed)
    Flags: N Z C V

    VARIANT: 6502 (NMOS) - N and Z flags are set from BCD result in decimal mode
    VARIANT: 65C02 (CMOS) - N and Z flags are set from binary result in decimal mode
    """
    from mos6502 import flags

    address: int = cpu.fetch_indirect_indexed_mode_address()
    value: int = cpu.read_byte(address=address)

    if cpu.flags[flags.D]:
        result, carry_out, overflow, binary_result = cpu._sbc_bcd(cpu.A, value, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
        cpu.flags[flags.Z] = 1 if (binary_result & 0xFF) == 0 else 0
        cpu.flags[flags.N] = 1 if ((binary_result & 0xFF) & 0x80) else 0
    else:
        result: int = cpu.A - value - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ value) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF
        cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
        cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("iy")
