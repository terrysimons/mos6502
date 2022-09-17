#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import copy
import logging

import mos6502
import mos6502.flags as flags
import mos6502.instructions as instructions
import mos6502.exceptions as exceptions

log = logging.getLogger('mos6502')
log.setLevel(logging.DEBUG)

def check_noop_flags(expected_cpu, actual_cpu):
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]

def test_cpu_instruction_NOP_IMPLIED_0xEA():
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    initial_cpu: mos6502.CPU = copy.deepcopy(cpu)

    cpu.ram[0xFFFC] = instructions.NOP_IMPLIED_0xEA

    # when:
    try:
        cpu.execute(cycles=2)
    except exceptions.CPUCycleExhaustionException:
        pass

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)

