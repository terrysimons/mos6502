#!/usr/bin/env python3
import contextlib
import copy
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def check_noop_flags(expected_cpu: CPU, actual_cpu: CPU) -> None:
    """PHA does not affect any flags."""
    assert actual_cpu.flags[flags.C] == expected_cpu.flags[flags.C]
    assert actual_cpu.flags[flags.Z] == expected_cpu.flags[flags.Z]
    assert actual_cpu.flags[flags.B] == expected_cpu.flags[flags.B]
    assert actual_cpu.flags[flags.D] == expected_cpu.flags[flags.D]
    assert actual_cpu.flags[flags.I] == expected_cpu.flags[flags.I]
    assert actual_cpu.flags[flags.V] == expected_cpu.flags[flags.V]
    assert actual_cpu.flags[flags.N] == expected_cpu.flags[flags.N]


def test_cpu_instruction_PHA_IMPLIED_0x48(cpu: CPU) -> None:  # noqa: N802
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    cpu.A = 0x42
    initial_sp: int = cpu.S

    cpu.ram[pc] = instructions.PHA_IMPLIED_0x48

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=3

    # then:
    assert cpu.PC == pc + 1
    # assert cpu.cycles_executed - cycles_before == 3  # 1 opcode + 2 for push
    assert cpu.A == 0x42  # A unchanged
    assert cpu.S == initial_sp - 1  # Stack pointer decremented
    assert cpu.ram[initial_sp] == 0x42  # Value pushed to stack
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_PHA_IMPLIED_0x48_stack_grows_down(cpu: CPU) -> None:  # noqa: N802
    """Test that stack grows downward with multiple pushes."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)
    initial_sp: int = cpu.S

    # Set A to different value and push three times
    cpu.A = 0x33
    cpu.ram[pc] = instructions.PHA_IMPLIED_0x48
    cpu.ram[pc + 1] = instructions.PHA_IMPLIED_0x48
    cpu.ram[pc + 2] = instructions.PHA_IMPLIED_0x48

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=3)  # cycles=9

    # then:
    assert cpu.PC == pc + 3
    # assert cpu.cycles_executed - cycles_before == 9  # 3 * 3 cycles
    assert cpu.S == initial_sp - 3  # Stack pointer decremented by 3
    # All three pushes should have the same value (0x33) since A doesn't change
    assert cpu.ram[initial_sp] == 0x33  # First push
    assert cpu.ram[initial_sp - 1] == 0x33  # Second push
    assert cpu.ram[initial_sp - 2] == 0x33  # Third push
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_PHA_IMPLIED_0x48_near_stack_bottom(cpu: CPU) -> None:  # noqa: N802
    """Test PHA near the bottom of the stack."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    # Set stack pointer to a low value
    cpu.S = 0x102
    cpu.A = 0xAA

    cpu.ram[pc] = instructions.PHA_IMPLIED_0x48

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=3

    # then:
    assert cpu.PC == pc + 1
    # assert cpu.cycles_executed - cycles_before == 3
    assert cpu.instructions_executed - instructions_before == 1
    assert cpu.A == 0xAA  # A unchanged
    assert cpu.S == 0x101  # Stack pointer decremented
    assert cpu.ram[0x0102] == 0xAA  # Value pushed to stack
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)


def test_cpu_instruction_PHA_IMPLIED_0x48_near_stack_top(cpu: CPU) -> None:  # noqa: N802
    """Test PHA near the top of the stack."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC
    initial_cpu: CPU = copy.deepcopy(cpu)

    # Set stack pointer near top (0x1FF = hardware 0xFF)
    cpu.S = 0x1FF
    cpu.A = 0x77

    cpu.ram[pc] = instructions.PHA_IMPLIED_0x48

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError):
        cpu.execute(max_instructions=1)  # cycles=3

    # then:
    assert cpu.PC == pc + 1
    # assert cpu.cycles_executed - cycles_before == 3
    assert cpu.instructions_executed - instructions_before == 1
    assert cpu.A == 0x77  # A unchanged
    assert cpu.S == 0x1FE  # Stack pointer decremented
    assert cpu.ram[0x01FF] == 0x77  # Value pushed to top of stack
    check_noop_flags(expected_cpu=initial_cpu, actual_cpu=cpu)
