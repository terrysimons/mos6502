#!/usr/bin/env python3
"""RLA instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - NMOS only

RLA (Rotate Left and AND) rotates a memory location left through the carry flag,
then performs a bitwise AND with the accumulator. It is functionally equivalent
to executing ROL followed by AND, but in a single instruction.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#RLA
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def rla_zeropage_0x27(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - Zero Page addressing mode.

    Opcode: 0x27
    Cycles: 5
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Rotates memory left and ANDs with A
    VARIANT: 6502A - Rotates memory left and ANDs with A
    VARIANT: 6502C - Rotates memory left and ANDs with A
    VARIANT: 65C02 - Acts as NOP (see _rla_65c02.py)

    Operation: M = ROL(M), A = A & M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)
    carry_in: int = cpu.flags[flags.C]

    # Rotate left (bit 7 goes to carry, carry goes to bit 0)
    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    rotated: int = ((value << 1) | carry_in) & 0xFF

    # Write rotated value back to memory
    cpu.write_byte(address=address, data=rotated)

    # AND with accumulator
    cpu.A = int(cpu.A) & rotated

    # Set N and Z flags based on accumulator
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def rla_zeropage_x_0x37(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - Zero Page,X addressing mode.

    Opcode: 0x37
    Cycles: 6
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Rotates memory left and ANDs with A
    VARIANT: 6502A - Rotates memory left and ANDs with A
    VARIANT: 6502C - Rotates memory left and ANDs with A
    VARIANT: 65C02 - Acts as NOP (see _rla_65c02.py)

    Operation: M = ROL(M), A = A & M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    value: int = cpu.read_byte(address=address)
    carry_in: int = cpu.flags[flags.C]

    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    rotated: int = ((value << 1) | carry_in) & 0xFF

    cpu.write_byte(address=address, data=rotated)

    cpu.A = int(cpu.A) & rotated

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def rla_indexed_indirect_x_0x23(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - (Indirect,X) addressing mode.

    Opcode: 0x23
    Cycles: 8
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Rotates memory left and ANDs with A
    VARIANT: 6502A - Rotates memory left and ANDs with A
    VARIANT: 6502C - Rotates memory left and ANDs with A
    VARIANT: 65C02 - Acts as NOP (see _rla_65c02.py)

    Operation: M = ROL(M), A = A & M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_indexed_indirect_mode_address()
    value: int = cpu.read_byte(address=address)
    carry_in: int = cpu.flags[flags.C]

    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    rotated: int = ((value << 1) | carry_in) & 0xFF

    cpu.write_byte(address=address & 0xFFFF, data=rotated)

    cpu.A = int(cpu.A) & rotated

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def rla_indirect_indexed_y_0x33(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - (Indirect),Y addressing mode.

    Opcode: 0x33
    Cycles: 8
    Bytes: 2
    Flags: N, Z, C

    VARIANT: 6502 - Rotates memory left and ANDs with A
    VARIANT: 6502A - Rotates memory left and ANDs with A
    VARIANT: 6502C - Rotates memory left and ANDs with A
    VARIANT: 65C02 - Acts as NOP (see _rla_65c02.py)

    Operation: M = ROL(M), A = A & M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_indirect_indexed_mode_address()
    value: int = cpu.read_byte(address=address)
    carry_in: int = cpu.flags[flags.C]

    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    rotated: int = ((value << 1) | carry_in) & 0xFF

    cpu.write_byte(address=address & 0xFFFF, data=rotated)

    cpu.A = int(cpu.A) & rotated

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def rla_absolute_0x2f(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - Absolute addressing mode.

    Opcode: 0x2F
    Cycles: 6
    Bytes: 3
    Flags: N, Z, C

    VARIANT: 6502 - Rotates memory left and ANDs with A
    VARIANT: 6502A - Rotates memory left and ANDs with A
    VARIANT: 6502C - Rotates memory left and ANDs with A
    VARIANT: 65C02 - Acts as NOP (see _rla_65c02.py)

    Operation: M = ROL(M), A = A & M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)
    carry_in: int = cpu.flags[flags.C]

    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    rotated: int = ((value << 1) | carry_in) & 0xFF

    cpu.write_byte(address=address & 0xFFFF, data=rotated)

    cpu.A = int(cpu.A) & rotated

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def rla_absolute_x_0x3f(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - Absolute,X addressing mode.

    Opcode: 0x3F
    Cycles: 7
    Bytes: 3
    Flags: N, Z, C

    VARIANT: 6502 - Rotates memory left and ANDs with A
    VARIANT: 6502A - Rotates memory left and ANDs with A
    VARIANT: 6502C - Rotates memory left and ANDs with A
    VARIANT: 65C02 - Acts as NOP (see _rla_65c02.py)

    Operation: M = ROL(M), A = A & M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name="X")

    # Read-Modify-Write with Absolute,X always does a dummy read regardless of page crossing
    cpu.spend_cpu_cycles(1)

    value: int = cpu.read_byte(address=address)

    # Internal processing cycle for RMW operation
    cpu.spend_cpu_cycles(1)

    carry_in: int = cpu.flags[flags.C]

    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    rotated: int = ((value << 1) | carry_in) & 0xFF

    cpu.write_byte(address=address & 0xFFFF, data=rotated)

    cpu.A = int(cpu.A) & rotated

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ax")


def rla_absolute_y_0x3b(cpu: "MOS6502CPU") -> None:
    """Execute RLA (Rotate Left and AND) - Absolute,Y addressing mode.

    Opcode: 0x3B
    Cycles: 7
    Bytes: 3
    Flags: N, Z, C

    VARIANT: 6502 - Rotates memory left and ANDs with A
    VARIANT: 6502A - Rotates memory left and ANDs with A
    VARIANT: 6502C - Rotates memory left and ANDs with A
    VARIANT: 65C02 - Acts as NOP (see _rla_65c02.py)

    Operation: M = ROL(M), A = A & M

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name="Y")

    # Read-Modify-Write with Absolute,Y always does a dummy read regardless of page crossing
    cpu.spend_cpu_cycles(1)

    value: int = cpu.read_byte(address=address & 0xFFFF)

    # Internal processing cycle for RMW operation
    cpu.spend_cpu_cycles(1)

    carry_in: int = cpu.flags[flags.C]

    cpu.flags[flags.C] = 1 if (value & 0x80) else 0
    rotated: int = ((value << 1) | carry_in) & 0xFF

    cpu.write_byte(address=address & 0xFFFF, data=rotated)

    cpu.A = int(cpu.A) & rotated

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ay")
