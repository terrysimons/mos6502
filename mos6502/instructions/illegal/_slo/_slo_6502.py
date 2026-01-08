#!/usr/bin/env python3
"""SLO instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - NMOS only

SLO (Shift Left and OR) shifts a memory location left by one bit, then
performs a bitwise OR with the accumulator. It is functionally equivalent
to executing ASL followed by ORA, but in a single instruction.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#SLO
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def slo_zeropage_0x07(cpu: "MOS6502CPU") -> None:
    """Execute SLO (Shift Left and OR) - Zero Page addressing mode.

    Opcode: 0x07
    Cycles: 5
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory left and ORs with A
    VARIANT: 6502A - Shifts memory left and ORs with A
    VARIANT: 6502C - Shifts memory left and ORs with A
    VARIANT: 65C02 - Acts as NOP (see _slo_65c02.py)

    Operation: M = M << 1, A = A | M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Fetch zero page address
    address: int = cpu.fetch_zeropage_mode_address(None)

    # Read value from memory
    value: int = cpu.read_byte(address)

    # Shift left (bit 7 goes to carry)
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    shifted: int = (value << 1) & 0xFF

    # Write shifted value back to memory
    cpu.write_byte(address, shifted)

    # OR with accumulator
    cpu.A = int(cpu.A) | shifted

    # Set N and Z flags based on accumulator
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    # Internal cycle
    cpu.log.info("i")


def slo_zeropage_x_0x17(cpu: "MOS6502CPU") -> None:
    """Execute SLO (Shift Left and OR) - Zero Page,X addressing mode.

    Opcode: 0x17
    Cycles: 6
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory left and ORs with A
    VARIANT: 6502A - Shifts memory left and ORs with A
    VARIANT: 6502C - Shifts memory left and ORs with A
    VARIANT: 65C02 - Acts as NOP (see _slo_65c02.py)

    Operation: M = M << 1, A = A | M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Fetch zero page,X address
    address: int = cpu.fetch_zeropage_mode_address("X")

    # Read value from memory
    value: int = cpu.read_byte(address)

    # Shift left (bit 7 goes to carry)
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    shifted: int = (value << 1) & 0xFF

    # Write shifted value back to memory
    cpu.write_byte(address, shifted)

    # OR with accumulator
    cpu.A = int(cpu.A) | shifted

    # Set N and Z flags based on accumulator
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    # Internal cycle
    cpu.log.info("i")


def slo_indexed_indirect_x_0x03(cpu: "MOS6502CPU") -> None:
    """Execute SLO (Shift Left and OR) - (Indirect,X) addressing mode.

    Opcode: 0x03
    Cycles: 8
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory left and ORs with A
    VARIANT: 6502A - Shifts memory left and ORs with A
    VARIANT: 6502C - Shifts memory left and ORs with A
    VARIANT: 65C02 - Acts as NOP (see _slo_65c02.py)

    Operation: M = M << 1, A = A | M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Use existing helper for indexed indirect addressing
    address: int = cpu.fetch_indexed_indirect_mode_address()

    # Read value from memory
    value: int = cpu.read_byte(address)

    # Shift left (bit 7 goes to carry)
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    shifted: int = (value << 1) & 0xFF

    # Write shifted value back to memory
    cpu.write_byte(address & 0xFFFF, shifted)

    # OR with accumulator
    cpu.A = int(cpu.A) | shifted

    # Set N and Z flags based on accumulator
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    # Internal cycle
    cpu.log.info("i")


def slo_indirect_indexed_y_0x13(cpu: "MOS6502CPU") -> None:
    """Execute SLO (Shift Left and OR) - (Indirect),Y addressing mode.

    Opcode: 0x13
    Cycles: 8
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory left and ORs with A
    VARIANT: 6502A - Shifts memory left and ORs with A
    VARIANT: 6502C - Shifts memory left and ORs with A
    VARIANT: 65C02 - Acts as NOP (see _slo_65c02.py)

    Operation: M = M << 1, A = A | M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Use existing helper for indirect indexed addressing
    address: int = cpu.fetch_indirect_indexed_mode_address()

    # Read value from memory
    value: int = cpu.read_byte(address)

    # Shift left (bit 7 goes to carry)
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    shifted: int = (value << 1) & 0xFF

    # Write shifted value back to memory
    cpu.write_byte(address & 0xFFFF, shifted)

    # OR with accumulator
    cpu.A = int(cpu.A) | shifted

    # Set N and Z flags based on accumulator
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    # Internal cycle
    cpu.log.info("i")


def slo_absolute_0x0f(cpu: "MOS6502CPU") -> None:
    """Execute SLO (Shift Left and OR) - Absolute addressing mode.

    Opcode: 0x0F
    Cycles: 6
    Bytes: 3
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory left and ORs with A
    VARIANT: 6502A - Shifts memory left and ORs with A
    VARIANT: 6502C - Shifts memory left and ORs with A
    VARIANT: 65C02 - Acts as NOP (see _slo_65c02.py)

    Operation: M = M << 1, A = A | M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    # Fetch absolute address
    address: int = cpu.fetch_absolute_mode_address(None)

    # Read value from memory
    value: int = cpu.read_byte(address)

    # Shift left (bit 7 goes to carry)
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    shifted: int = (value << 1) & 0xFF

    # Write shifted value back to memory
    cpu.write_byte(address & 0xFFFF, shifted)

    # OR with accumulator
    cpu.A = int(cpu.A) | shifted

    # Set N and Z flags based on accumulator
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    # Internal cycle
    cpu.log.info("i")


def slo_absolute_x_0x1f(cpu: "MOS6502CPU") -> None:
    """Execute SLO (Shift Left and OR) - Absolute,X addressing mode.

    Opcode: 0x1F
    Cycles: 7
    Bytes: 3
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory left and ORs with A
    VARIANT: 6502A - Shifts memory left and ORs with A
    VARIANT: 6502C - Shifts memory left and ORs with A
    VARIANT: 65C02 - Acts as NOP (see _slo_65c02.py)

    Operation: M = M << 1, A = A | M

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

    # Shift left (bit 7 goes to carry)
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    shifted: int = (value << 1) & 0xFF

    # Write shifted value back to memory
    cpu.write_byte(address & 0xFFFF, shifted)

    # OR with accumulator
    cpu.A = int(cpu.A) | shifted

    # Set N and Z flags based on accumulator
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ax")


def slo_absolute_y_0x1b(cpu: "MOS6502CPU") -> None:
    """Execute SLO (Shift Left and OR) - Absolute,Y addressing mode.

    Opcode: 0x1B
    Cycles: 7
    Bytes: 3
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory left and ORs with A
    VARIANT: 6502A - Shifts memory left and ORs with A
    VARIANT: 6502C - Shifts memory left and ORs with A
    VARIANT: 65C02 - Acts as NOP (see _slo_65c02.py)

    Operation: M = M << 1, A = A | M

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

    # Shift left (bit 7 goes to carry)
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    shifted: int = (value << 1) & 0xFF

    # Write shifted value back to memory
    cpu.write_byte(address & 0xFFFF, shifted)

    # OR with accumulator
    cpu.A = int(cpu.A) | shifted

    # Set N and Z flags based on accumulator
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ay")
