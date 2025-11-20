#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def check_noop_flags(expected_cpu: CPU, actual_cpu: CPU) -> None:
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]


def test_cpu_instruction_INY_IMPLIED_0xC8(cpu: CPU) -> None:  # noqa: N802
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.Y = 0x42

    cpu.ram[0xFFFC] = instructions.INY_IMPLIED_0xC8

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
    assert cpu.Y == 0x43
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_INY_IMPLIED_0xC8_zero_flag(cpu: CPU) -> None:  # noqa: N802
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.Y = 0xFF

    cpu.ram[0xFFFC] = instructions.INY_IMPLIED_0xC8

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
    assert cpu.Y == 0x00  # Wraps around
    assert cpu.flags[flags.Z] == 1
    assert cpu.flags[flags.N] == 0
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_INY_IMPLIED_0xC8_negative_flag(cpu: CPU) -> None:  # noqa: N802
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.Y = 0x7F

    cpu.ram[0xFFFC] = instructions.INY_IMPLIED_0xC8

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
    assert cpu.Y == 0x80
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1  # 0x80 has bit 7 set
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)
