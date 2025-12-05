#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log: logging.Logger = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def check_noop_flags(expected_cpu: CPU, actual_cpu: CPU) -> None:
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]


def test_cpu_instruction_JSR_ABSOLUTE_0x20(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    copy.deepcopy(cpu)

    # Jump to 0x4243
    # Should be 6 cycles
    cpu.ram[pc] = instructions.JSR_ABSOLUTE_0x20
    cpu.ram[pc + 1] = 0x43
    cpu.ram[pc + 2] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=6

    # then:
    # assert cpu.cycles_executed - cycles_before == 6
    assert cpu.instructions_executed - instructions_before == 1
    assert cpu.PC == 0x4243
