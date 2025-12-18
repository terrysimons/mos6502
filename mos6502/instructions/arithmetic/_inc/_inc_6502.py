#!/usr/bin/env python3
"""INC instruction implementation for all 6502 variants."""


from mos6502.compat import TYPE_CHECKING

if TYPE_CHECKING:
    from mos6502.core import MOS6502CPU


def inc_zeropage_0xe6(cpu: "MOS6502CPU") -> None:
    """Execute INC (Increment Memory) - Zero Page addressing mode.

    Opcode: 0xE6
    Cycles: 5
    Flags: N Z

    Arguments:
    ---------
        cpu: The CPU instance to operate on
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address(None)
    value: int = cpu.read_byte(address)

    result: int = (value + 1) & 0xFF
    cpu.write_byte(address, result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("z")


def inc_zeropage_x_0xf6(cpu: "MOS6502CPU") -> None:
    """Execute INC (Increment Memory) - Zero Page,X addressing mode.

    Opcode: 0xF6
    Cycles: 6
    Flags: N Z
    """
    from mos6502 import flags

    address: int = cpu.fetch_zeropage_mode_address("X")
    value: int = cpu.read_byte(address)

    result: int = (value + 1) & 0xFF
    cpu.write_byte(address, result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("zx")


def inc_absolute_0xee(cpu: "MOS6502CPU") -> None:
    """Execute INC (Increment Memory) - Absolute addressing mode.

    Opcode: 0xEE
    Cycles: 6
    Flags: N Z
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address(None)
    value: int = cpu.read_byte(address)

    # Read-Modify-Write operations have an internal processing cycle
    cpu.spend_cpu_cycles(1)

    result: int = (value + 1) & 0xFF
    cpu.write_byte(address & 0xFFFF, result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("a")


def inc_absolute_x_0xfe(cpu: "MOS6502CPU") -> None:
    """Execute INC (Increment Memory) - Absolute,X addressing mode.

    Opcode: 0xFE
    Cycles: 7
    Flags: N Z
    """
    from mos6502 import flags

    address: int = cpu.fetch_absolute_mode_address("X")

    # Read-Modify-Write with Absolute,X always does a dummy read regardless of page crossing
    cpu.spend_cpu_cycles(1)

    value: int = cpu.read_byte(address)

    # Internal processing cycle for RMW operation
    cpu.spend_cpu_cycles(1)

    result: int = (value + 1) & 0xFF
    cpu.write_byte(address & 0xFFFF, result)

    # Set N and Z flags
    cpu.flags[flags.Z] = 1 if result == 0 else 0
    cpu.flags[flags.N] = 1 if (result & 0x80) else 0

    cpu.log.info("ax")
