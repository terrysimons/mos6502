#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_ASL_ACCUMULATOR_0x0A(cpu: CPU) -> None:  # noqa: N802
    """Test ASL Accumulator mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x42  # 0100 0010

    # ASL A
    cpu.ram[pc] = instructions.ASL_ACCUMULATOR_0x0A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x84  # 1000 0100 (shifted left)
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 now set
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_ASL_ACCUMULATOR_0x0A_carry(cpu: CPU) -> None:  # noqa: N802
    """Test ASL with carry flag set."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x81  # 1000 0001 (bit 7 set)

    # ASL A
    cpu.ram[pc] = instructions.ASL_ACCUMULATOR_0x0A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x02  # 0000 0010
    assert cpu.flags[flags.C] == 1  # Bit 7 was 1
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Bit 7 now clear
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_ASL_ACCUMULATOR_0x0A_zero(cpu: CPU) -> None:  # noqa: N802
    """Test ASL resulting in zero."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x80  # 1000 0000

    # ASL A
    cpu.ram[pc] = instructions.ASL_ACCUMULATOR_0x0A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x00  # 0000 0000
    assert cpu.flags[flags.C] == 1  # Bit 7 was 1
    assert cpu.flags[flags.Z] == 1  # Zero
    assert cpu.flags[flags.N] == 0  # Bit 7 clear
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_ASL_ZEROPAGE_0x06(cpu: CPU) -> None:  # noqa: N802
    """Test ASL Zero Page mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.ram[0x0042] = 0x55  # 0101 0101

    # ASL $42
    cpu.ram[pc] = instructions.ASL_ZEROPAGE_0x06
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=5

    # then:
    assert cpu.ram[0x0042] == 0xAA  # 1010 1010
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 now set
    # assert cpu.cycles_executed - cycles_before == 5
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_ASL_ZEROPAGE_X_0x16(cpu: CPU) -> None:  # noqa: N802
    """Test ASL Zero Page,X mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.X = 0x05
    cpu.ram[0x0047] = 0x01  # 0x42 + 0x05

    # ASL $42,X
    cpu.ram[pc] = instructions.ASL_ZEROPAGE_X_0x16
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=6

    # then:
    assert cpu.ram[0x0047] == 0x02
    assert cpu.flags[flags.C] == 0
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    # assert cpu.cycles_executed - cycles_before == 6
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_ASL_ABSOLUTE_0x0E(cpu: CPU) -> None:  # noqa: N802
    """Test ASL Absolute mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.ram[0x1234] = 0x40  # 0100 0000

    # ASL $1234
    cpu.ram[pc] = instructions.ASL_ABSOLUTE_0x0E
    cpu.ram[pc + 1] = 0x34
    cpu.ram[pc + 2] = 0x12

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=6

    # then:
    assert cpu.ram[0x1234] == 0x80  # 1000 0000
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 now set
    # assert cpu.cycles_executed - cycles_before == 6
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_ASL_ABSOLUTE_X_0x1E(cpu: CPU) -> None:  # noqa: N802
    """Test ASL Absolute,X mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.X = 0x10
    cpu.ram[0x1244] = 0xFF  # 0x1234 + 0x10

    # ASL $1234,X
    cpu.ram[pc] = instructions.ASL_ABSOLUTE_X_0x1E
    cpu.ram[pc + 1] = 0x34
    cpu.ram[pc + 2] = 0x12

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=7

    # then:
    assert cpu.ram[0x1244] == 0xFE  # 1111 1110
    assert cpu.flags[flags.C] == 1  # Bit 7 was 1
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 set
    # assert cpu.cycles_executed - cycles_before == 7
    assert cpu.instructions_executed - instructions_before == 1
