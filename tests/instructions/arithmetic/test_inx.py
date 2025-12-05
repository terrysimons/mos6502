#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def check_noop_flags(expected_cpu: CPU, actual_cpu: CPU) -> None:
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]


def test_cpu_instruction_INX_IMPLIED_0xE8(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.X = 0x42

    cpu.ram[pc] = instructions.INX_IMPLIED_0xE8

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.PC == pc + 1
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1
    assert cpu.X == 0x43
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_INX_IMPLIED_0xE8_zero_flag(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.X = 0xFF

    cpu.ram[pc] = instructions.INX_IMPLIED_0xE8

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.PC == pc + 1
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1
    assert cpu.X == 0x00  # Wraps around
    assert cpu.flags[flags.Z] == 1
    assert cpu.flags[flags.N] == 0
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_INX_IMPLIED_0xE8_negative_flag(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.X = 0x7F

    cpu.ram[pc] = instructions.INX_IMPLIED_0xE8

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.PC == pc + 1
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1
    assert cpu.X == 0x80
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1  # 0x80 has bit 7 set
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)
