#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_ROL_ACCUMULATOR_0x2A(cpu: CPU) -> None:  # noqa: N802
    """Test ROL Accumulator mode with carry clear."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x42  # 0100 0010
    cpu.flags[flags.C] = 0

    # ROL A
    cpu.ram[pc] = instructions.ROL_ACCUMULATOR_0x2A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x84  # 1000 0100 (shifted left, carry 0 in bit 0)
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 now set
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_ROL_ACCUMULATOR_0x2A_with_carry(cpu: CPU) -> None:  # noqa: N802
    """Test ROL with carry set."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x42  # 0100 0010
    cpu.flags[flags.C] = 1  # Carry set

    # ROL A
    cpu.ram[pc] = instructions.ROL_ACCUMULATOR_0x2A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x85  # 1000 0101 (shifted left, carry 1 in bit 0)
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 now set
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_ROL_ACCUMULATOR_0x2A_carry_out(cpu: CPU) -> None:  # noqa: N802
    """Test ROL with bit 7 set (carry out)."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.A = 0x81  # 1000 0001 (bit 7 set)
    cpu.flags[flags.C] = 0

    # ROL A
    cpu.ram[pc] = instructions.ROL_ACCUMULATOR_0x2A

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=2

    # then:
    assert cpu.A == 0x02  # 0000 0010
    assert cpu.flags[flags.C] == 1  # Bit 7 was 1
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Bit 7 clear
    # assert cpu.cycles_executed - cycles_before == 2
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_ROL_ZEROPAGE_0x26(cpu: CPU) -> None:  # noqa: N802
    """Test ROL Zero Page mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.ram[0x0042] = 0x55  # 0101 0101
    cpu.flags[flags.C] = 1

    # ROL $42
    cpu.ram[pc] = instructions.ROL_ZEROPAGE_0x26
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=5

    # then:
    assert cpu.ram[0x0042] == 0xAB  # 1010 1011 (shifted left with carry 1)
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 now set
    # assert cpu.cycles_executed - cycles_before == 5
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_ROL_ZEROPAGE_X_0x36(cpu: CPU) -> None:  # noqa: N802
    """Test ROL Zero Page,X mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.X = 0x05
    cpu.ram[0x0047] = 0x80  # 0x42 + 0x05
    cpu.flags[flags.C] = 0

    # ROL $42,X
    cpu.ram[pc] = instructions.ROL_ZEROPAGE_X_0x36
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=6

    # then:
    assert cpu.ram[0x0047] == 0x00  # 0000 0000 (bit 7 rotated out)
    assert cpu.flags[flags.C] == 1  # Bit 7 was 1
    assert cpu.flags[flags.Z] == 1  # Zero
    assert cpu.flags[flags.N] == 0
    # assert cpu.cycles_executed - cycles_before == 6
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_ROL_ABSOLUTE_0x2E(cpu: CPU) -> None:  # noqa: N802
    """Test ROL Absolute mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.ram[0x1234] = 0xFF  # 1111 1111
    cpu.flags[flags.C] = 0

    # ROL $1234
    cpu.ram[pc] = instructions.ROL_ABSOLUTE_0x2E
    cpu.ram[pc + 1] = 0x34
    cpu.ram[pc + 2] = 0x12

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=6

    # then:
    assert cpu.ram[0x1234] == 0xFE  # 1111 1110
    assert cpu.flags[flags.C] == 1  # Bit 7 was 1
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Bit 7 set
    # assert cpu.cycles_executed - cycles_before == 6
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_ROL_ABSOLUTE_X_0x3E(cpu: CPU) -> None:  # noqa: N802
    """Test ROL Absolute,X mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.X = 0x10
    cpu.ram[0x1244] = 0x01  # 0x1234 + 0x10
    cpu.flags[flags.C] = 1

    # ROL $1234,X
    cpu.ram[pc] = instructions.ROL_ABSOLUTE_X_0x3E
    cpu.ram[pc + 1] = 0x34
    cpu.ram[pc + 2] = 0x12

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=7

    # then:
    assert cpu.ram[0x1244] == 0x03  # 0000 0011 (shifted left with carry 1)
    assert cpu.flags[flags.C] == 0  # Bit 7 was 0
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0
    # assert cpu.cycles_executed - cycles_before == 7
    assert cpu.instructions_executed - instructions_before == 1
