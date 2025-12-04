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
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]


def test_cpu_instruction_TXS_IMPLIED_0x9A(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.X = 0x42

    cpu.ram[pc] = instructions.TXS_IMPLIED_0x9A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == pc + 1
    assert cpu.cycles_executed - cycles_before == 2
    assert cpu.S == 0x142  # Stack pointer is 0x100 | X
    assert cpu.X == 0x42
    # TXS does not affect flags
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_TXS_IMPLIED_0x9A_zero_value(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.X = 0x00

    cpu.ram[pc] = instructions.TXS_IMPLIED_0x9A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == pc + 1
    assert cpu.cycles_executed - cycles_before == 2
    assert cpu.S == 0x100
    # TXS does not affect flags (including Z flag)
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)
