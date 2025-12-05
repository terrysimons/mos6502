#!/usr/bin/env python3
import contextlib
import logging

import mos6502
from mos6502 import CPU, errors, flags, instructions

log = logging.getLogger("mos6502")
log.setLevel(logging.DEBUG)


def test_cpu_instruction_DEC_ZEROPAGE_0xC6(cpu: CPU) -> None:  # noqa: N802
    """Test DEC Zero Page addressing mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.ram[0x0042] = 0x05

    # DEC $42
    cpu.ram[pc] = instructions.DEC_ZEROPAGE_0xC6
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=5

    # then:
    assert cpu.ram[0x0042] == 0x04
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 0  # Positive
    # assert cpu.cycles_executed - cycles_before == 5
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_DEC_ZEROPAGE_0xC6_to_zero(cpu: CPU) -> None:  # noqa: N802
    """Test DEC to zero."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.ram[0x0042] = 0x01

    # DEC $42
    cpu.ram[pc] = instructions.DEC_ZEROPAGE_0xC6
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=5

    # then:
    assert cpu.ram[0x0042] == 0x00
    assert cpu.flags[flags.Z] == 1  # Zero
    assert cpu.flags[flags.N] == 0  # Not negative
    # assert cpu.cycles_executed - cycles_before == 5
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_DEC_ZEROPAGE_0xC6_wrap_to_ff(cpu: CPU) -> None:  # noqa: N802
    """Test DEC wrapping from 0x00 to 0xFF."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.ram[0x0042] = 0x00

    # DEC $42
    cpu.ram[pc] = instructions.DEC_ZEROPAGE_0xC6
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=5

    # then:
    assert cpu.ram[0x0042] == 0xFF
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Negative (bit 7 set)
    # assert cpu.cycles_executed - cycles_before == 5
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_DEC_ZEROPAGE_0xC6_negative(cpu: CPU) -> None:  # noqa: N802
    """Test DEC resulting in negative value (bit 7 set)."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.ram[0x0042] = 0x81  # 129

    # DEC $42
    cpu.ram[pc] = instructions.DEC_ZEROPAGE_0xC6
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=5

    # then:
    assert cpu.ram[0x0042] == 0x80  # 128 (bit 7 set)
    assert cpu.flags[flags.Z] == 0  # Not zero
    assert cpu.flags[flags.N] == 1  # Negative (bit 7 set)
    # assert cpu.cycles_executed - cycles_before == 5
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_DEC_ZEROPAGE_X_0xD6(cpu: CPU) -> None:  # noqa: N802
    """Test DEC Zero Page,X addressing mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.X = 0x05
    cpu.ram[0x0047] = 0x10  # 0x42 + 0x05 = 0x47

    # DEC $42,X
    cpu.ram[pc] = instructions.DEC_ZEROPAGE_X_0xD6
    cpu.ram[pc + 1] = 0x42

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=6

    # then:
    assert cpu.ram[0x0047] == 0x0F
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    # assert cpu.cycles_executed - cycles_before == 6
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_DEC_ABSOLUTE_0xCE(cpu: CPU) -> None:  # noqa: N802
    """Test DEC Absolute addressing mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.ram[0x1234] = 0x42

    # DEC $1234
    cpu.ram[pc] = instructions.DEC_ABSOLUTE_0xCE
    cpu.ram[pc + 1] = 0x34
    cpu.ram[pc + 2] = 0x12

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=6

    # then:
    assert cpu.ram[0x1234] == 0x41
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0
    # assert cpu.cycles_executed - cycles_before == 6
    assert cpu.instructions_executed - instructions_before == 1


def test_cpu_instruction_DEC_ABSOLUTE_X_0xDE(cpu: CPU) -> None:  # noqa: N802
    """Test DEC Absolute,X addressing mode."""
    # given:
    cycles_before = cpu.cycles_executed
    instructions_before = cpu.instructions_executed
    cpu.PC = 0x0400
    pc = cpu.PC

    cpu.X = 0x10
    cpu.ram[0x1244] = 0x80  # 0x1234 + 0x10 = 0x1244

    # DEC $1234,X
    cpu.ram[pc] = instructions.DEC_ABSOLUTE_X_0xDE
    cpu.ram[pc + 1] = 0x34
    cpu.ram[pc + 2] = 0x12

    # when:
    with contextlib.suppress(errors.CPUCycleExhaustionError, errors.IllegalCPUInstructionError):
        cpu.execute(max_instructions=1)  # cycles=7

    # then:
    assert cpu.ram[0x1244] == 0x7F
    assert cpu.flags[flags.Z] == 0
    assert cpu.flags[flags.N] == 0  # 0x7F doesn't have bit 7 set
    # assert cpu.cycles_executed - cycles_before == 7
    assert cpu.instructions_executed - instructions_before == 1
