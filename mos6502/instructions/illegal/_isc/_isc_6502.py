#!/usr/bin/env python3
"""ISC instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - NMOS only

ISC (Increment and Subtract with Carry) increments a memory location, then
subtracts the result from the accumulator with the carry flag. It is functionally
equivalent to executing INC followed by SBC, but in a single instruction.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#ISC
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def isc_zeropage_0xe7(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - Zero Page addressing mode.

    Opcode: 0xE7
    Cycles: 5
    Bytes: 2
    Flags: N, Z, C, V

    VARIANT: 6502 - Increments memory and subtracts from A with carry
    VARIANT: 6502A - Increments memory and subtracts from A with carry
    VARIANT: 6502C - Increments memory and subtracts from A with carry
    VARIANT: 65C02 - Acts as NOP (see _isc_65c02.py)

    Operation: M = M + 1, A = A - M - (1 - C)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Fetch zero page address
    address: int = cpu.fetch_zeropage_mode_address(None)

    # Read value from memory
    value: int = cpu.read_byte(address)

    # Increment value
    incremented: int = (value + 1) & 0xFF

    # Write incremented value back to memory
    cpu.write_byte(address, incremented)

    # Subtract incremented value from A with carry (like SBC)
    if cpu.flags[flags.D]:
        result, carry_out, overflow, _ = cpu._sbc_bcd(cpu.A, incremented, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
    else:
        result: int = cpu.A - incremented - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ incremented) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    # Internal cycle
    cpu.log.info("i")


def isc_zeropage_x_0xf7(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - Zero Page,X addressing mode.

    Opcode: 0xF7
    Cycles: 6
    Bytes: 2
    Flags: N, Z, C, V

    VARIANT: 6502 - Increments memory and subtracts from A with carry
    VARIANT: 6502A - Increments memory and subtracts from A with carry
    VARIANT: 6502C - Increments memory and subtracts from A with carry
    VARIANT: 65C02 - Acts as NOP (see _isc_65c02.py)

    Operation: M = M + 1, A = A - M - (1 - C)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Fetch zero page,X address
    address: int = cpu.fetch_zeropage_mode_address("X")

    # Read value from memory
    value: int = cpu.read_byte(address)

    # Increment value
    incremented: int = (value + 1) & 0xFF

    # Write incremented value back to memory
    cpu.write_byte(address, incremented)

    # Subtract incremented value from A with carry
    if cpu.flags[flags.D]:
        result, carry_out, overflow, _ = cpu._sbc_bcd(cpu.A, incremented, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
    else:
        result: int = cpu.A - incremented - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ incremented) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    # Internal cycle
    cpu.log.info("i")


def isc_indexed_indirect_x_0xe3(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - (Indirect,X) addressing mode.

    Opcode: 0xE3
    Cycles: 8
    Bytes: 2
    Flags: N, Z, C, V

    VARIANT: 6502 - Increments memory and subtracts from A with carry
    VARIANT: 6502A - Increments memory and subtracts from A with carry
    VARIANT: 6502C - Increments memory and subtracts from A with carry
    VARIANT: 65C02 - Acts as NOP (see _isc_65c02.py)

    Operation: M = M + 1, A = A - M - (1 - C)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Use existing helper for indexed indirect addressing
    address: int = cpu.fetch_indexed_indirect_mode_address()

    # Read value from memory
    value: int = cpu.read_byte(address)

    # Increment value
    incremented: int = (value + 1) & 0xFF

    # Write incremented value back to memory
    cpu.write_byte(address & 0xFFFF, incremented)

    # Subtract incremented value from A with carry
    if cpu.flags[flags.D]:
        result, carry_out, overflow, _ = cpu._sbc_bcd(cpu.A, incremented, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
    else:
        result: int = cpu.A - incremented - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ incremented) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    # Internal cycle
    cpu.log.info("i")


def isc_indirect_indexed_y_0xf3(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - (Indirect),Y addressing mode.

    Opcode: 0xF3
    Cycles: 8
    Bytes: 2
    Flags: N, Z, C, V

    VARIANT: 6502 - Increments memory and subtracts from A with carry
    VARIANT: 6502A - Increments memory and subtracts from A with carry
    VARIANT: 6502C - Increments memory and subtracts from A with carry
    VARIANT: 65C02 - Acts as NOP (see _isc_65c02.py)

    Operation: M = M + 1, A = A - M - (1 - C)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Use existing helper for indirect indexed addressing
    address: int = cpu.fetch_indirect_indexed_mode_address()

    # Read value from memory
    value: int = cpu.read_byte(address)

    # Increment value
    incremented: int = (value + 1) & 0xFF

    # Write incremented value back to memory
    cpu.write_byte(address & 0xFFFF, incremented)

    # Subtract incremented value from A with carry
    if cpu.flags[flags.D]:
        result, carry_out, overflow, _ = cpu._sbc_bcd(cpu.A, incremented, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
    else:
        result: int = cpu.A - incremented - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ incremented) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    # Internal cycle
    cpu.log.info("i")


def isc_absolute_0xef(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - Absolute addressing mode.

    Opcode: 0xEF
    Cycles: 6
    Bytes: 3
    Flags: N, Z, C, V

    VARIANT: 6502 - Increments memory and subtracts from A with carry
    VARIANT: 6502A - Increments memory and subtracts from A with carry
    VARIANT: 6502C - Increments memory and subtracts from A with carry
    VARIANT: 65C02 - Acts as NOP (see _isc_65c02.py)

    Operation: M = M + 1, A = A - M - (1 - C)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Fetch absolute address
    address: int = cpu.fetch_absolute_mode_address(None)

    # Read value from memory
    value: int = cpu.read_byte(address)

    # Increment value
    incremented: int = (value + 1) & 0xFF

    # Write incremented value back to memory
    cpu.write_byte(address & 0xFFFF, incremented)

    # Subtract incremented value from A with carry
    if cpu.flags[flags.D]:
        result, carry_out, overflow, _ = cpu._sbc_bcd(cpu.A, incremented, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
    else:
        result: int = cpu.A - incremented - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ incremented) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    # Internal cycle
    cpu.log.info("i")


def isc_absolute_x_0xff(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - Absolute,X addressing mode.

    Opcode: 0xFF
    Cycles: 7
    Bytes: 3
    Flags: N, Z, C, V

    VARIANT: 6502 - Increments memory and subtracts from A with carry
    VARIANT: 6502A - Increments memory and subtracts from A with carry
    VARIANT: 6502C - Increments memory and subtracts from A with carry
    VARIANT: 65C02 - Acts as NOP (see _isc_65c02.py)

    Operation: M = M + 1, A = A - M - (1 - C)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Use existing helper for absolute X addressing
    address: int = cpu.fetch_absolute_mode_address("X")

    # Read-Modify-Write with Absolute,X always does a dummy read regardless of page crossing
    cpu.spend_cpu_cycles(1)

    # Read value from memory
    value: int = cpu.read_byte(address)

    # Internal processing cycle for RMW operation
    cpu.spend_cpu_cycles(1)

    # Increment value
    incremented: int = (value + 1) & 0xFF

    # Write incremented value back to memory
    cpu.write_byte(address & 0xFFFF, incremented)

    # Subtract incremented value from A with carry
    if cpu.flags[flags.D]:
        result, carry_out, overflow, _ = cpu._sbc_bcd(cpu.A, incremented, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
    else:
        result: int = cpu.A - incremented - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ incremented) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ax")


def isc_absolute_y_0xfb(cpu: "MOS6502CPU") -> None:
    """Execute ISC (Increment and Subtract with Carry) - Absolute,Y addressing mode.

    Opcode: 0xFB
    Cycles: 7
    Bytes: 3
    Flags: N, Z, C, V

    VARIANT: 6502 - Increments memory and subtracts from A with carry
    VARIANT: 6502A - Increments memory and subtracts from A with carry
    VARIANT: 6502C - Increments memory and subtracts from A with carry
    VARIANT: 65C02 - Acts as NOP (see _isc_65c02.py)

    Operation: M = M + 1, A = A - M - (1 - C)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Use existing helper for absolute Y addressing
    address: int = cpu.fetch_absolute_mode_address("Y")

    # Read-Modify-Write with Absolute,Y always does a dummy read regardless of page crossing
    cpu.spend_cpu_cycles(1)

    # Read value from memory
    value: int = cpu.read_byte(address & 0xFFFF)

    # Internal processing cycle for RMW operation
    cpu.spend_cpu_cycles(1)

    # Increment value
    incremented: int = (value + 1) & 0xFF

    # Write incremented value back to memory
    cpu.write_byte(address & 0xFFFF, incremented)

    # Subtract incremented value from A with carry
    if cpu.flags[flags.D]:
        result, carry_out, overflow, _ = cpu._sbc_bcd(cpu.A, incremented, cpu.flags[flags.C])
        cpu.flags[flags.C] = carry_out
        cpu.flags[flags.V] = overflow
        cpu.A = result
    else:
        result: int = cpu.A - incremented - (1 - cpu.flags[flags.C])
        cpu.flags[flags.C] = 1 if result >= 0 else 0
        cpu.flags[flags.V] = 1 if ((cpu.A ^ incremented) & (cpu.A ^ result) & 0x80) else 0
        cpu.A = result & 0xFF

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ay")
