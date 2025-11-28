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


def test_cpu_instruction_SED_IMPLIED_0xF8(cpu: CPU) -> None:  # noqa: N802
    """Test SED instruction sets decimal flag on all CPU variants."""
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.flags[flags.D] = 0

    cpu.ram[pc] = instructions.SED_IMPLIED_0xF8

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == pc + 1
    assert cpu.cycles_executed - cycles_before == 2
    assert cpu.flags[flags.C] == initial_cpu.flags[flags.C]
    assert cpu.flags[flags.B] == initial_cpu.flags[flags.B]
    assert cpu.flags[flags.D] == 1
    assert cpu.flags[flags.I] == initial_cpu.flags[flags.I]
    assert cpu.flags[flags.V] == initial_cpu.flags[flags.V]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)
