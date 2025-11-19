#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import exceptions, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)

def check_noop_flags(expected_cpu: mos6502.CPU, actual_cpu: mos6502.CPU) -> None:
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]

def test_cpu_instruction_SEC_IMPLIED_0x38() -> None:  # noqa: N802
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    initial_cpu: mos6502.CPU = copy.deepcopy(cpu)

    cpu.flags[flags.C] = 0

    cpu.ram[0xFFFC] = instructions.SEC_IMPLIED_0x38

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
    assert cpu.flags[flags.C] == 1
    assert cpu.flags[flags.B] == initial_cpu.flags[flags.B]
    assert cpu.flags[flags.D] == initial_cpu.flags[flags.D]
    assert cpu.flags[flags.I] == initial_cpu.flags[flags.I]
    assert cpu.flags[flags.V] == initial_cpu.flags[flags.V]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)
