#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import mos6502
import mos6502.instructions as instructions
import mos6502.exceptions as exceptions

def test_cpu_instruction_JSR_ABSOLUTE_0x20():
    cpu: mos6502.CPU = mos6502.CPU()

    # Jump to 0x4242
    # Should be 8 cycles
    cpu.ram[0xFFFC] = instructions.JSR_ABSOLUTE_0x20
    cpu.ram[0xFFFD] = 0x42
    cpu.ram[0xFFFE] = 0x42

    try:
        cpu.execute(cycles=6)
    except exceptions.CPUCycleExhaustionException:
        pass

    assert cpu.cycles_executed == 6

    cpu.ram[0x4242] = instructions.LDA_IMMEDIATE_0xA9
    cpu.ram[0x4243] = 0x23

    try:
        cpu.execute(cycles=2)
    except exceptions.CPUCycleExhaustionException:
        pass

    assert cpu.cycles_executed == 8
