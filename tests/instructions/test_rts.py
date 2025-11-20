#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import errors, flags, instructions

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


def test_cpu_instruction_RTS_IMPLIED_0x60(cpu: CPU) -> None:  # noqa: N802
    # given:
    copy.deepcopy(cpu)

    # JSR to 0x4243, then return
    cpu.ram[0xFFFC] = instructions.JSR_ABSOLUTE_0x20
    cpu.ram[0xFFFD] = 0x43
    cpu.ram[0xFFFE] = 0x42

    # Execute JSR first
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    assert cpu.PC == 0x4243

    # Reset cycle counter for clearer RTS test
    cpu.cycles_executed = 0

    # Now place RTS at the subroutine location
    cpu.ram[0x4243] = instructions.RTS_IMPLIED_0x60

    # when: Execute only RTS (6 cycles per 6502 spec)
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=6)

    # then: RTS should return to address after JSR (0xFFFF)
    assert cpu.PC == 0xFFFF
    assert cpu.cycles_executed == 6
