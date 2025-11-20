#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions
from mos6502.memory import Byte, Word

log: logging.Logger = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


@contextlib.contextmanager
def suppress_illegal_instruction_logs():
    """Temporarily disable ERROR logs for illegal instruction detection."""
    logger = logging.getLogger("mos6502.cpu")
    original_level = logger.level
    logger.setLevel(logging.CRITICAL)
    try:
        yield
    finally:
        logger.setLevel(original_level)


def check_noop_flags(expected_cpu: CPU, actual_cpu: CPU) -> None:
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]


def verify_store_zeropage(cpu: CPU, data: Byte, instruction: instructions.InstructionSet,
                          offset: Byte, register_name: str,
                          expected_flags: flags.ProcessorStatusFlags, expected_cycles: int,
                          offset_register_name: str = None, offset_value: int = 0x00) -> None:
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    # Load the register with a value to be stored in memory
    setattr(cpu, register_name, data)

    # Load the offset register, if necessary
    if offset_register_name:
        setattr(cpu, offset_register_name, offset_value)

    # Load with zeropage offset
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = offset

    # zero page is 0x00-0xFF, so need to handle wraparound
    cpu.ram[(offset + offset_value) & 0xFF] = 0x00

    # when:
    with suppress_illegal_instruction_logs(), \
         contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(cycles=expected_cycles)

    # expect:
    assert cpu.cycles_executed == expected_cycles
    assert cpu.ram[(offset + offset_value) & 0xFF] == data
    assert cpu.flags == expected_flags
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def verify_store_absolute(cpu: CPU, data: Byte, instruction: instructions.InstructionSet,
                          offset: Byte, register_name: str,
                          expected_flags: flags.ProcessorStatusFlags, expected_cycles: int,
                          offset_register_name: str = None, offset_value: int = 0x00) -> None:
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    # Load the register with a value to be stored in memory
    setattr(cpu, register_name, data)

    # Load with absolute offset
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = offset.lowbyte
    cpu.ram[0xFFFE] = offset.highbyte

    # when:
    with suppress_illegal_instruction_logs(), \
         contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(cycles=expected_cycles)

    # expect:
    assert cpu.cycles_executed == expected_cycles
    assert cpu.ram[offset & 0xFFFF] == data
    assert cpu.flags == expected_flags
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def verify_store_indexed_indirect(cpu: CPU, pc_value: Byte, data: Byte,
                                  instruction: instructions.InstructionSet, offset: int,
                                  register_name: str, expected_flags: flags.ProcessorStatusFlags,
                                  expected_cycles: int, offset_value: int = 0x00) -> None:
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    # Load the register with a value to be stored in memory
    setattr(cpu, register_name, data)
    cpu.X = offset_value

    # Store with indirect x offset
    # @PC
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = pc_value

    # @ZP offset
    cpu.ram[(pc_value + offset_value) & 0xFF] = (offset) & 0xFF # zeropage addr
    cpu.ram[(pc_value + offset_value + 1) & 0xFF] = (offset >> 8) & 0xFF # zerpage addr + 1

    address: Word = Word(offset)

    # @ RAM - initialize to 0x00 so we can verify the store happened
    cpu.ram[address & 0xFFFF] = 0x00

    # when:
    with suppress_illegal_instruction_logs(), \
         contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(cycles=expected_cycles)

    # expect:
    assert cpu.cycles_executed == expected_cycles
    assert cpu.ram[address & 0xFFFF] == data
    assert cpu.flags == expected_flags
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def verify_store_indirect_indexed(cpu: CPU, pc_value: int, data: int,
                                  instruction: int, offset: int, register_name: str,
                                  expected_flags: flags.ProcessorStatusFlags, expected_cycles: int,
                                  offset_value: int = 0x00) -> None:
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    # Load the register with a value to be stored in memory
    setattr(cpu, register_name, data)
    cpu.Y = offset_value

    # Load with indirect x offset
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = pc_value

    # @ZP offset
    cpu.ram[(pc_value) & 0xFF] = (offset) & 0xFF # zeropage addr
    cpu.ram[(pc_value + 1) & 0xFF] = (offset >> 8) & 0xFF # zerpage addr + 1

    # @Address - initialize to 0x00 so we can verify the store happened
    cpu.ram[(offset + offset_value) & 0xFFFF] = 0x00

    address: Word = Word(offset + offset_value, endianness=cpu.endianness)

    # when:
    with suppress_illegal_instruction_logs(), \
         contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(cycles=expected_cycles)

    # expect:
    assert cpu.cycles_executed == expected_cycles
    assert cpu.ram[address & 0xFFFF] == data
    assert cpu.flags == expected_flags
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


"""STA"""


def test_cpu_instruction_STA_ABSOLUTE_0x8D(cpu: CPU) -> None:  # noqa: N802
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_absolute(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STA_ABSOLUTE_0x8D,
        offset=Word(0x8000, endianness=cpu.endianness),
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
    )


def test_cpu_instruction_STA_ABSOLUTE_X_0x9D(cpu: CPU) -> None:  # noqa: N802
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_absolute(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STA_ABSOLUTE_X_0x9D,
        offset=Word(0x8000, endianness=cpu.endianness),
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="X",
        offset_value=0x0F,
    )


def test_cpu_instruction_STA_ABSOLUTE_Y_0x99(cpu: CPU) -> None:  # noqa: N802
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_absolute(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STA_ABSOLUTE_Y_0x99,
        offset=Word(0x8000, endianness=cpu.endianness),
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=5,
        offset_register_name="Y",
        offset_value=0x0F,
    )


def test_cpu_instruction_STA_INDEXED_INDIRECT_X_0x81(cpu: CPU) -> None:  # noqa: N802
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_indexed_indirect(
        cpu=cpu,
        pc_value=0x02,
        data=0xFF,
        instruction=instructions.STA_INDEXED_INDIRECT_X_0x81,
        offset=0x8000,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0x04,
    )


def test_cpu_instruction_STA_INDIRECT_INDEXED_Y_0x91(cpu: CPU) -> None:  # noqa: N802
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_indirect_indexed(
        cpu=cpu,
        pc_value=0x80,
        data=0xFF,
        instruction=instructions.STA_INDIRECT_INDEXED_Y_0x91,
        offset=0x8000,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=6,
        offset_value=0x04,
    )


def test_cpu_instruction_STA_ZEROPAGE_0x85(cpu: CPU) -> None:  # noqa: N802
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_zeropage(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STA_ZEROPAGE_0x85,
        offset=0x80,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=3,
    )


def test_cpu_instruction_STA_ZEROPAGE_X_0x95(cpu: CPU) -> None:  # noqa: N802
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_zeropage(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STA_ZEROPAGE_X_0x95,
        offset=0x80,
        register_name="A",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="X",
        offset_value=0x0F,
    )
