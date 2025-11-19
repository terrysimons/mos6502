#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import exceptions, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_PLP_IMPLIED_0x28() -> None:  # noqa: N802
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    # Push a status value onto the stack
    # Bit layout: C=7, Z=6, I=5, D=4, B=3, -, V=1, N=0
    # Set C, Z, I, D, V, N = 0b11110011 = 0xF3
    status_value: int = 0b11110011
    cpu.ram[cpu.S] = status_value
    cpu.S -= 1

    cpu.ram[0xFFFC] = instructions.PLP_IMPLIED_0x28

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 4  # 1 opcode + 3 for pull
    assert cpu.flags.value == status_value  # Flags restored from stack
    assert cpu.flags[flags.C] == 1
    assert cpu.flags[flags.Z] == 1
    assert cpu.flags[flags.I] == 1
    assert cpu.flags[flags.D] == 1
    assert cpu.flags[flags.V] == 1
    assert cpu.flags[flags.N] == 1


def test_cpu_instruction_PLP_IMPLIED_0x28_clear_flags() -> None:  # noqa: N802
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    # Set some flags initially using individual flag setters
    cpu.flags[flags.C] = 1
    cpu.flags[flags.Z] = 1
    cpu.flags[flags.N] = 1

    # Push zero status onto the stack
    cpu.ram[cpu.S] = 0x00
    cpu.S -= 1

    cpu.ram[0xFFFC] = instructions.PLP_IMPLIED_0x28

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 4
    assert cpu.flags.value == 0x00  # All flags cleared
    assert cpu.flags[flags.C] == 0
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.I] == 0
    assert cpu.flags[flags.D] == 0
    assert cpu.flags[flags.V] == 0
    assert cpu.flags[flags.N] == 0


def test_cpu_instruction_PLP_IMPLIED_0x28_with_php() -> None:  # noqa: N802
    """Test PLP after PHP - round trip."""
    # given:
    cpu: mos6502.CPU = mos6502.CPU()
    cpu.reset()

    # Set some specific flags
    cpu.flags[flags.C] = 1
    cpu.flags[flags.Z] = 1
    cpu.flags[flags.N] = 1
    initial_flags: int = cpu.flags.value

    cpu.ram[0xFFFC] = instructions.PHP_IMPLIED_0x08
    cpu.ram[0xFFFD] = instructions.PLP_IMPLIED_0x28

    # when:
    with contextlib.suppress(exceptions.CPUCycleExhaustionError):
        cpu.execute(cycles=7)

    # then:
    assert cpu.PC == 0xFFFE
    assert cpu.cycles_executed == 7  # 3 for PHP + 4 for PLP

    # Flags should be restored (PHP pushes with B flag set, but PLP restores all bits)
    # So we get back the original flags OR'd with the B bits that were pushed
    assert cpu.flags[flags.C] == 1
    assert cpu.flags[flags.Z] == 1
    assert cpu.flags[flags.N] == 1
