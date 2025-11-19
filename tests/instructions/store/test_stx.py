#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import exceptions, flags, instructions
from mos6502.memory import Byte, Word

log: logging.Logger = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def check_noop_flags(expected_cpu: mos6502.CPU, actual_cpu: mos6502.CPU) -> None:
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]


def verify_store_zeropage(cpu: mos6502.CPU, data: Byte, instruction: instructions.InstructionSet,
                          offset: Byte, register_name: str,
                          expected_flags: flags.ProcessorStatusFlags, expected_cycles: int,
                          offset_register_name: str = None, offset_value: int = 0x00) -> None:
    # given:
    initial_cpu: mos6502.CPU = copy.deepcopy(cpu)

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
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=expected_cycles)

    # expect:
    assert cpu.cycles_executed == expected_cycles
    assert cpu.ram[(offset + offset_value) & 0xFF] == data
    assert cpu.flags == expected_flags
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def verify_store_absolute(cpu: mos6502.CPU, data: Byte, instruction: instructions.InstructionSet,
                          offset: Byte, register_name: str,
                          expected_flags: flags.ProcessorStatusFlags, expected_cycles: int,
                          offset_register_name: str = None, offset_value: int = 0x00) -> None:
    # given:
    initial_cpu: mos6502.CPU = copy.deepcopy(cpu)

    # Load the register with a value to be stored in memory
    setattr(cpu, register_name, data)

    # Load with absolute offset
    cpu.ram[0xFFFC] = instruction
    cpu.ram[0xFFFD] = offset.lowbyte
    cpu.ram[0xFFFE] = offset.highbyte

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=expected_cycles)

    # expect:
    assert cpu.cycles_executed == expected_cycles
    assert cpu.ram[offset & 0xFFFF] == data
    assert cpu.flags == expected_flags
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


"""STX"""


def test_cpu_instruction_STX_ABSOLUTE_0x8E() -> None:  # noqa: N802
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_absolute(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STX_ABSOLUTE_0x8E,
        offset=Word(0x8000, endianness=cpu.endianness),
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=3,
    )


def test_cpu_instruction_STX_ZEROPAGE_0x86() -> None:  # noqa: N802
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_zeropage(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STX_ZEROPAGE_0x86,
        offset=0x80,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=4,
    )


def test_cpu_instruction_STX_ZEROPAGE_Y_0x96() -> None:  # noqa: N802
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    expected_flags: Byte = copy.deepcopy(cpu.flags)

    verify_store_zeropage(
        cpu=cpu,
        data=0x23,
        instruction=instructions.STX_ZEROPAGE_Y_0x96,
        offset=0x80,
        register_name="X",
        expected_flags=expected_flags,
        expected_cycles=4,
        offset_register_name="Y",
        offset_value=0x0F,
    )
