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


def test_cpu_instruction_TXA_IMPLIED_0x8A(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.X = 0x42

    cpu.ram[pc] = instructions.TXA_IMPLIED_0x8A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == pc + 1
    assert cpu.cycles_executed - cycles_before == 2
    assert cpu.A == 0x42
    assert cpu.X == 0x42
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_TXA_IMPLIED_0x8A_zero_flag(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.X = 0x00

    cpu.ram[pc] = instructions.TXA_IMPLIED_0x8A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == pc + 1
    assert cpu.cycles_executed - cycles_before == 2
    assert cpu.A == 0x00
    assert cpu.flags[flags.Z] == 1
    assert cpu.flags[flags.N] == 0
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_TXA_IMPLIED_0x8A_negative_flag(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.X = 0x80

    cpu.ram[pc] = instructions.TXA_IMPLIED_0x8A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == pc + 1
    assert cpu.cycles_executed - cycles_before == 2
    assert cpu.A == 0x80
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)
