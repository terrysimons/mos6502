#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import exceptions, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def check_noop_flags(expected_cpu: CPU, actual_cpu: CPU) -> None:
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]


def test_cpu_instruction_DEX_IMPLIED_0xCA(cpu: CPU) -> None:  # noqa: N802
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.X = 0x42

    cpu.ram[0xFFFC] = instructions.DEX_IMPLIED_0xCA

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
    assert cpu.X == 0x41
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_DEX_IMPLIED_0xCA_zero_flag(cpu: CPU) -> None:  # noqa: N802
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.X = 0x01

    cpu.ram[0xFFFC] = instructions.DEX_IMPLIED_0xCA

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
    assert cpu.X == 0x00
    assert cpu.flags[flags.Z] == 1
    assert cpu.flags[flags.N] == 0
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_DEX_IMPLIED_0xCA_negative_flag(cpu: CPU) -> None:  # noqa: N802
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.X = 0x00

    cpu.ram[0xFFFC] = instructions.DEX_IMPLIED_0xCA

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
    assert cpu.X == 0xFF  # Wraps around
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1  # 0xFF has bit 7 set
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)
