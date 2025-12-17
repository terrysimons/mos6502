#!/usr/bin/env python3
"""DCP instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - NMOS only

DCP (Decrement and Compare) decrements a memory location, then compares
the result with the accumulator. It is functionally equivalent to executing
DEC followed by CMP, but in a single instruction.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#DCP
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def dcp_zeropage_0xc7(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - Zero Page addressing mode.

    Opcode: 0xC7
    Cycles: 5
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Decrements memory and compares with A
    VARIANT: 6502A - Decrements memory and compares with A
    VARIANT: 6502C - Decrements memory and compares with A
    VARIANT: 65C02 - Acts as NOP (see _dcp_65c02.py)

    Operation: M = M - 1, Compare(A, M)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Fetch zero page address
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)

    # Read value from memory
    value: int = cpu.read_byte(address=address)

    # Decrement value
    decremented: int = (value - 1) & 0xFF

    # Write decremented value back to memory
    cpu.write_byte(address=address, data=decremented)

    # Compare A with decremented value (like CMP)
    result: int = (int(cpu.A) - decremented) & 0xFF
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if int(cpu.A) >= decremented else 0

    # Internal cycle
    cpu.log.info("i")


def dcp_zeropage_x_0xd7(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - Zero Page,X addressing mode.

    Opcode: 0xD7
    Cycles: 6
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Decrements memory and compares with A
    VARIANT: 6502A - Decrements memory and compares with A
    VARIANT: 6502C - Decrements memory and compares with A
    VARIANT: 65C02 - Acts as NOP (see _dcp_65c02.py)

    Operation: M = M - 1, Compare(A, M)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Fetch zero page,X address
    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")

    # Read value from memory
    value: int = cpu.read_byte(address=address)

    # Decrement value
    decremented: int = (value - 1) & 0xFF

    # Write decremented value back to memory
    cpu.write_byte(address=address, data=decremented)

    # Compare A with decremented value
    result: int = (int(cpu.A) - decremented) & 0xFF
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if int(cpu.A) >= decremented else 0

    # Internal cycle
    cpu.log.info("i")


def dcp_indexed_indirect_x_0xc3(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - (Indirect,X) addressing mode.

    Opcode: 0xC3
    Cycles: 8
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Decrements memory and compares with A
    VARIANT: 6502A - Decrements memory and compares with A
    VARIANT: 6502C - Decrements memory and compares with A
    VARIANT: 65C02 - Acts as NOP (see _dcp_65c02.py)

    Operation: M = M - 1, Compare(A, M)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Use existing helper for indexed indirect addressing
    address: int = cpu.fetch_indexed_indirect_mode_address()

    # Read value from memory
    value: int = cpu.read_byte(address=address)

    # Decrement value
    decremented: int = (value - 1) & 0xFF

    # Write decremented value back to memory
    cpu.write_byte(address=address & 0xFFFF, data=decremented)

    # Compare A with decremented value
    result: int = (int(cpu.A) - decremented) & 0xFF
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if int(cpu.A) >= decremented else 0

    # Internal cycle
    cpu.log.info("i")


def dcp_indirect_indexed_y_0xd3(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - (Indirect),Y addressing mode.

    Opcode: 0xD3
    Cycles: 8
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Decrements memory and compares with A
    VARIANT: 6502A - Decrements memory and compares with A
    VARIANT: 6502C - Decrements memory and compares with A
    VARIANT: 65C02 - Acts as NOP (see _dcp_65c02.py)

    Operation: M = M - 1, Compare(A, M)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Use existing helper for indirect indexed addressing
    address: int = cpu.fetch_indirect_indexed_mode_address()

    # Read value from memory
    value: int = cpu.read_byte(address=address)

    # Decrement value
    decremented: int = (value - 1) & 0xFF

    # Write decremented value back to memory
    cpu.write_byte(address=address & 0xFFFF, data=decremented)

    # Compare A with decremented value
    result: int = (int(cpu.A) - decremented) & 0xFF
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if int(cpu.A) >= decremented else 0

    # Internal cycle
    cpu.log.info("i")


def dcp_absolute_0xcf(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - Absolute addressing mode.

    Opcode: 0xCF
    Cycles: 6
    Bytes: 3
    Flags: N, Z, C

    VARIANT: 6502 - Decrements memory and compares with A
    VARIANT: 6502A - Decrements memory and compares with A
    VARIANT: 6502C - Decrements memory and compares with A
    VARIANT: 65C02 - Acts as NOP (see _dcp_65c02.py)

    Operation: M = M - 1, Compare(A, M)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Fetch absolute address
    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)

    # Read value from memory
    value: int = cpu.read_byte(address=address)

    # Decrement value
    decremented: int = (value - 1) & 0xFF

    # Write decremented value back to memory
    cpu.write_byte(address=address & 0xFFFF, data=decremented)

    # Compare A with decremented value
    result: int = (int(cpu.A) - decremented) & 0xFF
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if int(cpu.A) >= decremented else 0

    # Internal cycle
    cpu.log.info("i")


def dcp_absolute_x_0xdf(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - Absolute,X addressing mode.

    Opcode: 0xDF
    Cycles: 7
    Bytes: 3
    Flags: N, Z, C

    VARIANT: 6502 - Decrements memory and compares with A
    VARIANT: 6502A - Decrements memory and compares with A
    VARIANT: 6502C - Decrements memory and compares with A
    VARIANT: 65C02 - Acts as NOP (see _dcp_65c02.py)

    Operation: M = M - 1, Compare(A, M)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Use existing helper for absolute X addressing
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")

    # Read-Modify-Write with Absolute,X always does a dummy read regardless of page crossing
    cpu.spend_cpu_cycles(1)

    # Read value from memory
    value: int = cpu.read_byte(address=address)

    # Internal processing cycle for RMW operation
    cpu.spend_cpu_cycles(1)

    # Decrement value
    decremented: int = (value - 1) & 0xFF

    # Write decremented value back to memory
    cpu.write_byte(address=address & 0xFFFF, data=decremented)

    # Compare A with decremented value
    result: int = (int(cpu.A) - decremented) & 0xFF
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if int(cpu.A) >= decremented else 0

    cpu.log.info("ax")


def dcp_absolute_y_0xdb(cpu: "MOS6502CPU") -> None:
    """Execute DCP (Decrement and Compare) - Absolute,Y addressing mode.

    Opcode: 0xDB
    Cycles: 7
    Bytes: 3
    Flags: N, Z, C

    VARIANT: 6502 - Decrements memory and compares with A
    VARIANT: 6502A - Decrements memory and compares with A
    VARIANT: 6502C - Decrements memory and compares with A
    VARIANT: 65C02 - Acts as NOP (see _dcp_65c02.py)

    Operation: M = M - 1, Compare(A, M)

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Use existing helper for absolute Y addressing
    address: int = cpu.fetch_absolute_mode_address(offset_register_name="Y")

    # Read-Modify-Write with Absolute,Y always does a dummy read regardless of page crossing
    cpu.spend_cpu_cycles(1)

    # Read value from memory
    value: int = cpu.read_byte(address=address & 0xFFFF)

    # Internal processing cycle for RMW operation
    cpu.spend_cpu_cycles(1)

    # Decrement value
    decremented: int = (value - 1) & 0xFF

    # Write decremented value back to memory
    cpu.write_byte(address=address & 0xFFFF, data=decremented)

    # Compare A with decremented value
    result: int = (int(cpu.A) - decremented) & 0xFF
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0
    cpu.flags[flags.C] = 1 if int(cpu.A) >= decremented else 0

    cpu.log.info("ay")
