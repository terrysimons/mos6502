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
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]

def test_cpu_instruction_CLC_IMPLIED_0x18():
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    initial_cpu: mos6502.CPU = copy.deepcopy(cpu)

    cpu.flags[flags.C] = 1

    cpu.ram[0xFFFC] = instructions.CLC_IMPLIED_0x18

    # when:
    try:
        cpu.execute(cycles=2)
    except exceptions.CPUCycleExhaustionException:
        pass

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
    assert cpu.flags[flags.C] == 0
    assert cpu.flags[flags.B] == initial_cpu.flags[flags.B]
    assert cpu.flags[flags.D] == initial_cpu.flags[flags.D]
    assert cpu.flags[flags.I] == initial_cpu.flags[flags.I]
    assert cpu.flags[flags.V] == initial_cpu.flags[flags.V]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)

def test_cpu_instruction_CLD_IMPLIED_0xD8():
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    initial_cpu: mos6502.CPU = copy.deepcopy(cpu)

    cpu.flags[flags.D] = 1

    cpu.ram[0xFFFC] = instructions.CLD_IMPLIED_0xD8

    # when:
    try:
        cpu.execute(cycles=2)
    except exceptions.CPUCycleExhaustionException:
        pass

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
    assert cpu.flags[flags.C] == initial_cpu.flags[flags.C]
    assert cpu.flags[flags.B] == initial_cpu.flags[flags.B]
    assert cpu.flags[flags.D] == 0
    assert cpu.flags[flags.I] == initial_cpu.flags[flags.I]
    assert cpu.flags[flags.V] == initial_cpu.flags[flags.V]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_CLI_IMPLIED_0x58():
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    initial_cpu: mos6502.CPU = copy.deepcopy(cpu)

    cpu.flags[flags.I] = 1

    cpu.ram[0xFFFC] = instructions.CLI_IMPLIED_0x58

    # when:
    try:
        cpu.execute(cycles=2)
    except exceptions.CPUCycleExhaustionException:
        pass

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
    assert cpu.flags[flags.C] == initial_cpu.flags[flags.C]
    assert cpu.flags[flags.B] == initial_cpu.flags[flags.B]
    assert cpu.flags[flags.D] == initial_cpu.flags[flags.D]
    assert cpu.flags[flags.I] == 0
    assert cpu.flags[flags.V] == initial_cpu.flags[flags.V]
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)

def test_cpu_instruction_CLV_IMPLIED_0xB8():
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()
    initial_cpu: mos6502.CPU = copy.deepcopy(cpu)

    cpu.flags[flags.V] = 1

    cpu.ram[0xFFFC] = instructions.CLV_IMPLIED_0xB8

    # when:
    try:
        cpu.execute(cycles=2)
    except exceptions.CPUCycleExhaustionException:
        pass

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 2
    assert cpu.flags[flags.C] == initial_cpu.flags[flags.C]
    assert cpu.flags[flags.B] == initial_cpu.flags[flags.B]
    assert cpu.flags[flags.D] == initial_cpu.flags[flags.D]
    assert cpu.flags[flags.I] == initial_cpu.flags[flags.I]
    assert cpu.flags[flags.V] == 0
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)

