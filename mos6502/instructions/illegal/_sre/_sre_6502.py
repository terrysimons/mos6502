#!/usr/bin/env python3
"""SRE instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - NMOS only

SRE (Shift Right and EOR) shifts a memory location right by one bit,
then performs a bitwise EOR with the accumulator. It is functionally equivalent
to executing LSR followed by EOR, but in a single instruction.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#SRE
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def sre_zeropage_0x47(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - Zero Page addressing mode.

    Opcode: 0x47
    Cycles: 5
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory right and EORs with A
    VARIANT: 6502A - Shifts memory right and EORs with A
    VARIANT: 6502C - Shifts memory right and EORs with A
    VARIANT: 65C02 - Acts as NOP (see _sre_65c02.py)

    Operation: M = LSR(M), A = A ^ M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(None)
    value: int = cpu.read_byte(address)

    # Shift right (bit 0 goes to carry)
    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    shifted: int = (value >> 1) & 0xFF

    # Write shifted value back to memory
    cpu.write_byte(address, shifted)

    # EOR with accumulator
    cpu.A = int(cpu.A) ^ shifted

    # Set N and Z flags based on accumulator
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def sre_zeropage_x_0x57(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - Zero Page,X addressing mode.

    Opcode: 0x57
    Cycles: 6
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory right and EORs with A
    VARIANT: 6502A - Shifts memory right and EORs with A
    VARIANT: 6502C - Shifts memory right and EORs with A
    VARIANT: 65C02 - Acts as NOP (see _sre_65c02.py)

    Operation: M = LSR(M), A = A ^ M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address("X")
    value: int = cpu.read_byte(address)

    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    shifted: int = (value >> 1) & 0xFF

    cpu.write_byte(address, shifted)

    cpu.A = int(cpu.A) ^ shifted

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def sre_indexed_indirect_x_0x43(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - (Indirect,X) addressing mode.

    Opcode: 0x43
    Cycles: 8
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory right and EORs with A
    VARIANT: 6502A - Shifts memory right and EORs with A
    VARIANT: 6502C - Shifts memory right and EORs with A
    VARIANT: 65C02 - Acts as NOP (see _sre_65c02.py)

    Operation: M = LSR(M), A = A ^ M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_indexed_indirect_mode_address()
    value: int = cpu.read_byte(address)

    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    shifted: int = (value >> 1) & 0xFF

    cpu.write_byte(address & 0xFFFF, shifted)

    cpu.A = int(cpu.A) ^ shifted

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def sre_indirect_indexed_y_0x53(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - (Indirect),Y addressing mode.

    Opcode: 0x53
    Cycles: 8
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory right and EORs with A
    VARIANT: 6502A - Shifts memory right and EORs with A
    VARIANT: 6502C - Shifts memory right and EORs with A
    VARIANT: 65C02 - Acts as NOP (see _sre_65c02.py)

    Operation: M = LSR(M), A = A ^ M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_indirect_indexed_mode_address()
    value: int = cpu.read_byte(address)

    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    shifted: int = (value >> 1) & 0xFF

    cpu.write_byte(address & 0xFFFF, shifted)

    cpu.A = int(cpu.A) ^ shifted

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def sre_absolute_0x4f(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - Absolute addressing mode.

    Opcode: 0x4F
    Cycles: 6
    Bytes: 3
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory right and EORs with A
    VARIANT: 6502A - Shifts memory right and EORs with A
    VARIANT: 6502C - Shifts memory right and EORs with A
    VARIANT: 65C02 - Acts as NOP (see _sre_65c02.py)

    Operation: M = LSR(M), A = A ^ M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(None)
    value: int = cpu.read_byte(address)

    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    shifted: int = (value >> 1) & 0xFF

    cpu.write_byte(address & 0xFFFF, shifted)

    cpu.A = int(cpu.A) ^ shifted

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def sre_absolute_x_0x5f(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - Absolute,X addressing mode.

    Opcode: 0x5F
    Cycles: 7
    Bytes: 3
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory right and EORs with A
    VARIANT: 6502A - Shifts memory right and EORs with A
    VARIANT: 6502C - Shifts memory right and EORs with A
    VARIANT: 65C02 - Acts as NOP (see _sre_65c02.py)

    Operation: M = LSR(M), A = A ^ M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address("X")

    # Read-Modify-Write with Absolute,X always does a dummy read regardless of page crossing
    cpu.spend_cpu_cycles(1)

    value: int = cpu.read_byte(address)

    # Internal processing cycle for RMW operation
    cpu.spend_cpu_cycles(1)

    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    shifted: int = (value >> 1) & 0xFF

    cpu.write_byte(address & 0xFFFF, shifted)

    cpu.A = int(cpu.A) ^ shifted

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ax")


def sre_absolute_y_0x5b(cpu: "MOS6502CPU") -> None:
    """Execute SRE (Shift Right and EOR) - Absolute,Y addressing mode.

    Opcode: 0x5B
    Cycles: 7
    Bytes: 3
    Flags: N, Z, C

    VARIANT: 6502 - Shifts memory right and EORs with A
    VARIANT: 6502A - Shifts memory right and EORs with A
    VARIANT: 6502C - Shifts memory right and EORs with A
    VARIANT: 65C02 - Acts as NOP (see _sre_65c02.py)

    Operation: M = LSR(M), A = A ^ M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address("Y")

    # Read-Modify-Write with Absolute,Y always does a dummy read regardless of page crossing
    cpu.spend_cpu_cycles(1)

    value: int = cpu.read_byte(address & 0xFFFF)

    # Internal processing cycle for RMW operation
    cpu.spend_cpu_cycles(1)

    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    shifted: int = (value >> 1) & 0xFF

    cpu.write_byte(address & 0xFFFF, shifted)

    cpu.A = int(cpu.A) ^ shifted

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ay")
