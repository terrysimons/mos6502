#!/usr/bin/env python3
"""RRA instruction implementation for NMOS 6502 variants.

ILLEGAL INSTRUCTION - NMOS only

RRA (Rotate Right and Add with Carry) rotates a memory location right through
the carry flag, then adds the result to the accumulator with carry. It is
functionally equivalent to executing ROR followed by ADC, but in a single
instruction.

References:
  - https://masswerk.at/6502/6502_instruction_set.html#RRA
  - http://www.oxyron.de/html/opcodes02.html
"""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def rra_zeropage_0x67(cpu: "MOS6502CPU") -> None:
    """Execute RRA (Rotate Right and Add with Carry) - Zero Page addressing mode.

    Opcode: 0x67
    Cycles: 5
    Bytes: 2
    Flags: N, Z, C, V

    VARIANT: 6502 - Rotates memory right and ADCs with A
    VARIANT: 6502A - Rotates memory right and ADCs with A
    VARIANT: 6502C - Rotates memory right and ADCs with A
    VARIANT: 65C02 - Acts as NOP (see _rra_65c02.py)

    Operation: M = ROR(M), A = A + M + C

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)
    carry_in: int = cpu.flags[flags.C]

    # Rotate right (bit 0 goes to carry, carry goes to bit 7)
    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    rotated: int = (value >> 1) | (carry_in << 7)

    # Write rotated value back to memory
    cpu.write_byte(address=address, data=rotated)

    # Add with carry (using the NEW carry from rotation)
    result: int = cpu.A + rotated + cpu.flags[flags.C]

    # Set Carry flag if result > 255
    cpu.flags[flags.C] = 1 if result > 0xFF else 0

    # Set Overflow flag
    cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (rotated ^ result) & 0x80) else 0

    # Store result (masked to 8 bits)
    cpu.A = result & 0xFF

    # Set N and Z flags based on accumulator
    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def rra_zeropage_x_0x77(cpu: "MOS6502CPU") -> None:
    """Execute RRA (Rotate Right and Add with Carry) - Zero Page,X addressing mode.

    Opcode: 0x77
    Cycles: 6
    Bytes: 2
    Flags: N, Z, C, V

    VARIANT: 6502 - Rotates memory right and ADCs with A
    VARIANT: 6502A - Rotates memory right and ADCs with A
    VARIANT: 6502C - Rotates memory right and ADCs with A
    VARIANT: 65C02 - Acts as NOP (see _rra_65c02.py)

    Operation: M = ROR(M), A = A + M + C

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(offset_register_name="X")
    value: int = cpu.read_byte(address=address)
    carry_in: int = cpu.flags[flags.C]

    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    rotated: int = (value >> 1) | (carry_in << 7)

    cpu.write_byte(address=address, data=rotated)

    result: int = cpu.A + rotated + cpu.flags[flags.C]
    cpu.flags[flags.C] = 1 if result > 0xFF else 0
    cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (rotated ^ result) & 0x80) else 0
    cpu.A = result & 0xFF

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def rra_indexed_indirect_x_0x63(cpu: "MOS6502CPU") -> None:
    """Execute RRA (Rotate Right and Add with Carry) - (Indirect,X) addressing mode.

    Opcode: 0x63
    Cycles: 8
    Bytes: 2
    Flags: N, Z, C, V

    VARIANT: 6502 - Rotates memory right and ADCs with A
    VARIANT: 6502A - Rotates memory right and ADCs with A
    VARIANT: 6502C - Rotates memory right and ADCs with A
    VARIANT: 65C02 - Acts as NOP (see _rra_65c02.py)

    Operation: M = ROR(M), A = A + M + C

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_indexed_indirect_mode_address()
    value: int = cpu.read_byte(address=address)
    carry_in: int = cpu.flags[flags.C]

    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    rotated: int = (value >> 1) | (carry_in << 7)

    cpu.write_byte(address=address & 0xFFFF, data=rotated)

    result: int = cpu.A + rotated + cpu.flags[flags.C]
    cpu.flags[flags.C] = 1 if result > 0xFF else 0
    cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (rotated ^ result) & 0x80) else 0
    cpu.A = result & 0xFF

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def rra_indirect_indexed_y_0x73(cpu: "MOS6502CPU") -> None:
    """Execute RRA (Rotate Right and Add with Carry) - (Indirect),Y addressing mode.

    Opcode: 0x73
    Cycles: 8
    Bytes: 2
    Flags: N, Z, C, V

    VARIANT: 6502 - Rotates memory right and ADCs with A
    VARIANT: 6502A - Rotates memory right and ADCs with A
    VARIANT: 6502C - Rotates memory right and ADCs with A
    VARIANT: 65C02 - Acts as NOP (see _rra_65c02.py)

    Operation: M = ROR(M), A = A + M + C

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_indirect_indexed_mode_address()
    value: int = cpu.read_byte(address=address)
    carry_in: int = cpu.flags[flags.C]

    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    rotated: int = (value >> 1) | (carry_in << 7)

    cpu.write_byte(address=address & 0xFFFF, data=rotated)

    result: int = cpu.A + rotated + cpu.flags[flags.C]
    cpu.flags[flags.C] = 1 if result > 0xFF else 0
    cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (rotated ^ result) & 0x80) else 0
    cpu.A = result & 0xFF

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def rra_absolute_0x6f(cpu: "MOS6502CPU") -> None:
    """Execute RRA (Rotate Right and Add with Carry) - Absolute addressing mode.

    Opcode: 0x6F
    Cycles: 6
    Bytes: 3
    Flags: N, Z, C, V

    VARIANT: 6502 - Rotates memory right and ADCs with A
    VARIANT: 6502A - Rotates memory right and ADCs with A
    VARIANT: 6502C - Rotates memory right and ADCs with A
    VARIANT: 65C02 - Acts as NOP (see _rra_65c02.py)

    Operation: M = ROR(M), A = A + M + C

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(offset_register_name=None)
    value: int = cpu.read_byte(address=address)
    carry_in: int = cpu.flags[flags.C]

    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    rotated: int = (value >> 1) | (carry_in << 7)

    cpu.write_byte(address=address & 0xFFFF, data=rotated)

    result: int = cpu.A + rotated + cpu.flags[flags.C]
    cpu.flags[flags.C] = 1 if result > 0xFF else 0
    cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (rotated ^ result) & 0x80) else 0
    cpu.A = result & 0xFF

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("i")


def rra_absolute_x_0x7f(cpu: "MOS6502CPU") -> None:
    """Execute RRA (Rotate Right and Add with Carry) - Absolute,X addressing mode.

    Opcode: 0x7F
    Cycles: 7
    Bytes: 3
    Flags: N, Z, C, V

    VARIANT: 6502 - Rotates memory right and ADCs with A
    VARIANT: 6502A - Rotates memory right and ADCs with A
    VARIANT: 6502C - Rotates memory right and ADCs with A
    VARIANT: 65C02 - Acts as NOP (see _rra_65c02.py)

    Operation: M = ROR(M), A = A + M + C

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

    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    rotated: int = (value >> 1) | (carry_in << 7)

    cpu.write_byte(address=address & 0xFFFF, data=rotated)

    result: int = cpu.A + rotated + cpu.flags[flags.C]
    cpu.flags[flags.C] = 1 if result > 0xFF else 0
    cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (rotated ^ result) & 0x80) else 0
    cpu.A = result & 0xFF

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ax")


def rra_absolute_y_0x7b(cpu: "MOS6502CPU") -> None:
    """Execute RRA (Rotate Right and Add with Carry) - Absolute,Y addressing mode.

    Opcode: 0x7B
    Cycles: 7
    Bytes: 3
    Flags: N, Z, C, V

    VARIANT: 6502 - Rotates memory right and ADCs with A
    VARIANT: 6502A - Rotates memory right and ADCs with A
    VARIANT: 6502C - Rotates memory right and ADCs with A
    VARIANT: 65C02 - Acts as NOP (see _rra_65c02.py)

    Operation: M = ROR(M), A = A + M + C

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

    cpu.flags[flags.C] = 1 if (value & 0x01) else 0
    rotated: int = (value >> 1) | (carry_in << 7)

    cpu.write_byte(address=address & 0xFFFF, data=rotated)

    result: int = cpu.A + rotated + cpu.flags[flags.C]
    cpu.flags[flags.C] = 1 if result > 0xFF else 0
    cpu.flags[flags.V] = 1 if ((cpu.A ^ result) & (rotated ^ result) & 0x80) else 0
    cpu.A = result & 0xFF

    cpu.flags[flags.Z] = 1 if cpu.A == 0 else 0
    cpu.flags[flags.N] = 1 if (cpu.A & 0x80) else 0

    cpu.log.info("ay")
