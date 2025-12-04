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

def test_cpu_instruction_NOP_IMPLIED_0xEA(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.ram[pc] = instructions.NOP_IMPLIED_0xEA

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=2)

    # then:
    assert cpu.PC == pc + 1
    assert cpu.cycles_executed - cycles_before == 2
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)

