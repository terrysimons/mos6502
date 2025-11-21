#!/usr/bin/env python3
"""Helper functions for load instruction tests."""
import contextlib
import copy
import logging
from collections.abc import Generator

import mos6502
from mos6502 import errors, flags
from mos6502.memory import Byte, Word


@contextlib.contextmanager
def suppress_illegal_instruction_logs() -> Generator[None, None, None]:
    """Temporarily disable ERROR logs for illegal instruction detection."""
    logger = logging.getLogger("mos6502.cpu")
    original_level = logger.level
    logger.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        logger.setLevel(original_level)


def check_noop_flags(expected_cpu: mos6502.CPU, actual_cpu: mos6502.CPU) -> None:
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]


def verify_load_immediate(cpu: mos6502.CPU, data: int, instruction: int, register_name: str,
                          expected_flags: flags.ProcessorStatusFlags, expected_cycles: int) -> None:
    # given:
    initial_cpu: mos6502.CPU = copy.deepcopy(cpu)

    # Prevent false positives for Z flag on invalid addresses
    if data == 0x00:
        cpu.ram.fill(Byte(0xFF))

    # Load direct to memory
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = data

    # when:
    with suppress_illegal_instruction_logs(), \
         contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(cycles=expected_cycles)

    # then:
    assert cpu.cycles_executed == expected_cycles
    assert getattr(cpu, register_name) == data
    assert cpu.flags[flags.Z] == expected_flags[flags.Z]
    assert cpu.flags[flags.N] == expected_flags[flags.N]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def verify_load_zeropage(cpu: mos6502.CPU, data: int, instruction: int, offset: int,
                         register_name: str, expected_flags: flags.ProcessorStatusFlags,
                         expected_cycles: int, offset_register_name: str = None,
                         offset_value: int = 0x00) -> None:
    # given:
    initial_cpu: mos6502.MOS6502CPU = copy.deepcopy(cpu)

    # Prevent false positives for Z flag on invalid addresses
    if data == 0x00:
        cpu.ram.fill(Byte(0xFF))

    if offset_register_name is not None:
        setattr(cpu, offset_register_name, offset_value)

    # Load with zeropage offset
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = offset

    # zero page is 0x00-0xFF, so need to handle wraparound
    cpu.ram[(offset + offset_value) & 0xFF] = data

    # when:
    with suppress_illegal_instruction_logs(), \
         contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(cycles=expected_cycles)

    # then:
    assert cpu.cycles_executed == expected_cycles
    if offset_register_name is not None:
        assert getattr(cpu, offset_register_name) == offset_value
    assert getattr(cpu, register_name) == data
    assert cpu.flags[flags.Z] == expected_flags[flags.Z]
    assert cpu.flags[flags.N] == expected_flags[flags.N]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def verify_load_absolute(cpu: mos6502.CPU, data: int, instruction: int, offset: int,
                         register_name: str, expected_flags: flags.ProcessorStatusFlags,
                         expected_cycles: int, offset_register_name: str = None,
                         offset_value: int = 0x00) -> None:
    # given:
    initial_cpu: mos6502.MOS6502CPU = copy.deepcopy(cpu)

    # Prevent false positives for Z flag on invalid addresses
    if data == 0x00:
        cpu.ram.fill(Byte(0xFF))

    if offset_register_name is not None:
        setattr(cpu, offset_register_name, offset_value)

    offset_address: Word = Word(offset, endianness=cpu.endianness)

    # Load with 16-bit address + cpu.X offset
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = 0xFF & offset_address.lowbyte
    cpu.ram[0xFFFE] = 0xFF & offset_address.highbyte
    cpu.ram[(offset_address + offset_value) & 0xFFFF] = data

    # when:
    with suppress_illegal_instruction_logs(), \
         contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(cycles=expected_cycles)

    # then:
    assert cpu.cycles_executed == expected_cycles
    if offset_register_name is not None:
        assert getattr(cpu, offset_register_name) == offset_value
    assert getattr(cpu, register_name) == data
    assert cpu.flags[flags.Z] == expected_flags[flags.Z]
    assert cpu.flags[flags.N] == expected_flags[flags.N]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def verify_load_indexed_indirect(cpu: mos6502.CPU, pc_value: int, data: int, instruction: int,
                                 offset: int, register_name: str,
                                 expected_flags: flags.ProcessorStatusFlags, expected_cycles: int,
                                 offset_value: int = 0x00) -> None:
    # given:
    initial_cpu: mos6502.MOS6502CPU = copy.deepcopy(cpu)

    # Prevent false positives for Z flag on invalid addresses
    if data == 0x00:
        cpu.ram.fill(Byte(0xFF))

    cpu.X = offset_value

    offset_address: Word = Word(offset, endianness=cpu.endianness)

    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = pc_value # fetch_byte() -> 0x02

    # 0x02 + cpu.X(value))
    cpu.ram[pc_value + offset_value] = 0xFF & offset_address.lowbyte

    # read_byte(0x06) == 0x00, read_byte(0x07) == 0x80 -> Word(0x8000)
    cpu.ram[pc_value + offset_value + 1] = 0x80 & offset_address.highbyte
    cpu.ram[offset_address & 0xFFFF] = data # read_byte(0x8000) -> cpu.A

    # when:
    with suppress_illegal_instruction_logs(), \
         contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(cycles=expected_cycles)

    # then:
    assert cpu.cycles_executed == expected_cycles
    assert offset_value == cpu.X
    assert getattr(cpu, register_name) == data
    assert cpu.flags[flags.Z] == expected_flags[flags.Z]
    assert cpu.flags[flags.N] == expected_flags[flags.N]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def verify_load_indirect_indexed(cpu: mos6502.CPU, pc_value: int, data: int, instruction: int,
                                 offset: int, register_name: str,
                                 expected_flags: flags.ProcessorStatusFlags, expected_cycles: int,
                                 offset_value: int = 0x00) -> None:
    # given:
    initial_cpu: mos6502.MOS6502CPU = copy.deepcopy(cpu)

    # Prevent false positives for Z flag on invalid addresses
    if data == 0x00:
        cpu.ram.fill(Byte(0xFF))

    cpu.Y = offset_value

    offset_address: Word = Word(offset, endianness=cpu.endianness)

    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = pc_value

     # 0x02@0xFFFD is the start of our address vector in the zero page (LSB)
    cpu.ram[pc_value] = 0xFF & offset_address.lowbyte

    # 0x03 is the msb of our address (0x8000)
    cpu.ram[pc_value + 1] = 0xFF & offset_address.highbyte

    # 0x8000 + cpu.Y(0x80) [0x8080] -> cpu.A
    cpu.ram[(offset_address + offset_value) & 0xFFFF] = data

    # when:
    with suppress_illegal_instruction_logs(), \
         contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(cycles=expected_cycles)

    # then
    assert cpu.cycles_executed == expected_cycles
    assert offset_value == cpu.Y
    assert getattr(cpu, register_name) == data
    assert cpu.flags[flags.Z] == expected_flags[flags.Z]
    assert cpu.flags[flags.N] == expected_flags[flags.N]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)
