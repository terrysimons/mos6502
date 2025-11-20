#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def check_noop_flags(expected_cpu: CPU, actual_cpu: CPU) -> None:
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]


def test_cpu_instruction_CLV_IMPLIED_0xB8(cpu: CPU) -> None:  # noqa: N802
    """Test CLV instruction clears overflow flag on all CPU variants."""
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.flags[flags.V] = 1

    cpu.ram[0xFFFC] = instructions.CLV_IMPLIED_0xB8

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
    assert cpu.flags[flags.C] == initial_cpu.flags[flags.C]
    assert cpu.flags[flags.B] == initial_cpu.flags[flags.B]
    assert cpu.flags[flags.D] == initial_cpu.flags[flags.D]
    assert cpu.flags[flags.I] == initial_cpu.flags[flags.I]
    assert cpu.flags[flags.V] == 0
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)
