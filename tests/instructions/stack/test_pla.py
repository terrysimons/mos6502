#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def check_noop_flags(expected_cpu: CPU, actual_cpu: CPU) -> None:
    """PLA only affects N and Z flags."""
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]


def test_cpu_instruction_PLA_IMPLIED_0x68(cpu: CPU) -> None:  # noqa: N802
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    # Push a value onto the stack first
    cpu.ram[cpu.S] = 0x42
    cpu.S -= 1

    cpu.ram[0xFFFC] = instructions.PLA_IMPLIED_0x68

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 4  # 1 opcode + 3 for pull
    assert cpu.A == 0x42  # Value pulled from stack
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_PLA_IMPLIED_0x68_zero_flag(cpu: CPU) -> None:  # noqa: N802
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    # Push zero onto the stack
    cpu.ram[cpu.S] = 0x00
    cpu.S -= 1

    cpu.ram[0xFFFC] = instructions.PLA_IMPLIED_0x68

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 4
    assert cpu.A == 0x00
    assert cpu.flags[flags.Z] == 1
    assert cpu.flags[flags.N] == 0
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_PLA_IMPLIED_0x68_negative_flag(cpu: CPU) -> None:  # noqa: N802
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    # Push negative value onto the stack
    cpu.ram[cpu.S] = 0x80
    cpu.S -= 1

    cpu.ram[0xFFFC] = instructions.PLA_IMPLIED_0x68

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 4
    assert cpu.A == 0x80
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1  # 0x80 has bit 7 set
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_PLA_IMPLIED_0x68_with_pha(cpu: CPU) -> None:  # noqa: N802
    """Test PLA after PHA - round trip."""
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.A = 0x55

    cpu.ram[0xFFFC] = instructions.PHA_IMPLIED_0x48
    cpu.ram[0xFFFD] = instructions.PLA_IMPLIED_0x68

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=7)

    # then:
    assert cpu.PC == 0xFFFE
    assert cpu.cycles_executed == 7  # 3 for PHA + 4 for PLA
    assert cpu.A == 0x55  # Same value pulled back
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_PLA_IMPLIED_0x68_near_stack_bottom(cpu: CPU) -> None:  # noqa: N802
    """Test PLA when pulling from near bottom of stack."""
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    # Set stack pointer to a low value
    cpu.S = 0x101
    cpu.ram[0x0102] = 0xBB  # Value to be pulled

    cpu.ram[0xFFFC] = instructions.PLA_IMPLIED_0x68

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)

    # then:
    assert cpu.PC == 0xFFFD
    assert cpu.cycles_executed == 4
    assert cpu.A == 0xBB  # Value pulled from 0x0102
    assert cpu.S == 0x102  # Stack pointer incremented
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 1  # 0xBB has bit 7 set
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_PLA_IMPLIED_0x68_multiple_pulls(cpu: CPU) -> None:  # noqa: N802
    """Test multiple PLA operations in sequence."""
    # given:
    initial_cpu: CPU = copy.deepcopy(cpu)

    # Set up stack with three values
    cpu.S = 0x1FC  # Stack pointer below three values (hardware: 0xFC)
    cpu.ram[0x01FD] = 0x11  # First to be pulled
    cpu.ram[0x01FE] = 0x22  # Second to be pulled
    cpu.ram[0x01FF] = 0x33  # Third to be pulled

    cpu.ram[0xFFFC] = instructions.PLA_IMPLIED_0x68
    cpu.ram[0xFFFD] = instructions.PLA_IMPLIED_0x68
    cpu.ram[0xFFFE] = instructions.PLA_IMPLIED_0x68

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)  # Pull first value

    # then:
    assert cpu.A == 0x11  # First value pulled
    assert cpu.S == 0x1FD

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)  # Pull second value

    # then:
    assert cpu.A == 0x22  # Second value pulled
    assert cpu.S == 0x1FE

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(cycles=4)  # Pull third value

    # then:
    assert cpu.A == 0x33  # Third value pulled
    assert cpu.S == 0x1FF
